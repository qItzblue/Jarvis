import { ArrowDown, ArrowUp, Play, Plus, Save, Trash2, Workflow } from "lucide-react";
import { useState } from "react";
import { Button, Card, Empty, Toggle, useData } from "../components/ui";
import { api } from "../lib/api";
import { useJarvis } from "../lib/store";

type Step = { tool?: string; args?: Record<string, unknown>; say?: string; wait?: number };
const blank = { name: "", phrase: "", steps: [] as Step[], enabled: true };

function StepEditor({ step, tools, onChange }: { step: Step; tools: any[]; onChange: (s: Step) => void }) {
  const kind = step.say !== undefined ? "say" : step.wait !== undefined ? "wait" : "tool";
  const [argsText, setArgsText] = useState(JSON.stringify(step.args ?? {}));
  return (
    <div className="flex flex-1 flex-wrap items-center gap-2">
      <select className="input !w-28" value={kind} aria-label="Step type" onChange={(e) => onChange(e.target.value === "say" ? { say: "" } : e.target.value === "wait" ? { wait: 2 } : { tool: tools[0]?.name, args: {} })}>
        <option value="tool">Action</option><option value="say">Say</option><option value="wait">Wait</option>
      </select>
      {kind === "say" && <input className="input flex-1" value={step.say} placeholder="What Jarvis says" aria-label="Say text" onChange={(e) => onChange({ say: e.target.value })} />}
      {kind === "wait" && <input className="input !w-24" type="number" value={step.wait} aria-label="Seconds" onChange={(e) => onChange({ wait: +e.target.value })} />}
      {kind === "tool" && <>
        <select className="input flex-1" value={step.tool} aria-label="Action" onChange={(e) => onChange({ ...step, tool: e.target.value })}>
          {tools.map((t) => <option key={t.name} value={t.name}>{t.name.replace("__", " · ")} — {t.description}</option>)}
        </select>
        <input className="input flex-1 font-mono text-xs" value={argsText} aria-label="Arguments JSON" placeholder='{"level": 20}'
          onChange={(e) => { setArgsText(e.target.value); try { onChange({ ...step, args: JSON.parse(e.target.value || "{}") }); } catch { /* typing */ } }} />
      </>}
    </div>
  );
}

export function Routines() {
  const { toast } = useJarvis();
  const routines = useData<any[]>(() => api.get("/api/p/routines"));
  const tools = useData<any[]>(() => api.get("/api/tools"));
  const [edit, setEdit] = useState<any>(null);

  const save = async () => {
    const saved = edit.id ? await api.put(`/api/p/routines/${edit.id}`, edit) : await api.post("/api/p/routines", edit);
    setEdit(saved); routines.reload(); toast("Routine saved");
  };
  const move = (i: number, d: number) => {
    const steps = [...edit.steps]; const [s] = steps.splice(i, 1); steps.splice(i + d, 0, s); setEdit({ ...edit, steps });
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
      <Card title="Routines" icon={<Workflow size={14} />} actions={<Button variant="primary" onClick={() => setEdit({ ...blank })} aria-label="New routine"><Plus size={14} /></Button>}>
        {!routines.data?.length && <Empty title="No routines" />}
        {routines.data?.map((r) => (
          <button key={r.id} onClick={() => setEdit(r)} className={`rounded-lg border px-3 py-2 text-left ${edit?.id === r.id ? "border-accent bg-accent/10" : "border-line hover:border-accent/50"}`}>
            <p className="font-medium">{r.name}</p><p className="text-xs text-dim">“{r.phrase}” · {r.steps.length} steps{!r.enabled && " · off"}</p>
          </button>
        ))}
      </Card>
      <Card title={edit ? (edit.id ? "Edit routine" : "New routine") : "Builder"} actions={edit && <>
        {edit.id && <Button onClick={async () => toast("Routine finished", (await api.post(`/api/p/routines/${edit.id}/run`)).result)}><Play size={14} /> Test run</Button>}
        {edit.id && <Button variant="ghost" aria-label="Delete routine" onClick={async () => { await api.del(`/api/p/routines/${edit.id}`); setEdit(null); routines.reload(); }}><Trash2 size={14} /></Button>}
        <Button variant="primary" onClick={save}><Save size={14} /> Save</Button></>}>
        {!edit ? <Empty title="Pick a routine or create one">A routine runs several actions when you say its trigger phrase, e.g. “good night” → lights off, volume down, say goodnight.</Empty> : (
          <div className="flex flex-col gap-3">
            <div className="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
              <input className="input" placeholder="Name" value={edit.name} aria-label="Routine name" onChange={(e) => setEdit({ ...edit, name: e.target.value })} />
              <input className="input" placeholder="Trigger phrase" value={edit.phrase} aria-label="Trigger phrase" onChange={(e) => setEdit({ ...edit, phrase: e.target.value })} />
              <Toggle checked={edit.enabled} label="Enabled" onChange={(v) => setEdit({ ...edit, enabled: v })} />
            </div>
            <div className="label">When I say “{edit.phrase || "…"}”, do:</div>
            {edit.steps.map((s: Step, i: number) => (
              <div key={i} className="flex items-center gap-2 rounded-lg border border-line bg-panel-2 p-2">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-accent/20 font-mono text-xs text-accent">{i + 1}</span>
                <StepEditor key={`${i}-${s.tool ?? s.say ?? s.wait}`} step={s} tools={tools.data ?? []} onChange={(ns) => setEdit({ ...edit, steps: edit.steps.map((x: Step, j: number) => j === i ? ns : x) })} />
                <button disabled={i === 0} onClick={() => move(i, -1)} aria-label="Move up" className="text-dim hover:text-ink disabled:opacity-30"><ArrowUp size={14} /></button>
                <button disabled={i === edit.steps.length - 1} onClick={() => move(i, 1)} aria-label="Move down" className="text-dim hover:text-ink disabled:opacity-30"><ArrowDown size={14} /></button>
                <button onClick={() => setEdit({ ...edit, steps: edit.steps.filter((_: Step, j: number) => j !== i) })} aria-label="Remove step" className="text-dim hover:text-danger"><Trash2 size={14} /></button>
              </div>
            ))}
            <Button onClick={() => setEdit({ ...edit, steps: [...edit.steps, { say: "" }] })} className="w-fit"><Plus size={14} /> Add step</Button>
          </div>
        )}
      </Card>
    </div>
  );
}
