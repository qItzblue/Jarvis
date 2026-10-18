"""Plugin system. A plugin is one module in backend/plugins with a Plugin subclass.

Methods decorated with @tool become LLM tools named "<plugin>__<method>". Plugins may also
expose REST routes for the UI via router(), and background work via start()/stop().
"""
import importlib
import importlib.util
import inspect
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger("jarvis.plugins")


def tool(description: str, params: dict | None = None, required: list[str] | None = None,
         confirm: bool = False):
    """Mark a plugin method as a tool. `confirm=True` requires explicit user approval."""
    def deco(fn):
        fn._tool = {"description": description, "params": params or {},
                    "required": list(params or {}) if required is None else required, "confirm": confirm}
        return fn
    return deco


@dataclass
class Tool:
    name: str
    plugin: str
    description: str
    schema: dict
    confirm: bool
    fn: Callable

    def spec(self) -> dict:
        return {"name": self.name, "description": self.description, "schema": self.schema}


@dataclass
class Context:
    settings: Any
    bus: Any
    confirm: Any
    llm: Any
    memory: Any
    http: Any
    registry: Any = None
    voice: Any = None
    extra: dict = field(default_factory=dict)


class Plugin:
    name = ""
    title = ""
    description = ""
    category = "general"
    icon = "puzzle"
    settings_schema: dict[str, dict] = {}
    requires: tuple[str, ...] = ()        # setting keys that must be set
    optional_deps: tuple[str, ...] = ()   # python modules that must be importable
    default_enabled = True

    def __init__(self, ctx: Context):
        self.ctx = ctx

    # --- settings -------------------------------------------------------
    def setting(self, key: str, default=None):
        sch = self.settings_schema.get(key, {})
        val = self.ctx.settings.get(f"{self.name}.{key}", None, env=sch.get("env"))
        if val in (None, ""):
            fallback = sch.get("fallback")
            if fallback:
                val = self.ctx.settings.get(fallback)
        if val in (None, ""):
            return sch.get("default", default)
        return val

    def missing_deps(self) -> list[str]:
        return [m for m in self.optional_deps if importlib.util.find_spec(m) is None]

    def is_configured(self) -> bool:
        return all(self.setting(k) not in (None, "") for k in self.requires)

    @property
    def enabled(self) -> bool:
        val = self.ctx.settings.get(f"plugin.{self.name}.enabled", None)
        return self.default_enabled if val is None else bool(val)

    def status(self) -> str:
        if not self.enabled:
            return "disabled"
        if self.missing_deps():
            return "missing_dependency"
        if not self.is_configured():
            return "not_configured"
        return "ok"

    def tools(self) -> list[Tool]:
        out = []
        for attr, fn in inspect.getmembers(self, predicate=inspect.ismethod):
            meta = getattr(fn, "_tool", None)
            if meta:
                out.append(Tool(
                    name=f"{self.name}__{attr}", plugin=self.name, description=meta["description"],
                    schema={"type": "object", "properties": meta["params"], "required": meta["required"]},
                    confirm=meta["confirm"], fn=fn))
        return out

    def router(self):
        return None

    async def start(self):
        pass

    async def stop(self):
        pass

    def info(self) -> dict:
        settings = []
        for key, sch in self.settings_schema.items():
            val = self.setting(key)
            from .settings import mask
            settings.append({"key": key, **{k: v for k, v in sch.items() if k != "fallback"},
                             "value": mask(val) if sch.get("secret") else val, "is_set": val not in (None, "")})
        return {"name": self.name, "title": self.title or self.name, "description": self.description,
                "category": self.category, "icon": self.icon, "enabled": self.enabled, "status": self.status(),
                "missing_deps": self.missing_deps(), "requires": list(self.requires), "settings": settings,
                "tools": [{"name": t.name, "description": t.description, "confirm": t.confirm} for t in self.tools()]}


class Registry:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        ctx.registry = self
        self.plugins: dict[str, Plugin] = {}

    def discover(self, package: str = "backend.plugins") -> None:
        pkg = importlib.import_module(package)
        for mod in pkgutil.iter_modules(pkg.__path__):
            if mod.name.startswith("_"):
                continue
            try:
                module = importlib.import_module(f"{package}.{mod.name}")
            except Exception:
                log.exception("failed to import plugin %s", mod.name)
                continue
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, Plugin) and cls is not Plugin and cls.name and cls.__module__ == module.__name__:
                    self.add(cls(self.ctx))

    def add(self, plugin: Plugin) -> Plugin:
        self.plugins[plugin.name] = plugin
        return plugin

    def get(self, name: str) -> Plugin | None:
        p = self.plugins.get(name)
        return p if p and p.status() == "ok" else None

    def tools(self) -> list[Tool]:
        return [t for p in self.plugins.values() if p.status() == "ok" for t in p.tools()]

    def find_tool(self, name: str) -> Tool | None:
        return next((t for t in self.tools() if t.name == name), None)

    async def call(self, name: str, args: dict | None = None, source: str = "assistant") -> Any:
        t = self.find_tool(name)
        if t is None:
            return {"error": f"Tool '{name}' is not available (unknown, disabled or not configured)."}
        args = args or {}
        if t.confirm:
            approved = await self.ctx.confirm.request(t.description, {"tool": name, "args": args, "source": source})
            if not approved:
                return {"error": "The user declined this action."}
        try:
            return await t.fn(**args)
        except TypeError as e:
            return {"error": f"Bad arguments: {e}"}
        except Exception as e:  # never let a plugin crash the assistant
            log.exception("tool %s failed", name)
            return {"error": f"{type(e).__name__}: {e}"}

    async def start_all(self):
        for p in self.plugins.values():
            if p.status() == "ok":
                try:
                    await p.start()
                except Exception:
                    log.exception("plugin %s failed to start", p.name)

    async def stop_all(self):
        for p in self.plugins.values():
            try:
                await p.stop()
            except Exception:
                log.exception("plugin %s failed to stop", p.name)
