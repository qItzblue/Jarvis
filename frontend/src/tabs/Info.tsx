import { Car, Newspaper, Package, Plane, TrendingDown, TrendingUp, Trophy } from "lucide-react";
import { useState } from "react";
import { RequirePlugin } from "../components/NotConfigured";
import { Button, Card, ErrorNote, Sparkline, Spinner, useData } from "../components/ui";
import { api, isError } from "../lib/api";

function Lookup({ tool, placeholder, render, args }: { tool: string; placeholder: string; args: (v: string) => object; render: (r: any) => React.ReactNode }) {
  const [v, setV] = useState("");
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const go = async () => { if (!v) return; setBusy(true); setRes(await api.tool(tool, args(v) as any).catch((e) => ({ error: e.message }))); setBusy(false); };
  return (
    <>
      <div className="flex gap-2"><input className="input" value={v} placeholder={placeholder} aria-label={placeholder} onChange={(e) => setV(e.target.value)} onKeyDown={(e) => e.key === "Enter" && go()} />
        <Button variant="primary" onClick={go}>{busy ? <Spinner /> : "Go"}</Button></div>
      {res && (isError(res) ? <ErrorNote error={res.error} /> : render(res))}
    </>
  );
}

function Watchlist() {
  const w = useData<any[]>(() => api.get("/api/p/finance/watchlist"), [], 60000);
  if (w.loading) return <Spinner />;
  return (
    <table className="w-full text-sm"><tbody>
      {w.data?.map((q) => (
        <tr key={q.symbol ?? q.id} className="border-t border-line first:border-0">
          <td className="py-1.5 font-mono">{q.symbol ?? q.id}</td>
          <td className="text-right font-mono">{q.error ? "–" : q.price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
          <td className={`text-right font-mono ${q.change_percent >= 0 ? "text-ok" : "text-danger"}`}>
            {q.change_percent != null && <>{q.change_percent >= 0 ? <TrendingUp size={12} className="inline" /> : <TrendingDown size={12} className="inline" />} {q.change_percent}%</>}
          </td>
          <td className="pl-2"><Sparkline values={q.history ?? []} /></td>
        </tr>
      ))}
    </tbody></table>
  );
}

const LEAGUES = ["premier league", "nba", "nfl", "mlb", "nhl", "champions league", "la liga", "f1"];
function Scores() {
  const [league, setLeague] = useState(LEAGUES[0]);
  const s = useData<any>(() => api.tool("sports__scores", { league }), [league], 60000);
  return (
    <>
      <select className="input" value={league} onChange={(e) => setLeague(e.target.value)} aria-label="League">{LEAGUES.map((l) => <option key={l}>{l}</option>)}</select>
      {s.loading ? <Spinner /> : isError(s.data) ? <ErrorNote error={s.data.error} /> : !s.data?.length ? <p className="text-sm text-dim">No games today.</p> :
        s.data.slice(0, 8).map((g: any) => (
          <div key={g.name} className="flex items-center justify-between text-sm">
            <span className="truncate">{g.teams.map((t: any) => `${t.team} ${t.score ?? ""}`).join("  –  ")}</span>
            <span className="label shrink-0">{g.detail}</span>
          </div>
        ))}
    </>
  );
}

export function Info() {
  const news = useData<any[]>(() => api.get("/api/p/news?limit=12"), [], 300000);
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <Card title="News" icon={<Newspaper size={14} />} className="xl:row-span-2">
        <RequirePlugin name="news" label="News">
          {news.loading ? <Spinner /> : news.data?.map((n) => (
            <a key={n.link} href={n.link} target="_blank" rel="noreferrer" className="block border-b border-line pb-2 hover:text-accent">
              <p className="text-sm font-medium">{n.title}</p><p className="label !text-[10px]">{n.source}</p>
            </a>
          ))}
        </RequirePlugin>
      </Card>
      <Card title="Markets" icon={<TrendingUp size={14} />}><RequirePlugin name="finance" label="Markets"><Watchlist /></RequirePlugin></Card>
      <Card title="Sports" icon={<Trophy size={14} />}><RequirePlugin name="sports" label="Sports"><Scores /></RequirePlugin></Card>
      <Card title="Packages" icon={<Package size={14} />}>
        <RequirePlugin name="packages" label="Package tracking needs a 17TRACK key">
          <Lookup tool="packages__track" placeholder="Tracking number" args={(v) => ({ number: v })}
            render={(r) => <p className="text-sm"><b>{r.status}</b> · {r.last_event} {r.location && `(${r.location})`}</p>} />
        </RequirePlugin>
      </Card>
      <Card title="Flights" icon={<Plane size={14} />}>
        <RequirePlugin name="flights" label="Flight status needs an AviationStack key">
          <Lookup tool="flights__flight_status" placeholder="Flight number, e.g. BA117" args={(v) => ({ flight: v })}
            render={(r) => <div className="text-sm"><p><b>{r.airline} {r.flight}</b> · <span className="capitalize text-accent">{r.status}</span></p>
              <p>{r.departure.airport} → {r.arrival.airport}</p><p className="text-xs text-dim">ETA {r.arrival.estimated ?? r.arrival.scheduled}</p></div>} />
        </RequirePlugin>
      </Card>
      <Card title="Commute" icon={<Car size={14} />}>
        <RequirePlugin name="commute" label="Commute needs a Google Maps key">
          <Lookup tool="commute__travel_time" placeholder="Destination (from home)" args={(v) => ({ origin: "home", destination: v })}
            render={(r) => <p className="text-sm"><b className="text-accent">{r.duration}</b> · {r.distance} to {r.to}</p>} />
        </RequirePlugin>
      </Card>
    </div>
  );
}
