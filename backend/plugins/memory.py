from ..core.plugins import Plugin, tool


class MemoryPlugin(Plugin):
    name, title, category, icon = "memory", "Long-term memory", "core", "brain"
    description = "Remembers facts and preferences about you, stored locally."

    @tool("Save a lasting fact or preference about the user.", {"fact": {"type": "string"}})
    async def remember(self, fact: str):
        return self.ctx.memory.add(fact)

    @tool("Search what you remember about the user.", {"query": {"type": "string"}})
    async def recall(self, query: str):
        return self.ctx.memory.search(query, k=8, min_score=0.0)

    @tool("Forget a remembered fact by its id.", {"id": {"type": "integer"}}, confirm=True)
    async def forget(self, id: int):
        return {"deleted": self.ctx.memory.delete(id)}
