// Pure chat-state reducer for server events (unit-tested).

export interface ToolEvent { name: string; status: "running" | "done"; ok?: boolean; args?: unknown; result?: unknown }
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  tools: ToolEvent[];
  error?: string;
  pending?: boolean;
  images?: string[];
}

let counter = 0;
export const newId = () => `${Date.now().toString(36)}-${(counter++).toString(36)}`;

export function userMessage(text: string, images?: string[]): ChatMessage {
  return { id: newId(), role: "user", text, tools: [], images };
}

function withAssistant(msgs: ChatMessage[], fn: (m: ChatMessage) => ChatMessage): ChatMessage[] {
  const last = msgs[msgs.length - 1];
  if (last && last.role === "assistant" && last.pending) return [...msgs.slice(0, -1), fn(last)];
  return [...msgs, fn({ id: newId(), role: "assistant", text: "", tools: [], pending: true })];
}

export function applyEvent(msgs: ChatMessage[], ev: any): ChatMessage[] {
  switch (ev.type) {
    case "start":
      return withAssistant(msgs, (m) => m);
    case "token":
      return withAssistant(msgs, (m) => ({ ...m, text: m.text + ev.text }));
    case "tool":
      return withAssistant(msgs, (m) => {
        const tools = [...m.tools];
        const idx = tools.findIndex((t) => t.name === ev.name && t.status === "running");
        const entry: ToolEvent = { name: ev.name, status: ev.status, ok: ev.ok, args: ev.args, result: ev.result };
        if (ev.status === "done" && idx >= 0) tools[idx] = { ...tools[idx], ...entry, args: tools[idx].args };
        else tools.push(entry);
        return { ...m, tools };
      });
    case "error":
      return withAssistant(msgs, (m) => ({ ...m, error: ev.message, pending: false }));
    case "done":
    case "cancelled":
      return withAssistant(msgs, (m) => ({ ...m, pending: false, text: m.text || (ev.type === "cancelled" ? "…" : m.text) }));
    default:
      return msgs;
  }
}

export function toolLabel(name: string): string {
  const [plugin, fn] = name.split("__");
  const nice = (fn || plugin).replace(/_/g, " ");
  return `${plugin} · ${nice}`;
}
