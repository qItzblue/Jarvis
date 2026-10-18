import { describe, expect, it, vi } from "vitest";
import { Speaker } from "../lib/speaker";

describe("Speaker barge-in", () => {
  it("stop() clears the queue and reports not speaking", async () => {
    const spoken: string[] = [];
    (globalThis as any).SpeechSynthesisUtterance = class { onend: any; constructor(public text: string) {} };
    (globalThis as any).speechSynthesis = {
      getVoices: () => [], cancel: vi.fn(),
      speak: (u: any) => { spoken.push(u.text); setTimeout(() => u.onend?.(), 5); },
    };
    const s = new Speaker();
    const states: boolean[] = [];
    s.onState = (v) => states.push(v);
    s.enqueue("one"); s.enqueue("two"); s.enqueue("three");
    await new Promise((r) => setTimeout(r, 1));
    s.stop();
    await new Promise((r) => setTimeout(r, 30));
    expect(spoken).toEqual(["one"]);
    expect(states).toEqual([true, false]);
    expect(s.speaking).toBe(false);
  });

  it("muted speaker ignores sentences", () => {
    const s = new Speaker();
    s.muted = true;
    s.enqueue("hello");
    expect(s.speaking).toBe(false);
  });
});
