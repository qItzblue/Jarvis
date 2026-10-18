import { Lightbulb, Minus, Plug, Plus, Sparkles, Thermometer } from "lucide-react";
import { RequirePlugin } from "../components/NotConfigured";
import { Button, Card, Empty, ErrorNote, Spinner, Toggle, useData } from "../components/ui";
import { api, isError } from "../lib/api";

function Devices() {
  const dev = useData<any>(() => api.get("/api/p/homeassistant/devices"), [], 10000);
  if (dev.loading) return <Spinner />;
  if (isError(dev.data)) return <ErrorNote error={dev.data.error} />;
  const list: any[] = dev.data ?? [];
  const scenes = list.filter((d) => d.domain === "scene");
  const climate = list.filter((d) => d.domain === "climate");
  const switches = list.filter((d) => ["light", "switch", "fan"].includes(d.domain));
  const call = async (tool: string, args: object) => { await api.tool(tool, args as any); setTimeout(dev.reload, 600); };
  if (!list.length) return <Empty title="No devices found" />;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Scenes" icon={<Sparkles size={14} />} className="lg:col-span-2">
        <div className="flex flex-wrap gap-2">
          {scenes.length ? scenes.map((s) => <Button key={s.entity_id} onClick={() => call("homeassistant__scene", { scene: s.entity_id })}>{s.name}</Button>)
            : <p className="text-sm text-dim">No scenes in Home Assistant.</p>}
        </div>
      </Card>
      <Card title="Lights & plugs" icon={<Lightbulb size={14} />}>
        {switches.map((d) => (
          <div key={d.entity_id} className="flex items-center gap-3">
            {d.domain === "light" ? <Lightbulb size={18} className={d.state === "on" ? "text-warn" : "text-dim"} /> : <Plug size={18} className={d.state === "on" ? "text-ok" : "text-dim"} />}
            <span className="flex-1">{d.name}</span>
            {d.domain === "light" && d.state === "on" && (
              <input type="range" min={1} max={100} defaultValue={d.brightness ? Math.round(d.brightness / 2.55) : 100} aria-label={`${d.name} brightness`}
                onMouseUp={(e) => call("homeassistant__switch", { target: d.entity_id, on: true, brightness: +(e.target as HTMLInputElement).value })} />
            )}
            <Toggle checked={d.state === "on"} label={d.name} onChange={(on) => call("homeassistant__switch", { target: d.entity_id, on })} />
          </div>
        ))}
      </Card>
      <Card title="Climate" icon={<Thermometer size={14} />}>
        {!climate.length && <p className="text-sm text-dim">No thermostats.</p>}
        {climate.map((c) => (
          <div key={c.entity_id} className="flex items-center gap-4">
            <div className="grid h-24 w-24 place-items-center rounded-full border-4 border-accent/60 glow">
              <span className="font-mono text-2xl">{c.temperature ?? "–"}°</span>
            </div>
            <div className="flex-1"><p>{c.name}</p><p className="text-xs text-dim">Now {c.current_temperature ?? "?"}° · {c.state}</p></div>
            <Button aria-label="Lower" onClick={() => call("homeassistant__thermostat", { target: c.entity_id, temperature: (c.temperature ?? 20) - 0.5 })}><Minus size={14} /></Button>
            <Button aria-label="Raise" onClick={() => call("homeassistant__thermostat", { target: c.entity_id, temperature: (c.temperature ?? 20) + 0.5 })}><Plus size={14} /></Button>
          </div>
        ))}
      </Card>
    </div>
  );
}

export function SmartHome() {
  return <RequirePlugin name="homeassistant" label="Home Assistant is not connected"><Devices /></RequirePlugin>;
}
