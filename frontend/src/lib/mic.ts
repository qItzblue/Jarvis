import { WS_BASE } from "./api";
import { downsample, encodeWav, Endpointer, rms } from "./audio";

/**
 * Microphone pipeline: captures 16 kHz PCM, streams it to the backend for wake-word
 * detection (when enabled) and records utterances with automatic end-pointing.
 */
export class Mic {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private node: ScriptProcessorNode | null = null;
  private wakeWs: WebSocket | null = null;
  private recording: { chunks: Int16Array[]; ep: Endpointer } | null = null;
  level = 0;
  onLevel: (l: number) => void = () => {};
  onWake: () => void = () => {};
  onUtterance: (wav: Blob) => void = () => {};
  onRecordingChange: (on: boolean) => void = () => {};
  onWakeUnavailable: (msg: string) => void = () => {};

  get active() { return !!this.stream; }
  get isRecording() { return !!this.recording; }

  async start() {
    if (this.stream) return;
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    this.ctx = new AudioContext();
    const src = this.ctx.createMediaStreamSource(this.stream);
    this.node = this.ctx.createScriptProcessor(4096, 1, 1);
    const frameMs = (4096 / this.ctx.sampleRate) * 1000;
    this.node.onaudioprocess = (e) => {
      const pcm = downsample(e.inputBuffer.getChannelData(0), this.ctx!.sampleRate);
      this.level = rms(pcm);
      this.onLevel(this.level);
      if (this.wakeWs?.readyState === WebSocket.OPEN && !this.recording) this.wakeWs.send(pcm.buffer as ArrayBuffer);
      if (this.recording) {
        this.recording.chunks.push(pcm);
        const r = this.recording.ep.push(pcm, frameMs);
        if (r !== "continue") this.finish(r === "end");
      }
    };
    src.connect(this.node);
    this.node.connect(this.ctx.destination);
  }

  stop() {
    this.setWakeWord(false);
    this.node?.disconnect();
    this.stream?.getTracks().forEach((t) => t.stop());
    void this.ctx?.close();
    this.stream = null; this.ctx = null; this.node = null; this.recording = null;
    this.onRecordingChange(false);
  }

  setWakeWord(on: boolean) {
    if (!on) { this.wakeWs?.close(); this.wakeWs = null; return; }
    if (this.wakeWs) return;
    const ws = new WebSocket(`${WS_BASE}/ws/audio`);
    ws.binaryType = "arraybuffer";
    ws.onmessage = (m) => {
      const msg = JSON.parse(m.data);
      if (msg.type === "wake") this.onWake();
      if (msg.type === "wake_unavailable") this.onWakeUnavailable(msg.message);
    };
    ws.onclose = () => { if (this.wakeWs === ws) this.wakeWs = null; };
    this.wakeWs = ws;
  }

  async record(ep: Endpointer = new Endpointer()) {
    await this.start();
    this.recording = { chunks: [], ep };
    this.onRecordingChange(true);
  }

  /** Stop recording now (push-to-talk released or cancelled). */
  finish(send = true) {
    const rec = this.recording;
    this.recording = null;
    this.onRecordingChange(false);
    if (send && rec && rec.chunks.length) this.onUtterance(encodeWav(rec.chunks));
  }
}
