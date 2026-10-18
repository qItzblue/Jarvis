import { Brain, Mic, Pencil, Plus, Save, Square, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button, Card, Empty, useData } from "../components/ui";
import { api, API_BASE } from "../lib/api";
import { Endpointer } from "../lib/audio";
import { Mic as MicEngine } from "../lib/mic";

export function Notes() {
  const notes = useData<any[]>(() => api.get("/api/p/notes"));
  const memory = useData<any[]>(() => api.get("/api/memory"));
  const [sel, setSel] = useState<any>(null);
  const [recording, setRecording] = useState(false);
  const [fact, setFact] = useState("");
  const [editing, setEditing] = useState<{ id: number; text: string } | null>(null);
  const memo = useRef<MicEngine | null>(null);

  useEffect(() => () => memo.current?.stop(), []);

  const save = async () => {
    if (!sel) return;
    const saved = sel.id ? await api.put(`/api/p/notes/${sel.id}`, sel) : await api.post("/api/p/notes", sel);
    setSel(saved); notes.reload();
  };

  const toggleMemo = async () => {
    if (recording) { memo.current?.finish(true); return; }
    const m = new MicEngine();
    memo.current = m;
    m.onRecordingChange = setRecording;
    m.onUtterance = async (wav) => {
      const f = new FormData(); f.append("audio", wav, "memo.wav"); f.append("title", `Voice memo ${new Date().toLocaleString()}`);
      const n = await api.post("/api/p/notes/memo", f); m.stop(); notes.reload(); setSel(n);
    };
    await m.record(new Endpointer(0.02, 1e9, 10 * 60_000, 1e9)); // manual stop, 10 min max
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[260px_1fr_1fr]">
      <Card title="Notes" actions={<>
        <Button variant={recording ? "danger" : "subtle"} onClick={toggleMemo} title="Record voice memo">{recording ? <Square size={14} /> : <Mic size={14} />}{recording ? "Stop" : "Memo"}</Button>
        <Button variant="primary" onClick={() => setSel({ title: "", body: "" })} aria-label="New note"><Plus size={14} /></Button></>}>
        {!notes.data?.length && <Empty title="No notes yet" />}
        <div className="flex flex-col gap-1 overflow-y-auto">
          {notes.data?.map((n) => (
            <button key={n.id} onClick={() => setSel(n)} className={`rounded-lg px-2 py-1.5 text-left text-sm ${sel?.id === n.id ? "bg-accent/10 text-accent" : "hover:bg-panel-2"}`}>
              <p className="truncate font-medium">{n.audio_path ? "🎙 " : ""}{n.title || "Untitled"}</p>
              <p className="truncate text-xs text-dim">{n.body}</p>
            </button>
          ))}
        </div>
      </Card>
      <Card title="Editor" actions={sel && <>
        {sel.id && <Button variant="ghost" aria-label="Delete note" onClick={async () => { await api.del(`/api/p/notes/${sel.id}`); setSel(null); notes.reload(); }}><Trash2 size={14} /></Button>}
        <Button variant="primary" onClick={save}><Save size={14} /> Save</Button></>}>
        {sel ? (
          <>
            <input className="input text-lg font-semibold" value={sel.title} placeholder="Title" aria-label="Note title" onChange={(e) => setSel({ ...sel, title: e.target.value })} />
            {sel.audio_path && <audio controls src={`${API_BASE}/api/p/notes/${sel.id}/audio`} className="w-full" />}
            <textarea className="input min-h-80 flex-1 font-mono text-sm" value={sel.body} aria-label="Note body" onChange={(e) => setSel({ ...sel, body: e.target.value })} />
          </>
        ) : <Empty title="Select or create a note">Or say “take a note: …”.</Empty>}
      </Card>
      <Card title="What Jarvis remembers about you" icon={<Brain size={14} />}>
        <div className="flex gap-2">
          <input className="input" value={fact} placeholder="Add a fact, e.g. I'm vegetarian" onChange={(e) => setFact(e.target.value)} aria-label="New memory" />
          <Button variant="primary" aria-label="Add memory" onClick={async () => { if (fact.trim()) { await api.post("/api/memory", { text: fact }); setFact(""); memory.reload(); } }}><Plus size={16} /></Button>
        </div>
        {!memory.data?.length && <Empty title="Nothing remembered yet">Jarvis saves lasting facts you mention. Everything stays on this computer.</Empty>}
        <ul className="divide-y divide-line">
          {memory.data?.map((m) => (
            <li key={m.id} className="flex items-center gap-2 py-2 text-sm">
              {editing?.id === m.id ? (
                <input className="input" autoFocus value={editing!.text} onChange={(e) => setEditing({ id: m.id, text: e.target.value })} aria-label="Edit memory"
                  onKeyDown={async (e) => { if (e.key === "Enter") { await api.put(`/api/memory/${m.id}`, { text: editing!.text }); setEditing(null); memory.reload(); } }} />
              ) : <span className="flex-1">{m.text}</span>}
              <button className="text-dim hover:text-accent" aria-label="Edit memory" onClick={() => setEditing({ id: m.id, text: m.text })}><Pencil size={14} /></button>
              <button className="text-dim hover:text-danger" aria-label="Forget" onClick={async () => { await api.del(`/api/memory/${m.id}`); memory.reload(); }}><Trash2 size={14} /></button>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
