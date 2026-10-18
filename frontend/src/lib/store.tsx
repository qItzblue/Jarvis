import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, WS_BASE } from "./api";
import { NO, YES } from "./audio";
import { applyEvent, ChatMessage, userMessage } from "./chat";
import { Mic } from "./mic";
import { Speaker } from "./speaker";

export type OrbState = "idle" | "listening" | "thinking" | "speaking";
export interface Confirm { id: string; title: string; details: any }
export interface Toast { id: number; title: string; body?: string; level: string }
export interface Status {
  provider: string; llm_configured: boolean; assistant_name: string;
  voice: { stt: boolean; wake_word: boolean; tts: { engine: string } };
  plugins: Record<string, string>;
}

interface JarvisState {
  connected: boolean;
  status: Status | null;
  refreshStatus: () => Promise<void>;
  messages: ChatMessage[];
  conversationId: number | null;
  openConversation: (id: number | null) => Promise<void>;
  send: (text: string, images?: string[]) => void;
  cancel: () => void;
  orb: OrbState;
  busy: boolean;
  confirms: Confirm[];
  respond: (id: string, approved: boolean) => void;
  toasts: Toast[];
  dismissToast: (id: number) => void;
  toast: (title: string, body?: string, level?: string) => void;
  timers: { id: number; label: string; ends_at: number }[];
  focus: any;
  // voice
  micOn: boolean;
  setMicOn: (on: boolean) => Promise<void>;
  wakeOn: boolean;
  setWakeOn: (on: boolean) => Promise<void>;
  listen: () => Promise<void>;
  stopSpeaking: () => void;
  level: number;
  muted: boolean;
  setMuted: (m: boolean) => void;
  speaker: Speaker;
  settingsVersion: number;
  bumpSettings: () => void;
}

const Ctx = createContext<JarvisState | null>(null);
export const useJarvis = () => {
  const c = useContext(Ctx);
  if (!c) throw new Error("useJarvis outside provider");
  return c;
};

export function JarvisProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<Status | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [recording, setRecording] = useState(false);
  const [confirms, setConfirms] = useState<Confirm[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [timers, setTimers] = useState<JarvisState["timers"]>([]);
  const [focus, setFocus] = useState<any>(null);
  const [micOn, setMicOnState] = useState(false);
  const [wakeOn, setWakeOnState] = useState(false);
  const [level, setLevel] = useState(0);
  const [muted, setMutedState] = useState(false);
  const [settingsVersion, setSettingsVersion] = useState(0);

  const ws = useRef<WebSocket | null>(null);
  const convRef = useRef<number | null>(null);
  const confirmsRef = useRef<Confirm[]>([]);
  const speaker = useRef(new Speaker()).current;
  const mic = useRef(new Mic()).current;
  const toastId = useRef(0);

  confirmsRef.current = confirms;
  convRef.current = conversationId;

  const toast = useCallback((title: string, body?: string, level = "info") => {
    const id = ++toastId.current;
    setToasts((t) => [...t.slice(-4), { id, title, body, level }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), level === "alarm" ? 15000 : 6000);
  }, []);

  const refreshStatus = useCallback(async () => {
    try { setStatus(await api.get<Status>("/api/status")); } catch { setStatus(null); }
  }, []);

  // --- websocket ----------------------------------------------------------
  useEffect(() => {
    let stopped = false;
    let retry: ReturnType<typeof setTimeout>;
    const connect = () => {
      const sock = new WebSocket(`${WS_BASE}/ws`);
      ws.current = sock;
      sock.onopen = () => { setConnected(true); void refreshStatus(); };
      sock.onclose = () => {
        setConnected(false);
        if (!stopped) retry = setTimeout(connect, 2000);
      };
      sock.onmessage = (m) => {
        const ev = JSON.parse(m.data);
        switch (ev.type) {
          case "start": setConversationId(ev.conversation_id); setBusy(true); break;
          case "sentence": speaker.enqueue(ev.text); break;
          case "done": case "cancelled": setBusy(false); break;
          case "error": setBusy(false); speaker.enqueue("Sorry, something went wrong."); break;
          case "confirm_request":
            setConfirms((c) => [...c, { id: ev.id, title: ev.title, details: ev.details }]);
            speaker.enqueue(`I need your confirmation: ${ev.title}`);
            break;
          case "confirm_closed": setConfirms((c) => c.filter((x) => x.id !== ev.id)); break;
          case "alert":
            toast(ev.title, ev.body, ev.level);
            if (ev.level === "alarm" || ev.level === "warning") speaker.enqueue(`${ev.title}. ${ev.body ?? ""}`);
            break;
          case "greet": speaker.enqueue(`Welcome back, ${ev.name}.`); toast(`Welcome back, ${ev.name}`); break;
          case "timers": setTimers(ev.timers); break;
          case "focus": setFocus(ev.session); break;
        }
        if (["start", "token", "tool", "error", "done", "cancelled"].includes(ev.type)) {
          setMessages((msgs) => applyEvent(msgs, ev));
        }
      };
    };
    connect();
    speaker.onState = setSpeaking;
    return () => { stopped = true; clearTimeout(retry); ws.current?.close(); };
  }, [refreshStatus, speaker, toast]);

  // --- settings that affect voice ----------------------------------------
  useEffect(() => {
    api.get<any[]>("/api/settings").then((rows) => {
      const v = Object.fromEntries(rows.map((r) => [r.key, r.value]));
      speaker.engine = v["voice.tts_engine"] || "browser";
      speaker.rate = Number(v["voice.speed"] || 1);
      document.documentElement.dataset.theme = v["ui.theme"] || "dark";
      document.documentElement.dataset.motion = v["ui.reduced_motion"] ? "reduced" : "full";
      if (v["voice.wake_word"] && !wakeOn) void setWakeOn(true);
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connected, settingsVersion]);

  const sendRaw = (msg: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(msg));
    else toast("Not connected", "The Jarvis backend isn't running.", "warning");
  };

  const send = useCallback((text: string, images?: string[]) => {
    if (!text.trim()) return;
    speaker.stop();
    setMessages((m) => [...m, userMessage(text, images)]);
    setBusy(true);
    sendRaw({ type: "chat", text, conversation_id: convRef.current, images });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speaker]);

  const cancel = useCallback(() => { speaker.stop(); sendRaw({ type: "cancel" }); setBusy(false); },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [speaker]);

  const respond = useCallback((id: string, approved: boolean) => {
    sendRaw({ type: "confirm", id, approved });
    setConfirms((c) => c.filter((x) => x.id !== id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openConversation = useCallback(async (id: number | null) => {
    setConversationId(id);
    if (id === null) { setMessages([]); return; }
    const conv = await api.get(`/api/conversations/${id}`);
    setMessages(conv.messages.map((m: any) => ({ id: String(m.id), role: m.role, text: m.content, tools: [] })));
  }, []);

  // --- voice ---------------------------------------------------------------
  const handleUtterance = useCallback(async (wav: Blob) => {
    const form = new FormData();
    form.append("audio", wav, "speech.wav");
    try {
      const { text } = await api.post<{ text: string }>("/api/stt", form);
      if (!text) return;
      const pending = confirmsRef.current[0];
      if (pending && (YES.test(text) || NO.test(text))) { respond(pending.id, YES.test(text)); return; }
      send(text);
    } catch (e: any) {
      toast("Speech recognition failed", e.message, "warning");
    }
  }, [respond, send, toast]);

  useEffect(() => {
    mic.onLevel = (l) => setLevel(l);
    mic.onRecordingChange = setRecording;
    mic.onUtterance = (w) => void handleUtterance(w);
    mic.onWake = () => { speaker.stop(); void mic.record(); };
    mic.onWakeUnavailable = (msg) => { toast("Wake word unavailable", msg, "warning"); setWakeOnState(false); };
  }, [mic, speaker, handleUtterance, toast]);

  const setMicOn = useCallback(async (on: boolean) => {
    try {
      if (on) await mic.start(); else { mic.stop(); setWakeOnState(false); }
      setMicOnState(on);
    } catch (e: any) { toast("Microphone unavailable", e.message, "warning"); }
  }, [mic, toast]);

  const setWakeOn = useCallback(async (on: boolean) => {
    if (on) await setMicOn(true);
    mic.setWakeWord(on);
    setWakeOnState(on);
  }, [mic, setMicOn]);

  const listen = useCallback(async () => {
    speaker.stop(); // barge-in
    if (mic.isRecording) { mic.finish(true); return; }
    try { await mic.record(); setMicOnState(true); } catch (e: any) { toast("Microphone unavailable", e.message, "warning"); }
  }, [mic, speaker, toast]);

  useEffect(() => window.jarvisDesktop?.onPushToTalk(() => void listen()), [listen]);

  const setMuted = (m: boolean) => { speaker.muted = m; if (m) speaker.stop(); setMutedState(m); };

  const orb: OrbState = recording ? "listening" : speaking ? "speaking" : busy ? "thinking" : "idle";

  return (
    <Ctx.Provider value={{
      connected, status, refreshStatus, messages, conversationId, openConversation, send, cancel, orb, busy,
      confirms, respond, toasts, dismissToast: (id) => setToasts((t) => t.filter((x) => x.id !== id)), toast,
      timers, focus, micOn, setMicOn, wakeOn, setWakeOn, listen, stopSpeaking: () => speaker.stop(), level,
      muted, setMuted, speaker, settingsVersion, bumpSettings: () => setSettingsVersion((v) => v + 1),
    }}>
      {children}
    </Ctx.Provider>
  );
}

declare global {
  interface Window {
    jarvisDesktop?: { onPushToTalk: (cb: () => void) => () => void; setMiniMode: (on: boolean) => Promise<void>; hotkey: string };
  }
}
