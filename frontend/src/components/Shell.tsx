import {
  AlertTriangle, Bell, Bot, Brain, Camera, Check, Cpu, Home, LayoutDashboard, ListTodo, Maximize2, MessageSquare,
  Mic, MicOff, Minimize2, Newspaper, Puzzle, Send, Settings, Square, Volume2, VolumeX, Workflow, X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useJarvis } from "../lib/store";
import { toolLabel } from "../lib/chat";
import { Button } from "./ui";

export const TABS = [
  { id: "home", label: "Home", icon: LayoutDashboard },
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "tasks", label: "Tasks", icon: ListTodo },
  { id: "notes", label: "Notes & Memory", icon: Brain },
  { id: "smarthome", label: "Smart Home", icon: Home },
  { id: "system", label: "System", icon: Cpu },
  { id: "info", label: "Info Center", icon: Newspaper },
  { id: "routines", label: "Routines", icon: Workflow },
  { id: "plugins", label: "Plugins", icon: Puzzle },
  { id: "vision", label: "Vision", icon: Camera },
  { id: "settings", label: "Settings", icon: Settings },
] as const;
export type TabId = (typeof TABS)[number]["id"];

export function Sidebar({ tab, setTab }: { tab: TabId; setTab: (t: TabId) => void }) {
  const { micOn, wakeOn, orb } = useJarvis();
  return (
    <nav className="panel !rounded-none !border-y-0 !border-l-0 flex w-16 lg:w-52 shrink-0 flex-col gap-1 p-2" aria-label="Main">
      <div className="flex items-center gap-2 px-2 py-3">
        <Bot className="text-accent" size={24} />
        <span className="hidden lg:block font-mono text-sm tracking-[0.3em] text-accent">J.A.R.V.I.S</span>
      </div>
      {TABS.map((t) => (
        <button key={t.id} onClick={() => setTab(t.id)} title={t.label} aria-current={tab === t.id ? "page" : undefined}
          className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${tab === t.id
            ? "bg-accent/10 text-accent border border-accent/40" : "text-dim hover:text-ink hover:bg-panel-2 border border-transparent"}`}>
          <t.icon size={18} /><span className="hidden lg:inline">{t.label}</span>
        </button>
      ))}
      <div className="mt-auto flex items-center gap-2 px-3 py-2 text-xs text-dim" title="Microphone status">
        <span className={`h-2 w-2 rounded-full ${orb === "listening" ? "bg-danger anim-pulse-fast" : micOn ? "bg-ok" : "bg-line"}`} />
        <span className="hidden lg:inline">{orb === "listening" ? "Listening…" : wakeOn ? "Waiting for “Hey Jarvis”" : micOn ? "Mic ready" : "Mic off"}</span>
      </div>
    </nav>
  );
}

export function TopBar({ mini, setMini }: { mini: boolean; setMini: (m: boolean) => void }) {
  const { connected, status, micOn, muted, setMuted, toasts } = useJarvis();
  const [now, setNow] = useState(new Date());
  const [cameraOn, setCameraOn] = useState(false);
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t); }, []);
  useEffect(() => {
    const h = (e: Event) => setCameraOn((e as CustomEvent).detail);
    window.addEventListener("jarvis-camera", h);
    return () => window.removeEventListener("jarvis-camera", h);
  }, []);
  return (
    <header className="flex items-center gap-4 border-b border-line px-4 py-2">
      <div className="font-mono">
        <span className="text-lg text-accent">{now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
        <span className="ml-3 text-xs text-dim hidden sm:inline">{now.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" })}</span>
      </div>
      <div className="ml-auto flex items-center gap-3 text-xs">
        {cameraOn && <span className="flex items-center gap-1 rounded border border-danger/50 px-2 py-0.5 text-danger" title="Camera in use"><Camera size={14} /> CAM</span>}
        {micOn && <span className="flex items-center gap-1 rounded border border-danger/50 px-2 py-0.5 text-danger" title="Microphone in use"><Mic size={14} /> MIC</span>}
        <span className={`flex items-center gap-1 ${connected ? "text-ok" : "text-danger"}`} title="Backend connection">
          <span className={`h-2 w-2 rounded-full ${connected ? "bg-ok" : "bg-danger"}`} />
          <span className="hidden md:inline">{connected ? `${status?.provider ?? ""}${status && !status.llm_configured ? " · no key" : ""}` : "offline"}</span>
        </span>
        <button className="text-dim hover:text-ink" onClick={() => setMuted(!muted)} title={muted ? "Unmute voice" : "Mute voice"} aria-label={muted ? "Unmute voice" : "Mute voice"}>
          {muted ? <VolumeX size={18} /> : <Volume2 size={18} />}
        </button>
        <span className="relative text-dim" title={`${toasts.length} notifications`}><Bell size={18} />
          {toasts.length > 0 && <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-warn" />}</span>
        <button className="text-dim hover:text-ink" onClick={() => setMini(!mini)} title={mini ? "Full window" : "Mini mode"} aria-label="Toggle mini mode">
          {mini ? <Maximize2 size={18} /> : <Minimize2 size={18} />}
        </button>
      </div>
    </header>
  );
}

export function CommandBar() {
  const { send, busy, cancel, listen, orb, level, micOn, setMicOn } = useJarvis();
  const [text, setText] = useState("");
  const ref = useRef<HTMLInputElement>(null);
  const submit = () => { if (text.trim()) { send(text.trim()); setText(""); } };
  const bars = Array.from({ length: 24 }, (_, i) => orb === "listening" ? Math.max(3, Math.min(28, level * 400 * (0.4 + Math.abs(Math.sin(i * 1.7 + Date.now() / 120))))) : 3);
  return (
    <div className="border-t border-line p-3">
      <div className="panel flex items-center gap-2 px-2 py-1.5">
        <button onClick={() => void listen()} title={`Push to talk (${window.jarvisDesktop?.hotkey ?? "Ctrl+Shift+Space"})`} aria-label="Push to talk"
          className={`grid h-10 w-10 shrink-0 place-items-center rounded-full border transition ${orb === "listening" ? "border-danger bg-danger/20 text-danger" : "border-accent/50 text-accent hover:bg-accent/10"}`}>
          <Mic size={18} />
        </button>
        {orb === "listening" ? (
          <div className="flex h-10 flex-1 items-center gap-[3px]" aria-label="Listening">
            {bars.map((h, i) => <span key={i} className="w-1 rounded bg-accent" style={{ height: h }} />)}
            <span className="ml-3 text-sm text-dim">Listening… speak now</span>
          </div>
        ) : (
          <input ref={ref} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="Ask Jarvis anything…" aria-label="Message Jarvis"
            className="h-10 flex-1 bg-transparent px-2 outline-none placeholder:text-dim" />
        )}
        {busy ? (
          <Button variant="ghost" onClick={cancel} title="Stop" aria-label="Stop"><Square size={16} /></Button>
        ) : (
          <Button variant="primary" onClick={submit} disabled={!text.trim()} title="Send" aria-label="Send"><Send size={16} /></Button>
        )}
        <Button variant="ghost" onClick={() => void setMicOn(!micOn)} title={micOn ? "Turn microphone off" : "Turn microphone on"} aria-label="Toggle microphone">
          {micOn ? <Mic size={16} /> : <MicOff size={16} />}
        </Button>
      </div>
    </div>
  );
}

export function Confirmations() {
  const { confirms, respond } = useJarvis();
  if (!confirms.length) return null;
  return (
    <div className="fixed inset-x-0 top-16 z-40 flex flex-col items-center gap-2 px-4" role="alertdialog" aria-label="Confirmation needed">
      {confirms.map((c) => (
        <div key={c.id} className="panel w-full max-w-lg border-warn/60 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 shrink-0 text-warn" size={20} />
            <div className="min-w-0 flex-1">
              <p className="font-semibold">Confirm action</p>
              <p className="text-sm">{c.title}</p>
              {c.details?.tool && <p className="mt-1 font-mono text-xs text-dim break-all">{toolLabel(c.details.tool)} {JSON.stringify(c.details.args)}</p>}
              <p className="mt-1 text-xs text-dim">Say “yes” or “no”, or use the buttons. Requested from {c.details?.source ?? "assistant"}.</p>
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => respond(c.id, false)}><X size={16} /> Deny</Button>
            <Button variant="primary" onClick={() => respond(c.id, true)}><Check size={16} /> Approve</Button>
          </div>
        </div>
      ))}
    </div>
  );
}

export function Toasts() {
  const { toasts, dismissToast } = useJarvis();
  const color: Record<string, string> = { warning: "border-warn/60", alarm: "border-accent", error: "border-danger/60" };
  return (
    <div className="fixed bottom-24 right-4 z-50 flex w-80 flex-col gap-2" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`panel p-3 ${color[t.level] ?? ""}`}>
          <div className="flex items-start justify-between gap-2">
            <div><p className="text-sm font-semibold">{t.title}</p>{t.body && <p className="text-xs text-dim">{t.body}</p>}</div>
            <button onClick={() => dismissToast(t.id)} aria-label="Dismiss" className="text-dim hover:text-ink"><X size={14} /></button>
          </div>
        </div>
      ))}
    </div>
  );
}
