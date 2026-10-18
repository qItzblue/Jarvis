import { Bell, CalendarDays, Plus, Target, Trash2 } from "lucide-react";
import { useState } from "react";
import { RequirePlugin } from "../components/NotConfigured";
import { Button, Card, Empty, ErrorNote, useData } from "../components/ui";
import { api, isError } from "../lib/api";
import { useJarvis } from "../lib/store";
import { fmtCountdown } from "./Home";

const PRI = { 1: "text-danger", 2: "text-accent", 3: "text-dim" } as Record<number, string>;

function Week() {
  const ev = useData<any>(() => api.get("/api/p/calendar/events?days=7"));
  const days = Array.from({ length: 7 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i); return d; });
  if (ev.data && isError(ev.data)) return <ErrorNote error={ev.data.error} />;
  return (
    <div className="grid grid-cols-7 gap-2 text-xs">
      {days.map((d) => {
        const key = d.toISOString().slice(0, 10);
        const items = (ev.data ?? []).filter((e: any) => new Date(e.start).toISOString().slice(0, 10) === key);
        return (
          <div key={key} className="min-h-32 rounded-lg border border-line bg-panel-2 p-2">
            <p className="label mb-1">{d.toLocaleDateString([], { weekday: "short", day: "numeric" })}</p>
            {items.map((e: any) => <p key={e.id} className="mb-1 truncate rounded bg-accent/15 px-1 py-0.5" title={e.summary}>
              {e.start.includes("T") && new Date(e.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} {e.summary}</p>)}
          </div>
        );
      })}
    </div>
  );
}

export function Tasks() {
  const { send, focus } = useJarvis();
  const todos = useData<any[]>(() => api.get("/api/p/todo"));
  const reminders = useData<any[]>(() => api.get("/api/p/timers/reminders"), [], 15000);
  const [text, setText] = useState("");
  const [priority, setPriority] = useState(2);
  const [rText, setRText] = useState("");
  const [rWhen, setRWhen] = useState("");

  const add = async () => { if (!text.trim()) return; await api.post("/api/p/todo", { text, priority }); setText(""); todos.reload(); };
  const toggle = async (t: any) => { await api.put(`/api/p/todo/${t.id}`, { ...t, done: !t.done }); todos.reload(); };

  return (
    <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
      <Card title="This week" icon={<CalendarDays size={14} />} className="xl:col-span-2">
        <RequirePlugin name="calendar" label="Google Calendar"><Week /></RequirePlugin>
      </Card>
      <Card title="To-do" icon={<Plus size={14} />}>
        <div className="flex gap-2">
          <input className="input" placeholder="New task…" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && add()} aria-label="New task" />
          <select className="input !w-28" value={priority} onChange={(e) => setPriority(+e.target.value)} aria-label="Priority">
            <option value={1}>High</option><option value={2}>Normal</option><option value={3}>Low</option>
          </select>
          <Button variant="primary" onClick={add} aria-label="Add task"><Plus size={16} /></Button>
        </div>
        {!todos.data?.length && <Empty title="All clear">Add a task, or say “add buy milk to my list”.</Empty>}
        <ul className="divide-y divide-line">
          {todos.data?.map((t) => (
            <li key={t.id} className="flex items-center gap-3 py-2">
              <input type="checkbox" checked={t.done} onChange={() => toggle(t)} className="h-4 w-4 accent-[var(--accent)]" aria-label={`Done: ${t.text}`} />
              <span className={`flex-1 ${t.done ? "text-dim line-through" : ""}`}>{t.text}</span>
              <span className={`label ${PRI[t.priority]}`}>{["", "high", "normal", "low"][t.priority]}</span>
              <button onClick={async () => { await api.del(`/api/p/todo/${t.id}`); todos.reload(); }} aria-label="Delete task" className="text-dim hover:text-danger"><Trash2 size={14} /></button>
            </li>
          ))}
        </ul>
      </Card>
      <div className="flex flex-col gap-4">
        <Card title="Focus timer" icon={<Target size={14} />}>
          <RequirePlugin name="focus" label="Focus mode">
            {focus ? (
              <div className="flex flex-col items-center gap-2">
                <p className="font-mono text-5xl text-accent">{fmtCountdown(focus.ends_at - Date.now() / 1000)}</p>
                <p className="label">{focus.phase} · round {focus.round}/{focus.rounds}</p>
                <Button variant="danger" onClick={() => api.tool("focus__stop_focus")}>Stop</Button>
              </div>
            ) : (
              <div className="flex gap-2"><Button variant="primary" onClick={() => api.tool("focus__start_focus", { rounds: 4 })}>Start 4 × Pomodoro</Button>
                <Button onClick={() => api.tool("focus__start_focus", { rounds: 1 })}>One round</Button></div>
            )}
          </RequirePlugin>
        </Card>
        <Card title="Reminders" icon={<Bell size={14} />}>
          <div className="flex gap-2">
            <input className="input" placeholder="Remind me to…" value={rText} onChange={(e) => setRText(e.target.value)} aria-label="Reminder text" />
            <input className="input !w-52" type="datetime-local" value={rWhen} onChange={(e) => setRWhen(e.target.value)} aria-label="Reminder time" />
            <Button variant="primary" aria-label="Add reminder" onClick={async () => {
              if (!rText || !rWhen) return; await api.tool("timers__add_reminder", { text: rText, when: rWhen }); setRText(""); reminders.reload();
            }}><Plus size={16} /></Button>
          </div>
          {!reminders.data?.length ? <p className="text-sm text-dim">No upcoming reminders. Try “remind me in 20 minutes to stretch”.</p> :
            reminders.data.map((r) => (
              <div key={r.id} className="flex items-center justify-between text-sm">
                <span>{r.text}</span>
                <span className="flex items-center gap-2 font-mono text-xs text-dim">{new Date(r.due_at).toLocaleString()}
                  <button onClick={async () => { await api.del(`/api/p/timers/reminders/${r.id}`); reminders.reload(); }} aria-label="Delete reminder" className="hover:text-danger"><Trash2 size={14} /></button></span>
              </div>
            ))}
          <Button variant="ghost" onClick={() => send("What reminders do I have?")}>Ask Jarvis</Button>
        </Card>
      </div>
    </div>
  );
}
