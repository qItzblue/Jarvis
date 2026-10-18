import type { OrbState } from "../lib/store";

/** The arc-reactor orb. Its animation reflects what Jarvis is doing. */
export function Orb({ state, level = 0, size = 260, onClick }: { state: OrbState; level?: number; size?: number; onClick?: () => void }) {
  const scale = state === "listening" ? 1 + Math.min(level * 6, 0.35) : 1;
  const label = { idle: "Idle – click to talk", listening: "Listening", thinking: "Thinking", speaking: "Speaking – click to interrupt" }[state];
  return (
    <button onClick={onClick} aria-label={label} title={label}
      className="relative grid place-items-center rounded-full focus-visible:outline-2 focus-visible:outline-accent"
      style={{ width: size, height: size }}>
      <svg viewBox="0 0 200 200" className="absolute inset-0 h-full w-full">
        <defs>
          <radialGradient id="core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
            <stop offset="35%" stopColor="var(--accent)" stopOpacity="0.85" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </radialGradient>
        </defs>
        <g className={state === "thinking" ? "anim-spin-fast" : "anim-spin"} style={{ transformOrigin: "100px 100px" }}>
          <circle cx="100" cy="100" r="92" fill="none" stroke="var(--accent)" strokeOpacity=".35" strokeWidth="1" strokeDasharray="4 10" />
          <path d="M100 8 A92 92 0 0 1 192 100" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
        </g>
        <g className="anim-spin-rev" style={{ transformOrigin: "100px 100px" }}>
          <circle cx="100" cy="100" r="76" fill="none" stroke="var(--accent)" strokeOpacity=".5" strokeWidth="6" strokeDasharray="30 18" />
        </g>
        <circle cx="100" cy="100" r="62" fill="none" stroke="var(--accent)" strokeOpacity=".25" strokeWidth="1" />
        {Array.from({ length: 12 }).map((_, i) => (
          <rect key={i} x="98" y="44" width="4" height="12" rx="1" fill="var(--accent)" fillOpacity=".6"
            transform={`rotate(${i * 30} 100 100)`} />
        ))}
      </svg>
      <div className={state === "speaking" ? "anim-pulse-fast" : "anim-pulse"}
        style={{ width: size * 0.36, height: size * 0.36, transform: `scale(${scale})`, transition: "transform 80ms",
          borderRadius: "9999px", background: "radial-gradient(circle, #fff 0%, var(--accent) 40%, transparent 72%)",
          boxShadow: "0 0 60px var(--accent)" }} />
      <span className="sr-only">{label}</span>
    </button>
  );
}
