import { describe, expect, it } from "vitest";
import { applyEvent, ChatMessage, toolLabel, userMessage } from "../lib/chat";

const run = (events: any[], start: ChatMessage[] = []) => events.reduce(applyEvent, start);

describe("chat reducer", () => {
  it("streams tokens into one assistant message", () => {
    const msgs = run([{ type: "start" }, { type: "token", text: "Hel" }, { type: "token", text: "lo" }, { type: "done" }], [userMessage("hi")]);
    expect(msgs).toHaveLength(2);
    expect(msgs[1]).toMatchObject({ role: "assistant", text: "Hello", pending: false });
  });

  it("tracks a tool from running to done", () => {
    const msgs = run([{ type: "start" }, { type: "tool", name: "weather__forecast", status: "running", args: { days: 1 } },
      { type: "tool", name: "weather__forecast", status: "done", ok: true, result: { t: 1 } }]);
    expect(msgs[0].tools).toEqual([{ name: "weather__forecast", status: "done", ok: true, args: { days: 1 }, result: { t: 1 } }]);
  });

  it("records errors and starts a new message after completion", () => {
    let msgs = run([{ type: "start" }, { type: "error", message: "No key" }]);
    expect(msgs[0].error).toBe("No key");
    msgs = run([{ type: "start" }, { type: "token", text: "again" }], msgs);
    expect(msgs).toHaveLength(2);
  });

  it("formats tool labels", () => {
    expect(toolLabel("timers__start_timer")).toBe("timers · start timer");
  });
});
