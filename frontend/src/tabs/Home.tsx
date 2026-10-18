import { CalendarDays, CloudSun, Cpu, Newspaper, Sunrise, Timer, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { Orb } from "../components/Orb";
import { Button, Card, Empty, Ring, Spinner, useData } from "../components/ui";
import { api, isError } from "../lib/api";
import { useJarvis } from "../lib/store";

const QUICK = ["Good morning", "What's on my calendar today?", "Start a 25 minute focus session", "What's the weather tomorrow?",
  "Summarise today's news", "Good night"];

export function fmtCountdown(sec: number) {
  const s = Math.max(0, Math.round(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function Home() {
  const { orb, level, listen, stopSpeaking, send, timers, focus, status, messages } = useJarvis();
  const stats = useData(() => api.get("/api/p/system/stats"), [], 4000);
  const briefing = useData(() => api.get("/api/p/briefing"), [status?.provider]);
  const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick((x) => x + 1), 1000); return () => clearInterval(t); }, []);
  const b = briefing.data;
  const s = stats.data;
  const lastReply = [...messages].reverse().find((m) => m.role === "assistant")?.text;

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_1.2fr_1fr]">
      <div className="flex flex-col gap-4">
        <Card title="Weather" icon={<CloudSun size={14} />}>
          {briefing.loading ? <Spinner /> : b?.weather ? (
            <div>
              <p className="text-4xl font-light">{Math.round(b.weather.now.temp)}{b.weather.units}</p>
              <p className="text-dim capitalize">{b.weather.now.conditions} · {b.weather.location}</p>
              <div className="mt-3 flex gap-4 text-sm">
                {b.weather.days.map((d: any) => (
                  <div key={d.date}><p className="label">{new Date(d.date).toLocaleDateString([], { weekday: "short" })}</p>
                    <p>{Math.round(d.high)}° / {Math.round(d.low)}°</p><p className="text-xs text-dim">{d.rain_chance}% rain</p></div>
                ))}
              </div>
            </div>
          ) : <p className="text-sm text-dim">Weather unavailable.</p>}
        </Card>
        <Card title="Next up" icon={<CalendarDays size={14} />}>
          {b?.calendar?.length ? b.calendar.slice(0, 3).map((e: any) => (
            <div key={e.id} className="flex gap-3 border-l-2 border-accent pl-3">
              <span className="font-mono text-sm text-accent">{e.start.includes("T") ? new Date(e.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "All day"}</span>
              <span className="truncate">{e.summary}</span>
            </div>
          )) : <p className="text-sm text-dim">{status?.plugins.calendar === "ok" ? "Nothing scheduled today." : "Connect Google Calendar in Plugins."}</p>}
        </Card>
        <Card title="Timers & focus" icon={<Timer size={14} />}>
          {!timers.length && !focus && <p className="text-sm text-dim">No timers running.</p>}
          {focus && <div className="flex justify-between"><span>🎯 Focus · {focus.phase} {focus.round}/{focus.rounds}</span><span className="font-mono text-accent">{fmtCountdown(focus.ends_at - Date.now() / 1000)}</span></div>}
          {timers.map((t) => (
            <div key={t.id} className="flex justify-between"><span>{t.label}</span>
              <span className="font-mono text-accent">{fmtCountdown(t.ends_at - Date.now() / 1000)}</span></div>
          ))}
        </Card>
      </div>

      <div className="flex flex-col items-center gap-4">
        <Orb state={orb} level={level} size={300} onClick={() => (orb === "speaking" ? stopSpeaking() : void listen())} />
        <p className="label">{{ idle: "Standing by", listening: "Listening", thinking: "Processing", speaking: "Speaking" }[orb]}</p>
        {lastReply && <p className="panel max-w-xl p-3 text-center text-sm line-clamp-4">{lastReply}</p>}
        {status && !status.llm_configured && (
          <p className="text-sm text-warn">No API key for {status.provider}. Add one in Settings.</p>
        )}
        <div className="flex flex-wrap justify-center gap-2">
          {QUICK.map((q) => <Button key={q} onClick={() => send(q)}><Zap size={14} className="text-accent" />{q}</Button>)}
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <Card title="System" icon={<Cpu size={14} />}>
          {s ? (
            <div className="flex justify-around">
              <Ring value={s.cpu_percent} label="CPU" />
              <Ring value={s.memory_percent} label="RAM" sub={`${s.memory_used_gb}/${s.memory_total_gb} GB`} />
              {s.battery ? <Ring value={s.battery.percent} label="Battery" sub={s.battery.plugged ? "charging" : ""} /> : <Ring value={s.disk_percent} label="Disk" />}
            </div>
          ) : <Spinner />}
        </Card>
        <Card title="Morning briefing" icon={<Sunrise size={14} />} actions={<Button variant="ghost" onClick={() => send("Give me my morning briefing")}>Read aloud</Button>}>
          {briefing.loading ? <Spinner /> : b && !isError(b) ? (
            <ul className="space-y-1 text-sm">
              <li>✅ {b.tasks?.length ?? 0} open tasks</li>
              <li>🔔 {b.reminders?.length ?? 0} reminders</li>
              {b.commute && <li>🚗 Commute: {b.commute.duration}</li>}
            </ul>
          ) : <Empty title="Briefing unavailable" />}
        </Card>
        <Card title="Headlines" icon={<Newspaper size={14} />}>
          {b?.news?.length ? b.news.slice(0, 5).map((n: any) => (
            <a key={n.link} href={n.link} target="_blank" rel="noreferrer" className="block truncate text-sm hover:text-accent">{n.title}</a>
          )) : <p className="text-sm text-dim">No headlines.</p>}
        </Card>
      </div>
    </div>
  );
}
