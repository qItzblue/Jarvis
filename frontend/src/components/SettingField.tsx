import { Toggle } from "./ui";

export interface FieldDef { key: string; label: string; type: string; options?: string[]; secret?: boolean; value: any; is_set?: boolean }

export function SettingField({ f, value, onChange }: { f: FieldDef; value: any; onChange: (v: any) => void }) {
  const id = `f-${f.key}`;
  let input;
  if (f.type === "boolean") input = <Toggle checked={!!value} onChange={onChange} label={f.label} />;
  else if (f.type === "select") input = <select id={id} className="input" value={value ?? ""} onChange={(e) => onChange(e.target.value)}>{f.options?.map((o) => <option key={o}>{o}</option>)}</select>;
  else if (f.type === "text") input = <textarea id={id} className="input min-h-24 font-mono text-xs" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
  else if (f.type === "number") input = <input id={id} className="input" type="number" step="any" value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : +e.target.value)} />;
  else input = <input id={id} className="input" type={f.secret ? "password" : "text"} value={value ?? ""} placeholder={f.secret && f.is_set ? "•••••••• (saved)" : ""}
    onFocus={(e) => f.secret && String(value ?? "").startsWith("••") && onChange("") && e.target.select()} onChange={(e) => onChange(e.target.value)} />;
  return (
    <label htmlFor={id} className={f.type === "boolean" ? "flex items-center justify-between gap-3" : "flex flex-col gap-1"}>
      <span className="text-sm text-dim">{f.label}{f.secret && f.is_set && <span className="ml-2 text-ok">✓ set</span>}</span>
      {input}
    </label>
  );
}
