from fastapi import APIRouter
from pydantic import BaseModel

from .. import db
from ..db import Todo, row_dict
from ..core.plugins import Plugin, tool


class TodoBody(BaseModel):
    text: str = ""
    priority: int = 2
    due: str | None = None
    done: bool | None = None


class TodoPlugin(Plugin):
    name, title, category, icon = "todo", "To-do list", "productivity", "list-checks"
    description = "Local to-do list, with optional syncing of new tasks to Todoist."
    settings_schema = {"todoist_token": {"label": "Todoist API token (optional)", "type": "string",
                                         "secret": True, "env": "TODOIST_API_TOKEN"}}

    @tool("Add a task to the to-do list.", {
        "text": {"type": "string"}, "priority": {"type": "integer", "description": "1 high, 2 normal, 3 low"},
        "due": {"type": "string", "description": "Optional due date, ISO"}}, required=["text"])
    async def add(self, text: str, priority: int = 2, due: str | None = None):
        with db.session() as s:
            t = Todo(text=text, priority=int(priority), due=due)
            s.add(t)
            s.flush()
            out = row_dict(t)
        token = self.setting("todoist_token")
        if token:
            body = {"content": text, "priority": {1: 4, 2: 2, 3: 1}.get(int(priority), 1)}
            if due:
                body["due_string"] = due
            r = await self.ctx.http.post("https://api.todoist.com/rest/v2/tasks", json=body,
                                         headers={"Authorization": f"Bearer {token}"})
            out["todoist"] = r.status_code < 300
        return out

    @tool("List tasks.", {"include_done": {"type": "boolean"}}, required=[])
    async def list(self, include_done: bool = False):
        with db.session() as s:
            q = s.query(Todo)
            if not include_done:
                q = q.filter_by(done=False)
            return [row_dict(t) for t in q.order_by(Todo.done, Todo.priority, Todo.id)]

    @tool("Mark a task done.", {"id": {"type": "integer"}})
    async def complete(self, id: int):
        with db.session() as s:
            t = s.get(Todo, int(id))
            if t:
                t.done = True
            return {"ok": t is not None}

    @tool("Delete a task.", {"id": {"type": "integer"}})
    async def delete(self, id: int):
        with db.session() as s:
            return {"deleted": s.query(Todo).filter_by(id=int(id)).delete() > 0}

    def router(self):
        r = APIRouter()

        @r.get("")
        async def all_():
            return await self.list(True)

        @r.post("")
        async def create(b: TodoBody):
            return await self.add(b.text, b.priority, b.due)

        @r.put("/{tid}")
        async def update(tid: int, b: TodoBody):
            with db.session() as s:
                t = s.get(Todo, tid)
                if b.text:
                    t.text = b.text
                if b.done is not None:
                    t.done = b.done
                t.priority, t.due = b.priority, b.due
                return row_dict(t)

        r.delete("/{id}")(self.delete)
        return r
