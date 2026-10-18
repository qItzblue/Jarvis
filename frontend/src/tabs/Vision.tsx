import { Camera, CameraOff, Hand, MonitorSmartphone, ScanFace, UserPlus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { RequirePlugin } from "../components/NotConfigured";
import { Button, Card, ErrorNote, Spinner, useData } from "../components/ui";
import { api } from "../lib/api";
import { useJarvis } from "../lib/store";

const GESTURES: Record<string, string> = {
  Open_Palm: "Stop speaking", Thumb_Up: "Approve confirmation", Thumb_Down: "Deny confirmation", Victory: "Start listening",
};

function useGestures(video: HTMLVideoElement | null, on: boolean, handle: (g: string) => void) {
  const [ready, setReady] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!on || !video) return;
    let stop = false, raf = 0, last = "", lastAt = 0;
    (async () => {
      try {
        const { FilesetResolver, GestureRecognizer } = await import("@mediapipe/tasks-vision");
        const files = await FilesetResolver.forVisionTasks("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.1.1/wasm");
        const rec = await GestureRecognizer.createFromOptions(files, {
          baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task" },
          runningMode: "VIDEO", numHands: 1,
        });
        setReady(true);
        const loop = () => {
          if (stop) return;
          if (video.readyState >= 2) {
            const g = rec.recognizeForVideo(video, performance.now()).gestures?.[0]?.[0];
            if (g && g.score > 0.7 && GESTURES[g.categoryName] && (g.categoryName !== last || Date.now() - lastAt > 2500)) {
              last = g.categoryName; lastAt = Date.now(); handle(g.categoryName);
            }
          }
          raf = requestAnimationFrame(loop);
        };
        loop();
      } catch (e: any) { setErr(`Gesture model failed to load: ${e.message}`); }
    })();
    return () => { stop = true; cancelAnimationFrame(raf); setReady(false); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [on, video]);
  return { ready, err };
}

function VisionPanel() {
  const { stopSpeaking, confirms, respond, listen, toast } = useJarvis();
  const cfg = useData<any>(() => api.get("/api/p/vision/config"));
  const [cam, setCam] = useState(false);
  const [gestures, setGestures] = useState(false);
  const [name, setName] = useState("");
  const [lastGesture, setLastGesture] = useState("");
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);

  useEffect(() => {
    window.dispatchEvent(new CustomEvent("jarvis-camera", { detail: cam }));
    if (!cam) { stream.current?.getTracks().forEach((t) => t.stop()); stream.current = null; return; }
    navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } }).then((s) => {
      stream.current = s; if (video.current) video.current.srcObject = s;
    }).catch((e) => { toast("Camera unavailable", e.message, "warning"); setCam(false); });
  }, [cam, toast]);
  useEffect(() => () => { stream.current?.getTracks().forEach((t) => t.stop()); window.dispatchEvent(new CustomEvent("jarvis-camera", { detail: false })); }, []);

  const g = useGestures(video.current, cam && gestures, (gest) => {
    setLastGesture(gest);
    if (gest === "Open_Palm") stopSpeaking();
    if (gest === "Victory") void listen();
    if ((gest === "Thumb_Up" || gest === "Thumb_Down") && confirms[0]) respond(confirms[0].id, gest === "Thumb_Up");
  });

  const frame = () => {
    const v = video.current!, c = document.createElement("canvas");
    c.width = v.videoWidth; c.height = v.videoHeight; c.getContext("2d")!.drawImage(v, 0, 0);
    return c.toDataURL("image/jpeg", 0.85);
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
      <Card title="Camera (opt-in, processed locally)" icon={<Camera size={14} />} actions={
        <Button variant={cam ? "danger" : "primary"} onClick={() => setCam(!cam)}>{cam ? <><CameraOff size={14} /> Turn off</> : <><Camera size={14} /> Turn on</>}</Button>}>
        <div className="relative aspect-video overflow-hidden rounded-lg border border-line bg-bg">
          {cam ? <video ref={video} autoPlay muted playsInline className="h-full w-full -scale-x-100 object-cover" />
            : <div className="grid h-full place-items-center text-dim">Camera is off</div>}
          {cam && <span className="absolute left-2 top-2 rounded bg-danger px-2 py-0.5 text-xs font-semibold text-white">● LIVE</span>}
        </div>
      </Card>
      <div className="flex flex-col gap-4">
        <Card title="Face recognition" icon={<ScanFace size={14} />}>
          {cfg.data && !cfg.data.face_available ? <p className="text-sm text-dim">Install <code className="font-mono">face-recognition</code> (see requirements-extras.txt) to enable.</p> : <>
            <p className="text-sm text-dim">Known: {cfg.data?.known?.join(", ") || "nobody yet"}</p>
            <div className="flex gap-2">
              <input className="input" placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} aria-label="Name to enrol" />
              <Button disabled={!cam || !name} onClick={async () => { const r = await api.post("/api/p/vision/enroll", { image: frame(), name }); toast(r.error ?? `Enrolled ${name}`); cfg.reload(); }}><UserPlus size={14} /> Enrol</Button>
            </div>
            <Button disabled={!cam} onClick={async () => { const r = await api.post("/api/p/vision/identify", { image: frame() }); toast(r.error ?? (r.name ? `Hello ${r.name}` : r.face ? "Face not recognised" : "No face found")); }}>Who am I?</Button>
          </>}
        </Card>
        <Card title="Gesture control" icon={<Hand size={14} />} actions={<Button disabled={!cam} variant={gestures ? "primary" : "subtle"} onClick={() => setGestures(!gestures)}>{gestures ? "On" : "Off"}</Button>}>
          {gestures && !g.ready && !g.err && <Spinner />}
          <ErrorNote error={g.err} />
          <ul className="text-sm">{Object.entries(GESTURES).map(([k, v]) => (
            <li key={k} className={`flex justify-between py-0.5 ${lastGesture === k ? "text-accent" : ""}`}><span>{{ Open_Palm: "✋", Thumb_Up: "👍", Thumb_Down: "👎", Victory: "✌️" }[k]} {k.replace("_", " ")}</span><span className="text-dim">{v}</span></li>
          ))}</ul>
        </Card>
        <ScreenAsk />
      </div>
    </div>
  );
}

function ScreenAsk() {
  const [q, setQ] = useState("What's on my screen?");
  const [a, setA] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <Card title="Ask about my screen" icon={<MonitorSmartphone size={14} />}>
      <RequirePlugin name="screen" label="Screen vision">
        <div className="flex gap-2"><input className="input" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Question about screen" />
          <Button variant="primary" onClick={async () => { setBusy(true); const r = await api.tool("screen__look", { question: q }); setA(r.answer ?? r.error); setBusy(false); }}>{busy ? <Spinner /> : "Ask"}</Button></div>
        {a && <p className="text-sm whitespace-pre-wrap">{a}</p>}
      </RequirePlugin>
    </Card>
  );
}

export function Vision() {
  return <RequirePlugin name="vision" label="Camera vision is off (opt-in)"><VisionPanel /></RequirePlugin>;
}
