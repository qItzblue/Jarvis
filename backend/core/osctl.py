"""Small cross-platform helpers for controlling the local computer."""
import asyncio
import platform
import shutil

SYSTEM = platform.system()  # "Windows" | "Darwin" | "Linux"


async def run(*cmd: str, timeout: float = 15) -> dict:
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": "timed out"}
    return {"ok": proc.returncode == 0, "code": proc.returncode,
            "stdout": out.decode(errors="replace")[-4000:], "stderr": err.decode(errors="replace")[-2000:]}


async def powershell(script: str) -> dict:
    return await run("powershell", "-NoProfile", "-Command", script)


async def osascript(script: str) -> dict:
    return await run("osascript", "-e", script)


def have(binary: str) -> bool:
    return shutil.which(binary) is not None
