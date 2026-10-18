import { Bot, Check, KeyRound, Mic, Volume2 } from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";
import { useJarvis } from "../lib/store";
import { Button } from "./ui";

export function Onboarding({ done }: { done: () => void }) {
  const { setMicOn, speaker, refreshStatus, bumpSettings } = useJarvis();
  const [step, setStep] = useState(0);
  const [provider, setProvider] = useState("anthropic");
  const [key, setKey] = useState("");
  const [name, setName] = useState("sir");
  const [engine, setEngine] = useState("browser");
  const keyField = { anthropic: "anthropic.api_key", nanogpt: "nanogpt.api_key", gemini: "google.api_key" }[provider]!;

  const steps = [
    { icon: Bot, title: "Welcome", body: (
      <><p>I'm Jarvis, your personal assistant. I can chat, control your computer, manage your day and run your smart home.</p>
        <label className="mt-4 flex flex-col gap-1 text-sm text-dim">What should I call you?<input className="input" value={name} onChange={(e) => setName(e.target.value)} /></label></>) },
    { icon: KeyRound, title: "Connect a brain", body: (
      <><p className="text-sm text-dim">Pick an AI provider and paste its API key. It's stored only on this computer.</p>
        <div className="mt-3 flex gap-2">{["anthropic", "nanogpt", "gemini"].map((p) => <Button key={p} variant={provider === p ? "primary" : "subtle"} onClick={() => setProvider(p)} className="capitalize">{p === "anthropic" ? "Claude" : p === "nanogpt" ? "NanoGPT" : "Gemini"}</Button>)}</div>
        <input className="input mt-3" type="password" placeholder="API key" value={key} onChange={(e) => setKey(e.target.value)} aria-label="API key" />
        <p className="mt-1 text-xs text-dim">You can skip this if the key is already in your .env file.</p></>) },
    { icon: Mic, title: "Microphone", body: (
      <><p className="text-sm text-dim">Allow the microphone to talk to me. It's only active when you press the mic button, the hotkey, or enable “Hey Jarvis”.</p>
        <Button className="mt-3" onClick={() => setMicOn(true)}><Mic size={14} /> Allow microphone</Button></>) },
    { icon: Volume2, title: "Pick a voice", body: (
      <><div className="flex gap-2">{["browser", "piper", "elevenlabs"].map((e) => <Button key={e} variant={engine === e ? "primary" : "subtle"} onClick={() => setEngine(e)} className="capitalize">{e === "browser" ? "Built-in" : e}</Button>)}</div>
        <p className="mt-2 text-xs text-dim">Built-in works everywhere. Piper is a local neural voice (needs a model file). ElevenLabs is a paid cloud voice.</p>
        <Button className="mt-3" onClick={() => { speaker.engine = engine; speaker.enqueue(`Hello ${name}. All systems are online.`); }}>▶ Preview</Button></>) },
  ];

  const finish = async () => {
    const values: Record<string, unknown> = { "llm.provider": provider, "assistant.user_name": name, "voice.tts_engine": engine };
    if (key) values[keyField] = key;
    try { await api.put("/api/settings", { values }); } catch { /* backend offline – settings can be done later */ }
    bumpSettings(); void refreshStatus(); done();
  };
  const S = steps[step];
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-bg/90 p-4 backdrop-blur">
      <div className="panel w-full max-w-lg p-6">
        <div className="mb-4 flex gap-1">{steps.map((_, i) => <span key={i} className={`h-1 flex-1 rounded ${i <= step ? "bg-accent" : "bg-line"}`} />)}</div>
        <div className="flex items-center gap-3"><S.icon className="text-accent" /><h2 className="text-xl font-semibold">{S.title}</h2></div>
        <div className="mt-3">{S.body}</div>
        <div className="mt-6 flex justify-between">
          <Button variant="ghost" onClick={step ? () => setStep(step - 1) : done}>{step ? "Back" : "Skip setup"}</Button>
          {step < steps.length - 1 ? <Button variant="primary" onClick={() => setStep(step + 1)}>Next</Button>
            : <Button variant="primary" onClick={finish}><Check size={14} /> Finish</Button>}
        </div>
      </div>
    </div>
  );
}
