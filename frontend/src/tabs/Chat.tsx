import { AlertCircle, CheckCircle2, ImagePlus, Loader2, MessageSquarePlus, Trash2, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button, Empty, useData } from "../components/ui";
import { api, API_BASE } from "../lib/api";
import { ChatMessage, toolLabel } from "../lib/chat";
import { useJarvis } from "../lib/store";

function Text({ text }: { text: string }) {
  const parts = text.split(/```(?:\w+)?\n?([\s\S]*?)```/g);
  return <>{parts.map((p, i) => i % 2
    ? <pre key={i} className="my-2 overflow-x-auto rounded-lg bg-bg p-3 font-mono text-xs">{p}</pre>
    : <span key={i} className="whitespace-pre-wrap">{p}</span>)}</>;
}

function ToolChip({ t }: { t: ChatMessage["tools"][number] }) {
  const img = t.result && typeof t.result === "object" && (t.result as any).url?.startsWith("/api/p/images");
  return (
    <div className="flex flex-col gap-1">
      <span className={`inline-flex w-fit items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[11px] ${t.status === "running" ? "border-accent/50 text-accent" : t.ok ? "border-ok/40 text-ok" : "border-danger/40 text-danger"}`}
        title={t.result ? JSON.stringify(t.result).slice(0, 500) : undefined}>
        {t.status === "running" ? <Loader2 size={12} className="anim-spin-fast" /> : t.ok ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
        {toolLabel(t.name)}
      </span>
      {img && <img src={API_BASE + (t.result as any).url} className="max-w-xs rounded-lg border border-line" alt="Generated" />}
    </div>
  );
}

export function Chat() {
  const { messages, send, conversationId, openConversation, busy } = useJarvis();
  const convs = useData<any[]>(() => api.get("/api/conversations"), [conversationId, busy]);
  const [images, setImages] = useState<string[]>([]);
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [messages]);

  const attach = async (files: FileList | null) => {
    const out: string[] = [];
    for (const f of Array.from(files ?? [])) {
      const b64 = await new Promise<string>((res) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1]); r.readAsDataURL(f); });
      out.push(b64);
    }
    setImages((i) => [...i, ...out]);
  };

  return (
    <div className="grid h-full min-h-0 gap-4 md:grid-cols-[240px_1fr]">
      <aside className="panel hidden min-h-0 flex-col gap-1 overflow-y-auto p-2 md:flex">
        <Button variant="primary" onClick={() => openConversation(null)} className="mb-2"><MessageSquarePlus size={16} /> New chat</Button>
        {convs.data?.map((c) => (
          <div key={c.id} className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm ${c.id === conversationId ? "bg-accent/10 text-accent" : "hover:bg-panel-2"}`}>
            <button className="flex-1 truncate text-left" onClick={() => openConversation(c.id)} title={c.title}>
              {c.source === "telegram" ? "📱 " : ""}{c.title}
            </button>
            <button className="opacity-0 group-hover:opacity-100 text-dim hover:text-danger" aria-label="Delete conversation"
              onClick={async () => { await api.del(`/api/conversations/${c.id}`); if (c.id === conversationId) openConversation(null); convs.reload(); }}>
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </aside>
      <section className="panel flex min-h-0 flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {!messages.length && <Empty title="How can I help?">Type below, press the mic, or say “Hey Jarvis”. You can attach images for Jarvis to look at.</Empty>}
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${m.role === "user" ? "bg-accent/15 border border-accent/30" : "bg-panel-2 border border-line"}`}>
                {m.images?.map((b, i) => <img key={i} src={`data:image/png;base64,${b}`} className="mb-2 max-h-40 rounded" alt="Attachment" />)}
                {m.tools.length > 0 && <div className="mb-2 flex flex-col gap-1">{m.tools.map((t, i) => <ToolChip key={i} t={t} />)}</div>}
                <Text text={m.text} />
                {m.pending && !m.text && <span className="inline-flex gap-1"><span className="h-2 w-2 rounded-full bg-accent anim-pulse-fast" /><span className="h-2 w-2 rounded-full bg-accent anim-pulse" /></span>}
                {m.error && <p className="mt-1 flex items-center gap-1 text-sm text-danger"><AlertCircle size={14} />{m.error}</p>}
              </div>
            </div>
          ))}
          <div ref={end} />
        </div>
        <div className="border-t border-line p-3">
          {images.length > 0 && (
            <div className="mb-2 flex gap-2">{images.map((b, i) => (
              <button key={i} onClick={() => setImages(images.filter((_, j) => j !== i))} title="Remove"><img src={`data:image/png;base64,${b}`} className="h-14 rounded border border-line" alt="Attachment preview" /></button>
            ))}</div>
          )}
          <div className="flex gap-2">
            <label className="grid h-10 w-10 cursor-pointer place-items-center rounded-lg border border-line text-dim hover:text-accent" title="Attach image">
              <ImagePlus size={18} /><input type="file" accept="image/*" multiple hidden onChange={(e) => attach(e.target.files)} />
            </label>
            <input className="input" value={text} placeholder="Message Jarvis…" aria-label="Chat message" onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && text.trim()) { send(text.trim(), images.length ? images : undefined); setText(""); setImages([]); } }} />
          </div>
        </div>
      </section>
    </div>
  );
}
