import { AppWindow, Lock, Moon, Pause, Power, RotateCcw, SkipBack, SkipForward, Sun, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button, Card, Ring, useData } from "../components/ui";
import { api, isError } from "../lib/api";

function LineChart({ series }: { series: { values: number[]; color: string; label: string }[] }) {
  const w = 600, h = 140;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-36 w-full" role="img" aria-label="CPU and memory over time">
      {[25, 50, 75].map((y) => <line key={y} x1="0" x2={w} y1={h - (y / 100) * h} y2={h - (y / 100) * h} stroke="var(--line)" strokeDasharray="3 6" />)}
      {series.map((s) => (
        <polyline key={s.label} fill="none" stroke={s.color} strokeWidth="2"
          points={s.values.map((v, i) => `${(i / 59) * w},${h - (v / 100) * h}`).join(" ")} />
      ))}
    </svg>
  );
}

export function System() {
  const [hist, setHist] = useState<{ cpu: number[]; mem: number[] }>({ cpu: [], mem: [] });
  const stats = useData<any>(() => api.get("/api/p/system/stats"), [], 2000);
  const procs = useData<any[]>(() => api.get("/api/p/system/processes?limit=8"), [], 5000);
  const wins = useData<any>(() => api.tool("windows__list_windows"), [], 0);
  const [volume, setVolume] = useState(50);
  const [bright, setBright] = useState(70);
  const last = useRef<any>(null);

  useEffect(() => {
    const s = stats.data;
    if (!s || s === last.current) return;
    last.current = s;
    setHist((h) => ({ cpu: [...h.cpu, s.cpu_percent].slice(-60), mem: [...h.mem, s.memory_percent].slice(-60) }));
  }, [stats.data]);
  const s = stats.data;

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <Card title="Live usage" className="xl:col-span-2" actions={<span className="flex gap-3 text-xs"><span className="text-accent">● CPU</span><span className="text-warn">● RAM</span></span>}>
        <LineChart series={[{ values: hist.cpu, color: "var(--accent)", label: "cpu" }, { values: hist.mem, color: "#ffb300", label: "mem" }]} />
        {s && <div className="flex flex-wrap justify-around gap-4">
          <Ring value={s.cpu_percent} label="CPU" sub={`${s.cpu_count} cores`} />
          <Ring value={s.memory_percent} label="RAM" sub={`${s.memory_used_gb}/${s.memory_total_gb} GB`} />
          <Ring value={s.disk_percent} label="Disk" sub={`${s.disk_free_gb} GB free`} />
          {s.battery && <Ring value={s.battery.percent} label="Battery" sub={s.battery.plugged ? "plugged in" : "on battery"} />}
          <div className="flex flex-col justify-center text-sm"><span className="label">Network</span><span>↑ {s.net_sent_mb} MB</span><span>↓ {s.net_recv_mb} MB</span><span className="text-xs text-dim">Up {s.uptime_hours} h · {s.os}</span></div>
        </div>}
      </Card>
      <Card title="Media & display">
        <div className="flex justify-center gap-2">
          <Button aria-label="Previous" onClick={() => api.tool("media__playback", { action: "previous" })}><SkipBack size={16} /></Button>
          <Button variant="primary" aria-label="Play or pause" onClick={() => api.tool("media__playback", { action: "play_pause" })}><Pause size={16} /></Button>
          <Button aria-label="Next" onClick={() => api.tool("media__playback", { action: "next" })}><SkipForward size={16} /></Button>
        </div>
        <label className="flex items-center gap-3 text-sm"><Volume2 size={16} className="text-dim" />
          <input type="range" className="flex-1" value={volume} onChange={(e) => setVolume(+e.target.value)} onMouseUp={() => api.tool("media__set_volume", { level: volume })} aria-label="Volume" />
          <span className="w-8 font-mono text-xs">{volume}</span></label>
        <label className="flex items-center gap-3 text-sm"><Sun size={16} className="text-dim" />
          <input type="range" className="flex-1" value={bright} onChange={(e) => setBright(+e.target.value)} onMouseUp={() => api.tool("media__set_brightness", { level: bright })} aria-label="Brightness" />
          <span className="w-8 font-mono text-xs">{bright}</span></label>
        <div className="label mt-2">Power (asks for confirmation)</div>
        <div className="grid grid-cols-2 gap-2">
          <Button onClick={() => api.tool("power__lock")}><Lock size={14} /> Lock</Button>
          <Button onClick={() => api.tool("power__sleep")}><Moon size={14} /> Sleep</Button>
          <Button variant="danger" onClick={() => api.tool("power__restart")}><RotateCcw size={14} /> Restart</Button>
          <Button variant="danger" onClick={() => api.tool("power__shutdown")}><Power size={14} /> Shut down</Button>
        </div>
      </Card>
      <Card title="Top processes" className="xl:col-span-2">
        <table className="w-full text-sm">
          <thead className="label text-left"><tr><th className="py-1">Name</th><th>PID</th><th className="text-right">CPU %</th><th className="text-right">RAM %</th></tr></thead>
          <tbody>{procs.data?.map((p) => (
            <tr key={p.pid} className="border-t border-line"><td className="py-1 truncate max-w-48">{p.name}</td><td className="font-mono text-xs text-dim">{p.pid}</td>
              <td className="text-right font-mono">{(p.cpu_percent ?? 0).toFixed(1)}</td><td className="text-right font-mono">{p.memory_percent}</td></tr>
          ))}</tbody>
        </table>
      </Card>
      <Card title="Windows" icon={<AppWindow size={14} />}>
        {isError(wins.data) ? <p className="text-sm text-dim">{wins.data.error}</p> : (
          <div className="flex max-h-64 flex-col gap-1 overflow-y-auto">
            {(Array.isArray(wins.data) ? wins.data : []).map((w: string) => (
              <button key={w} className="truncate rounded px-2 py-1 text-left text-sm hover:bg-panel-2" onClick={() => api.tool("windows__focus", { title: w })} title={`Focus ${w}`}>{w}</button>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
