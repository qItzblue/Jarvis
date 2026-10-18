// Pure audio helpers (unit-tested): resampling, WAV encoding and loudness.

export function downsample(input: Float32Array, inRate: number, outRate = 16000): Int16Array {
  const ratio = inRate / outRate;
  const len = Math.floor(input.length / ratio);
  const out = new Int16Array(len);
  for (let i = 0; i < len; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j++) sum += input[j];
    const v = Math.max(-1, Math.min(1, sum / Math.max(1, end - start)));
    out[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
  }
  return out;
}

export function rms(samples: Int16Array): number {
  if (!samples.length) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += (samples[i] / 32768) ** 2;
  return Math.sqrt(sum / samples.length);
}

export function encodeWav(chunks: Int16Array[], rate = 16000): Blob {
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const buf = new ArrayBuffer(44 + total * 2);
  const v = new DataView(buf);
  const str = (o: number, s: string) => [...s].forEach((ch, i) => v.setUint8(o + i, ch.charCodeAt(0)));
  str(0, "RIFF"); v.setUint32(4, 36 + total * 2, true); str(8, "WAVE");
  str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, "data"); v.setUint32(40, total * 2, true);
  let off = 44;
  for (const c of chunks) for (let i = 0; i < c.length; i++, off += 2) v.setInt16(off, c[i], true);
  return new Blob([buf], { type: "audio/wav" });
}

/** Voice-activity end-pointing: decides when an utterance has finished. */
export class Endpointer {
  speechSeen = false;
  silenceMs = 0;
  elapsedMs = 0;
  constructor(private threshold = 0.02, private endSilenceMs = 1100, private maxMs = 15000, private noSpeechMs = 6000) {}
  /** Returns "continue", "end" (got speech then silence) or "timeout" (no speech at all). */
  push(frame: Int16Array, frameMs: number): "continue" | "end" | "timeout" {
    this.elapsedMs += frameMs;
    if (rms(frame) > this.threshold) { this.speechSeen = true; this.silenceMs = 0; }
    else this.silenceMs += frameMs;
    if (this.speechSeen && (this.silenceMs >= this.endSilenceMs || this.elapsedMs >= this.maxMs)) return "end";
    if (!this.speechSeen && this.elapsedMs >= this.noSpeechMs) return "timeout";
    return "continue";
  }
}

export const YES = /^(yes|yeah|yep|sure|do it|go ahead|confirm|approved?|ok(ay)?)\b/i;
export const NO = /^(no|nope|cancel|stop|don't|do not|deny)\b/i;
