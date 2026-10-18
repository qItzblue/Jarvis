import base64
import io

from ..core.plugins import Plugin, tool


class ScreenPlugin(Plugin):
    name, title, category, icon = "screen", "Screen vision", "computer", "monitor"
    description = "Takes screenshots and answers 'what's on my screen?' using the AI's vision."
    optional_deps = ("mss",)

    def capture_png(self) -> bytes:
        import mss
        import mss.tools
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[1])
            return mss.tools.to_png(shot.rgb, shot.size)

    @tool("Look at the user's screen and answer a question about it.", {"question": {"type": "string"}},
          required=[])
    async def look(self, question: str = "Describe what is on the screen."):
        png = self.capture_png()
        b64 = base64.b64encode(png).decode()
        answer = await self.ctx.llm.complete(question, system="You are looking at a screenshot of the user's "
                                             "screen. Be specific and concise.", images=[b64])
        return {"answer": answer}

    @tool("Save a screenshot to the Pictures folder.", {})
    async def screenshot(self):
        from datetime import datetime
        from pathlib import Path
        folder = Path.home() / "Pictures" / "Jarvis"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"screenshot-{datetime.now():%Y%m%d-%H%M%S}.png"
        path.write_bytes(self.capture_png())
        return {"saved": str(path)}
