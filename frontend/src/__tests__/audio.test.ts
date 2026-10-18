import { describe, expect, it } from "vitest";
import { downsample, encodeWav, Endpointer, NO, rms, YES } from "../lib/audio";

describe("audio helpers", () => {
  it("downsamples 48 kHz to 16 kHz", () => {
    const out = downsample(new Float32Array(4800).fill(0.5), 48000);
    expect(out.length).toBe(1600);
    expect(out[0]).toBe(Math.floor(0.5 * 0x7fff));
  });

  it("encodes a valid WAV header", async () => {
    const blob = encodeWav([new Int16Array([1, 2, 3])]);
    const buf = new DataView(await blob.arrayBuffer());
    expect(blob.size).toBe(44 + 6);
    expect(String.fromCharCode(buf.getUint8(0), buf.getUint8(1), buf.getUint8(2), buf.getUint8(3))).toBe("RIFF");
    expect(buf.getUint32(24, true)).toBe(16000);
    expect(buf.getInt16(46, true)).toBe(2);
  });

  it("computes loudness", () => {
    expect(rms(new Int16Array(10))).toBe(0);
    expect(rms(new Int16Array(10).fill(16384))).toBeCloseTo(0.5, 2);
  });

  it("end-points after speech followed by silence", () => {
    const ep = new Endpointer(0.02, 300, 10000, 2000);
    const loud = new Int16Array(100).fill(8000), quiet = new Int16Array(100);
    expect(ep.push(loud, 100)).toBe("continue");
    expect(ep.push(quiet, 100)).toBe("continue");
    expect(ep.push(quiet, 100)).toBe("continue");
    expect(ep.push(quiet, 100)).toBe("end");
  });

  it("times out when nobody speaks", () => {
    const ep = new Endpointer(0.02, 300, 10000, 250);
    expect(ep.push(new Int16Array(100), 100)).toBe("continue");
    expect(ep.push(new Int16Array(100), 200)).toBe("timeout");
  });

  it("recognises spoken yes/no for confirmations", () => {
    expect(YES.test("Yes please")).toBe(true);
    expect(YES.test("go ahead")).toBe(true);
    expect(NO.test("no thanks")).toBe(true);
    expect(YES.test("not now")).toBe(false);
  });
});
