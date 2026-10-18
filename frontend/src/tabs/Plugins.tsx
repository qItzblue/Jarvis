import * as Icons from "lucide-react";
import { Search, ShieldAlert, X } from "lucide-react";
import { useState } from "react";
import { SettingField } from "../components/SettingField";
import { Badge, Button, Spinner, Toggle, useData } from "../components/ui";
import { api } from "../lib/api";
import { useJarvis } from "../lib/store";

const CATS = ["all", "core", "productivity", "info", "computer", "home", "vision", "automation", "remote", "extras"];

function Icon({ name }: { name: string }) {
  const key = name.split("-").map((p) => p[0].toUpperCase() + p.slice(1)).join("");
  const C = (Icons as any)[key] ?? Icons.Puzzle;
  return <C size={20} />;
}

export function Plugins() {
  const { refreshStatus, toast } = useJarvis();
  const plugins = useData<any[]>(() => api.get("/api/plugins"));
  const [cat, setCat] = useState("all");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<any>(null);
  const [draft, setDraft] = useState<Record<string, any>>({});

  const update = async (name: string, body: object) => {
    const p = await api.put(`/api/plugins/${name}`, body);
    plugins.setData((list) => list!.map((x) => (x.name === name ? p : x)));
    if (open?.name === name) setOpen(p);
    void refreshStatus();
    return p;
  };
  const list = (plugins.data ?? []).filter((p) => (cat === "all" || p.category === cat) && `${p.title} ${p.description}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative"><Search size={14} className="absolute left-3 top-3 text-dim" />
          <input className="input !pl-8 !w-64" placeholder="Search plugins" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search plugins" /></div>
        {CATS.map((c) => <Button key={c} variant={cat === c ? "primary" : "ghost"} onClick={() => setCat(c)} className="capitalize">{c}</Button>)}
      </div>
      {plugins.loading && <Spinner />}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {list.map((p) => (
          <div key={p.name} className="panel flex flex-col gap-2 p-4 cursor-pointer hover:border-accent/60" onClick={() => { setOpen(p); setDraft(Object.fromEntries(p.settings.map((s: any) => [s.key, s.value]))); }}>
            <div className="flex items-center gap-3">
              <span className="text-accent"><Icon name={p.icon} /></span>
              <span className="flex-1 font-medium">{p.title}</span>
              <span onClick={(e) => e.stopPropagation()}><Toggle checked={p.enabled} label={`Enable ${p.title}`} onChange={(v) => update(p.name, { enabled: v })} /></span>
            </div>
            <p className="text-sm text-dim line-clamp-2">{p.description}</p>
            <div className="mt-auto flex items-center gap-2"><Badge status={p.status} /><span className="label !text-[10px]">{p.tools.length} tools</span></div>
          </div>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 z-30 flex justify-end bg-black/40" onClick={() => setOpen(null)}>
          <aside className="panel h-full w-full max-w-md overflow-y-auto !rounded-none p-5" onClick={(e) => e.stopPropagation()} aria-label={`${open.title} settings`}>
            <div className="flex items-center gap-3"><span className="text-accent"><Icon name={open.icon} /></span><h2 className="flex-1 text-lg font-semibold">{open.title}</h2>
              <button onClick={() => setOpen(null)} aria-label="Close"><X size={18} /></button></div>
            <p className="mt-2 text-sm text-dim">{open.description}</p>
            <div className="mt-3 flex items-center gap-2"><Badge status={open.status} />
              <Toggle checked={open.enabled} label="Enabled" onChange={(v) => update(open.name, { enabled: v })} /></div>
            {open.missing_deps.length > 0 && (
              <p className="mt-3 rounded-lg border border-warn/40 bg-warn/10 p-2 text-sm">Install: <code className="font-mono">pip install -r backend/requirements-extras.txt</code> (needs {open.missing_deps.join(", ")})</p>
            )}
            {open.settings.length > 0 && (
              <div className="mt-4 flex flex-col gap-3">
                <h3 className="label">Settings</h3>
                {open.settings.map((f: any) => <SettingField key={f.key} f={f} value={draft[f.key]} onChange={(v) => setDraft({ ...draft, [f.key]: v })} />)}
                <Button variant="primary" onClick={async () => { await update(open.name, { settings: draft }); toast(`${open.title} saved`); }}>Save settings</Button>
                {(open.name === "calendar" || open.name === "gmail") && open.status === "ok" && (
                  <Button onClick={async () => { const r = await api.post("/api/p/calendar/connect"); toast(r.error ? "Google connect failed" : "Google connected", r.error); }}>Connect Google account</Button>
                )}
              </div>
            )}
            <div className="mt-5 flex flex-col gap-1">
              <h3 className="label">What Jarvis can do with it</h3>
              {open.tools.map((t: any) => (
                <p key={t.name} className="text-sm">{t.confirm && <ShieldAlert size={13} className="mr-1 inline text-warn" aria-label="Needs confirmation" />}{t.description}</p>
              ))}
              {!open.tools.length && <p className="text-sm text-dim">Runs in the background.</p>}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
