import { useEffect, useState } from "react";
import { Onboarding } from "./components/Onboarding";
import { Orb } from "./components/Orb";
import { CommandBar, Confirmations, Sidebar, TabId, Toasts, TopBar } from "./components/Shell";
import { useJarvis } from "./lib/store";
import { Chat } from "./tabs/Chat";
import { Home } from "./tabs/Home";
import { Info } from "./tabs/Info";
import { Notes } from "./tabs/Notes";
import { Plugins } from "./tabs/Plugins";
import { Routines } from "./tabs/Routines";
import { Settings } from "./tabs/Settings";
import { SmartHome } from "./tabs/SmartHome";
import { System } from "./tabs/System";
import { Tasks } from "./tabs/Tasks";
import { Vision } from "./tabs/Vision";

const PAGES: Record<TabId, () => React.ReactElement> = {
  home: Home, chat: Chat, tasks: Tasks, notes: Notes, smarthome: SmartHome, system: System, info: Info,
  routines: Routines, plugins: Plugins, vision: Vision, settings: Settings,
};

function store(key: string, value?: string) {
  try { if (value === undefined) return localStorage.getItem(key); localStorage.setItem(key, value); } catch { /* storage blocked */ }
  return null;
}

export default function App() {
  const { orb, level, listen, stopSpeaking, messages } = useJarvis();
  const [tab, setTab] = useState<TabId>(() => (store("jarvis.tab") as TabId) || "home");
  const [mini, setMini] = useState(false);
  const [onboard, setOnboard] = useState(() => !store("jarvis.onboarded"));
  useEffect(() => { store("jarvis.tab", tab); }, [tab]);
  useEffect(() => { void window.jarvisDesktop?.setMiniMode(mini); }, [mini]);

  const Page = PAGES[tab];
  const last = [...messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="flex h-full">
      {!mini && <Sidebar tab={tab} setTab={setTab} />}
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar mini={mini} setMini={setMini} />
        <main className="min-h-0 flex-1 overflow-y-auto p-4">
          {mini ? (
            <div className="flex h-full flex-col items-center justify-center gap-4">
              <Orb state={orb} level={level} size={200} onClick={() => (orb === "speaking" ? stopSpeaking() : void listen())} />
              {last && <p className="panel max-h-60 overflow-y-auto p-3 text-sm whitespace-pre-wrap">{last.text || "…"}</p>}
            </div>
          ) : <Page />}
        </main>
        {tab !== "chat" || mini ? <CommandBar /> : null}
      </div>
      <Confirmations />
      <Toasts />
      {onboard && <Onboarding done={() => { store("jarvis.onboarded", "1"); setOnboard(false); }} />}
    </div>
  );
}
