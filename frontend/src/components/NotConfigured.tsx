import { Settings2 } from "lucide-react";
import { useJarvis } from "../lib/store";
import { Badge, Empty } from "./ui";

/** Renders children only when the plugin is active; otherwise explains what's missing. */
export function RequirePlugin({ name, label, children }: { name: string; label: string; children: React.ReactNode }) {
  const { status } = useJarvis();
  const st = status?.plugins?.[name];
  if (!status) return <Empty title="Backend offline">Start the Jarvis backend to see {label}.</Empty>;
  if (st === "ok") return <>{children}</>;
  const help: Record<string, string> = {
    not_configured: "Add the required settings in the Plugins tab.",
    missing_dependency: "An optional package needs installing — see the Plugins tab.",
    disabled: "Turn it on in the Plugins tab.",
  };
  return (
    <Empty icon={<Settings2 size={28} />} title={`${label}`}>
      <div className="flex flex-col items-center gap-2"><Badge status={st ?? "disabled"} /><span>{help[st ?? "disabled"]}</span></div>
    </Empty>
  );
}
