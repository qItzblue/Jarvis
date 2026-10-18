from pathlib import Path

from ..core import osctl
from ..core.plugins import Plugin, tool


class CodingPlugin(Plugin):
    name, title, category, icon = "coding", "Coding helper", "computer", "code"
    description = "Reads code files and project folders so Jarvis can explain errors and suggest fixes."
    settings_schema = {"projects_dir": {"label": "Projects folder", "type": "string", "default": "~/code"}}

    def _resolve(self, path: str) -> Path:
        p = Path(path).expanduser()
        return p if p.is_absolute() else Path(self.setting("projects_dir")).expanduser() / p

    @tool("Read a source file (first 400 lines).", {"path": {"type": "string"}})
    async def read_file(self, path: str):
        p = self._resolve(path)
        if not p.is_file():
            return {"error": f"Not found: {p}"}
        lines = p.read_text(errors="replace").splitlines()
        return {"path": str(p), "lines": len(lines), "content": "\n".join(lines[:400])}

    @tool("List files in a project folder.", {"path": {"type": "string"}}, required=[])
    async def list_dir(self, path: str = ""):
        p = self._resolve(path) if path else Path(self.setting("projects_dir")).expanduser()
        if not p.is_dir():
            return {"error": f"Not a folder: {p}"}
        return sorted(f"{c.name}/" if c.is_dir() else c.name for c in p.iterdir() if not c.name.startswith("."))[:300]

    @tool("Write (overwrite) a source file.", {"path": {"type": "string"}, "content": {"type": "string"}},
          confirm=True)
    async def write_file(self, path: str, content: str):
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return {"written": str(p), "bytes": len(content)}

    @tool("Show git status and recent commits for a project.", {"path": {"type": "string"}})
    async def git_status(self, path: str):
        p = str(self._resolve(path))
        status = await osctl.run("git", "-C", p, "status", "--short", "--branch")
        log = await osctl.run("git", "-C", p, "log", "--oneline", "-5")
        return {"status": status.get("stdout"), "log": log.get("stdout")}
