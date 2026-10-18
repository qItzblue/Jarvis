import { ButtonHTMLAttributes, ReactNode, useCallback, useEffect, useState } from "react";

export function Card({ title, icon, actions, children, className = "" }:
  { title?: ReactNode; icon?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`panel p-4 flex flex-col gap-3 min-w-0 ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-2">
          <h2 className="label flex items-center gap-2">{icon}{title}</h2>
          <div className="flex items-center gap-2">{actions}</div>
        </header>
      )}
      {children}
    </section>
  );
}

type Variant = "primary" | "ghost" | "danger" | "subtle";
export function Button({ variant = "subtle", className = "", ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const styles: Record<Variant, string> = {
    primary: "bg-accent text-bg font-semibold hover:brightness-110",
    ghost: "text-dim hover:text-ink hover:bg-panel-2",
    danger: "bg-danger/15 text-danger border border-danger/40 hover:bg-danger/25",
    subtle: "bg-panel-2 border border-line hover:border-accent text-ink",
  };
  return <button {...p} className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-sm transition disabled:opacity-40 disabled:pointer-events-none ${styles[variant]} ${className}`} />;
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <button role="switch" aria-checked={checked} aria-label={label} title={label} onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 shrink-0 rounded-full border transition ${checked ? "bg-accent/30 border-accent" : "bg-panel-2 border-line"}`}>
      <span className={`absolute top-0.5 h-4.5 w-4.5 rounded-full transition-all ${checked ? "left-5.5 bg-accent glow" : "left-0.5 bg-dim"}`} />
    </button>
  );
}

const BADGE: Record<string, string> = {
  ok: "text-ok border-ok/40 bg-ok/10", not_configured: "text-warn border-warn/40 bg-warn/10",
  missing_dependency: "text-warn border-warn/40 bg-warn/10", disabled: "text-dim border-line bg-panel-2",
  error: "text-danger border-danger/40 bg-danger/10",
};
const BADGE_TEXT: Record<string, string> = {
  ok: "Active", not_configured: "Not configured", missing_dependency: "Needs install", disabled: "Disabled",
};
export function Badge({ status, children }: { status: string; children?: ReactNode }) {
  return <span className={`label !text-[10px] rounded border px-1.5 py-0.5 ${BADGE[status] ?? BADGE.disabled}`}>{children ?? BADGE_TEXT[status] ?? status}</span>;
}

export function Empty({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-8 text-center text-dim">
      <div className="text-accent/60">{icon}</div>
      <p className="font-medium text-ink">{title}</p>
      {children && <div className="text-sm max-w-sm">{children}</div>}
    </div>
  );
}

export function Spinner() {
  return <span className="inline-block h-4 w-4 rounded-full border-2 border-accent border-t-transparent anim-spin-fast" aria-label="Loading" />;
}

export function Ring({ value, label, sub, size = 92 }: { value: number; label: string; sub?: string; size?: number }) {
  const r = size / 2 - 7, c = 2 * Math.PI * r, v = Math.max(0, Math.min(100, value || 0));
  const color = v > 85 ? "var(--color-danger)" : v > 65 ? "var(--color-warn)" : "var(--accent)";
  return (
    <div className="flex flex-col items-center gap-1" title={`${label} ${Math.round(v)}%`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--line)" strokeWidth="6" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="6" fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - v / 100)} style={{ transition: "stroke-dashoffset .6s" }} />
        <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" fill="var(--ink)"
          className="rotate-90 origin-center font-mono text-sm">{Math.round(v)}%</text>
      </svg>
      <span className="label">{label}</span>
      {sub && <span className="text-xs text-dim">{sub}</span>}
    </div>
  );
}

export function Sparkline({ values, width = 90, height = 28 }: { values: number[]; width?: number; height?: number }) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * width},${height - ((v - min) / span) * height}`).join(" ");
  const up = values[values.length - 1] >= values[0];
  return <svg width={width} height={height}><polyline points={pts} fill="none" strokeWidth="1.5" stroke={up ? "var(--color-ok)" : "var(--color-danger)"} /></svg>;
}

/** Fetches data and optionally re-polls. */
export function useData<T>(load: () => Promise<T>, deps: unknown[] = [], intervalMs = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const reload = useCallback(async () => {
    try { setData(await load()); setError(null); } catch (e: any) { setError(e.message ?? String(e)); }
    finally { setLoading(false); }
  }, deps);
  useEffect(() => {
    void reload();
    if (!intervalMs) return;
    const t = setInterval(reload, intervalMs);
    return () => clearInterval(t);
  }, [reload, intervalMs]);
  return { data, error, loading, reload, setData };
}

export function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return <p className="text-sm text-danger" role="alert">{error}</p>;
}
