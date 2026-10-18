"""Human-in-the-loop confirmation for destructive or outward-facing actions."""
import asyncio
import uuid

from .events import EventBus


class Confirmations:
    def __init__(self, bus: EventBus, timeout: float = 120):
        self.bus = bus
        self.timeout = timeout
        self._pending: dict[str, asyncio.Future] = {}

    async def request(self, title: str, details: dict | None = None) -> bool:
        cid = uuid.uuid4().hex[:12]
        fut = asyncio.get_running_loop().create_future()
        self._pending[cid] = fut
        self.bus.publish({"type": "confirm_request", "id": cid, "title": title, "details": details or {}})
        try:
            return await asyncio.wait_for(fut, self.timeout)
        except asyncio.TimeoutError:
            return False
        finally:
            self._pending.pop(cid, None)
            self.bus.publish({"type": "confirm_closed", "id": cid})

    def resolve(self, cid: str, approved: bool) -> bool:
        fut = self._pending.get(cid)
        if fut and not fut.done():
            fut.set_result(bool(approved))
            return True
        return False

    def pending(self) -> list[str]:
        return list(self._pending)
