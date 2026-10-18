import asyncio
import fnmatch
import os
from pathlib import Path

from ..core import osctl
from ..core.plugins import Plugin, tool


class FilesPlugin(Plugin):
    name, title, category, icon = "files", "File search", "computer", "folder-search"
    description = "Finds files by name in your folders and opens them."
    settings_schema = {"roots": {"label": "Folders to search (comma separated)", "type": "string",
                                 "default": "~/Documents,~/Desktop,~/Downloads,~/Pictures"}}

    def find(self, pattern: str, limit: int = 25) -> list[dict]:
        pat = pattern if any(c in pattern for c in "*?[") else f"*{pattern}*"
        out = []
        for root in str(self.setting("roots")).split(","):
            base = Path(root.strip()).expanduser()
            if not base.exists():
                continue
            for dirpath, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
                for f in files:
                    if fnmatch.fnmatch(f.lower(), pat.lower()):
                        p = Path(dirpath) / f
                        st = p.stat()
                        out.append({"path": str(p), "size_kb": round(st.st_size / 1024), "modified": st.st_mtime})
                        if len(out) >= limit:
                            return out
        return out

    @tool("Search for files by name (wildcards allowed).", {"pattern": {"type": "string"},
                                                              "limit": {"type": "integer"}}, required=["pattern"])
    async def search(self, pattern: str, limit: int = 25):
        res = await asyncio.to_thread(self.find, pattern, int(limit))
        return sorted(res, key=lambda r: -r["modified"])

    @tool("Open a file with its default app.", {"path": {"type": "string"}})
    async def open_file(self, path: str):
        p = str(Path(path).expanduser())
        if osctl.SYSTEM == "Windows":
            return await osctl.run("cmd", "/c", "start", "", p)
        return await osctl.run("open" if osctl.SYSTEM == "Darwin" else "xdg-open", p)

    @tool("Delete a file.", {"path": {"type": "string"}}, confirm=True)
    async def delete_file(self, path: str):
        p = Path(path).expanduser()
        if not p.is_file():
            return {"error": "Not a file"}
        p.unlink()
        return {"deleted": str(p)}
