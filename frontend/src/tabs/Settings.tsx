import { Download, Play } from "lucide-react";
import { useMemo, useState } from "react";
import { SettingField } from "../components/SettingField";
import { Button, Card, Spinner, useData } from "../components/ui";
import { api } from "../lib/api";
import { useJarvis } from "../lib/store";

const GROUPS: { title: string; prefix: string[] }[] = [
  { title: "AI provider", prefix: ["llm.", "anthropic.", "nanogpt.", "google.", "gemini."] },
  { title: "Personality", prefix: ["assistant."] },
  { title: "Voice", prefix: ["voice."] },
  { title: "Appearance", prefix: ["ui."] },
];

export function Settings() {
  const { bumpSettings, refreshStatus, toast, speaker, wakeOn, setWakeOn, status } = useJarvis();
  const rows = useData<any[]>(() => api.get("/api/settings"));
  const [draft, setDraft] = useState<Record<string, any>>({});
  const values = useMemo(() => ({ ...Object.fromEntries((rows.data ?? []).map((r) => [r.key, r.value])), ...draft }), [rows.data, draft]);

  const save = async () => {
    rows.setData(await api.put("/api/settings", { values: draft }));
    setDraft({});
    bumpSettings(); void refreshStatus(); toast("Settings saved");
    if ("voice.wake_word" in draft) void setWakeOn(!!draft["voice.wake_word"]);
  };

  if (rows.loading) return <Spinner />;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Button variant="primary" onClick={save} disabled={!Object.keys(draft).length}>Save changes</Button>
        <Button onClick={() => { speaker.stop(); speaker.engine = values["voice.tts_engine"]; speaker.rate = Number(values["voice.speed"] || 1); speaker.enqueue(`Good evening, ${values["assistant.user_name"]}. All systems are online.`); }}>
          <Play size={14} /> Preview voice</Button>
        <a className="ml-auto" href="#" onClick={async (e) => {
          e.preventDefault();
          const blob = new Blob([JSON.stringify(await api.get("/api/export"), null, 2)], { type: "application/json" });
          const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "jarvis-export.json"; a.click();
        }}><Button variant="ghost"><Download size={14} /> Export my data</Button></a>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {GROUPS.map((g) => (
          <Card key={g.title} title={g.title}>
            {(rows.data ?? []).filter((r) => g.prefix.some((p) => r.key.startsWith(p))).map((f) => (
              <SettingField key={f.key} f={f} value={values[f.key]} onChange={(v) => setDraft({ ...draft, [f.key]: v })} />
            ))}
            {g.title === "Voice" && (
              <div className="text-xs text-dim">
                Local speech recognition: {status?.voice.stt ? "installed ✓" : "not installed (pip install -r backend/requirements-voice.txt)"} ·
                Wake word: {status?.voice.wake_word ? (wakeOn ? "listening ✓" : "installed") : "not installed"} ·
                Push-to-talk hotkey: <span className="font-mono">{window.jarvisDesktop?.hotkey ?? "Ctrl+Shift+Space"}</span>
              </div>
            )}
          </Card>
        ))}
        <Card title="Privacy">
          <ul className="list-disc space-y-1 pl-5 text-sm text-dim">
            <li>Conversations, notes, memory and settings are stored only in <span className="font-mono">data/jarvis.db</span> on this computer.</li>
            <li>Text is sent only to the AI provider you chose, and to the services of plugins you enable.</li>
            <li>The microphone and camera are off until you turn them on, and the top bar shows when they're live.</li>
            <li>Sending email, deleting, running scripts and power actions always ask first.</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
