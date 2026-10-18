import platform
import time

import psutil

from ..core.plugins import Plugin, tool


class SystemPlugin(Plugin):
    name, title, category, icon = "system", "System stats", "computer", "cpu"
    description = "CPU, memory, disk, network, battery and running processes."

    @tool("Get current system statistics.", {})
    async def stats(self):
        vm, disk, net = psutil.virtual_memory(), psutil.disk_usage("/"), psutil.net_io_counters()
        bat = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
        return {
            "os": f"{platform.system()} {platform.release()}", "cpu_percent": psutil.cpu_percent(interval=0.2),
            "cpu_count": psutil.cpu_count(), "memory_percent": vm.percent,
            "memory_used_gb": round(vm.used / 1e9, 1), "memory_total_gb": round(vm.total / 1e9, 1),
            "disk_percent": disk.percent, "disk_free_gb": round(disk.free / 1e9, 1),
            "net_sent_mb": round(net.bytes_sent / 1e6, 1), "net_recv_mb": round(net.bytes_recv / 1e6, 1),
            "battery": {"percent": round(bat.percent), "plugged": bat.power_plugged} if bat else None,
            "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 1),
        }

    @tool("List the processes using the most CPU or memory.", {
        "sort": {"type": "string", "enum": ["cpu", "memory"]}, "limit": {"type": "integer"}}, required=[])
    async def top_processes(self, sort: str = "cpu", limit: int = 10):
        # psutil measures CPU between calls on the same Process object, so keep them cached.
        cache = self.__dict__.setdefault("_procs", {})
        procs, alive = [], set()
        for p in psutil.process_iter(["pid", "name"]):
            proc = cache.setdefault(p.pid, p)
            alive.add(p.pid)
            try:
                procs.append({**p.info, "cpu_percent": proc.cpu_percent(None), "memory_percent": proc.memory_percent()})
            except psutil.Error:
                pass
        for pid in set(cache) - alive:
            cache.pop(pid)
        key = "cpu_percent" if sort == "cpu" else "memory_percent"
        procs.sort(key=lambda x: x.get(key) or 0, reverse=True)
        return [{**p, "memory_percent": round(p.get("memory_percent") or 0, 1)} for p in procs[:int(limit)]]

    def router(self):
        from fastapi import APIRouter
        r = APIRouter()
        r.get("/stats")(self.stats)
        r.get("/processes")(self.top_processes)
        return r
