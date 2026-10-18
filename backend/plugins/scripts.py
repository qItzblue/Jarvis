import json

from ..core import osctl
from ..core.plugins import Plugin, tool

EXAMPLE = json.dumps({"backup notes": "echo backing up", "update system": "echo run your updater here"}, indent=2)


class ScriptsPlugin(Plugin):
    name, title, category, icon = "scripts", "Scripts & macros", "computer", "terminal"
    description = "Runs shell commands you have saved under a name. Each run asks for confirmation."
    settings_schema = {"scripts": {"label": "Saved scripts (JSON: name → command)", "type": "text",
                                   "default": EXAMPLE}}

    def saved(self) -> dict:
        try:
            return json.loads(self.setting("scripts") or "{}")
        except json.JSONDecodeError:
            return {}

    @tool("List the user's saved scripts.", {})
    async def list_scripts(self):
        return self.saved()

    @tool("Run one of the user's saved scripts by name.", {"name": {"type": "string"}}, confirm=True)
    async def run_script(self, name: str):
        cmd = self.saved().get(name)
        if not cmd:
            return {"error": f"No saved script called '{name}'"}
        if osctl.SYSTEM == "Windows":
            return await osctl.run("cmd", "/c", cmd, timeout=300)
        return await osctl.run("/bin/sh", "-c", cmd, timeout=300)
