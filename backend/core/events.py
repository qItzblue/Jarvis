"""In-process pub/sub used to push alerts and confirmations to every connected UI client."""
import asyncio


class EventBus:
    def __init__(self):
        self._subs: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def publish(self, event: dict) -> None:
        for q in list(self._subs):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def alert(self, title: str, body: str = "", level: str = "info") -> None:
        self.publish({"type": "alert", "title": title, "body": body, "level": level})
