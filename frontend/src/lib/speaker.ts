import { API_BASE } from "./api";

/** Speaks sentences in order; can be interrupted instantly (barge-in). */
export class Speaker {
  private queue: string[] = [];
  private busy = false;
  private audio: HTMLAudioElement | null = null;
  private generation = 0;
  engine = "browser";
  rate = 1;
  muted = false;
  onState: (speaking: boolean) => void = () => {};

  enqueue(text: string) {
    if (this.muted || !text.trim()) return;
    this.queue.push(text);
    if (!this.busy) void this.loop();
  }

  stop() {
    this.generation++;
    this.queue = [];
    if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
    if (this.audio) { this.audio.pause(); this.audio = null; }
    if (this.busy) { this.busy = false; this.onState(false); }
  }

  get speaking() { return this.busy; }

  private async loop() {
    const gen = this.generation;
    this.busy = true;
    this.onState(true);
    while (this.queue.length && gen === this.generation) {
      const text = this.queue.shift()!;
      try {
        if (this.engine !== "browser") await this.playServer(text, gen);
        else await this.playBrowser(text);
      } catch {
        await this.playBrowser(text).catch(() => {});
      }
    }
    if (gen === this.generation) { this.busy = false; this.onState(false); }
  }

  private async playServer(text: string, gen: number) {
    const r = await fetch(`${API_BASE}/api/tts`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }),
    });
    if (!r.ok) throw new Error("tts unavailable");
    const url = URL.createObjectURL(await r.blob());
    if (gen !== this.generation) return;
    await new Promise<void>((resolve) => {
      const a = new Audio(url);
      a.playbackRate = this.rate;
      this.audio = a;
      a.onended = a.onerror = () => { URL.revokeObjectURL(url); resolve(); };
      a.play().catch(() => resolve());
    });
  }

  private playBrowser(text: string) {
    return new Promise<void>((resolve) => {
      if (typeof speechSynthesis === "undefined") return resolve();
      const u = new SpeechSynthesisUtterance(text);
      const voices = speechSynthesis.getVoices();
      u.voice = voices.find((v) => /en-GB/i.test(v.lang) && /male|daniel|george|ryan/i.test(v.name))
        ?? voices.find((v) => /en-GB/i.test(v.lang)) ?? null;
      u.rate = this.rate;
      u.onend = u.onerror = () => resolve();
      speechSynthesis.speak(u);
    });
  }
}
