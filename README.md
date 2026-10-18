# J.A.R.V.I.S

A personal AI desktop assistant inspired by Iron Man's JARVIS. It runs on your own computer, talks and listens, controls your PC and smart home, and keeps everything personal in one local database.

- **Brain:** Claude, NanoGPT or Google Gemini (pick in Settings), with tool use
- **Voice:** "Hey Jarvis" wake word, push-to-talk hotkey, local Whisper speech recognition, Piper / ElevenLabs / built-in voices, interrupt any time
- **37 plugins:** calendar, email, to-dos, notes, weather, news, stocks, smart home, screen vision, routines, Telegram remote and more
- **Desktop app:** Electron + React with 11 tabs (Home, Chat, Tasks, Notes & Memory, Smart Home, System, Info Center, Routines, Plugins, Vision, Settings) and a floating mini mode

## Quick start

You need **Python 3.11+** and **Node.js 20+**.

| OS | Command |
| --- | --- |
| Windows | double-click `start.bat` (or run `.\start.ps1`) |
| macOS / Linux | `./start.sh` |

The first run creates a virtual environment, installs everything, builds the UI and copies `.env.example` to `.env`. Then a setup wizard asks for:

1. your name,
2. an AI provider and its API key (Claude, NanoGPT or Gemini; keys can also go in `.env`),
3. microphone permission,
4. a voice.

### Optional extras

```bash
# Local voice: wake word, Whisper speech-to-text, Piper TTS
.venv/bin/pip install -r backend/requirements-voice.txt

# Google Calendar/Gmail, screenshots, Windows window control, face recognition
.venv/bin/pip install -r backend/requirements-extras.txt
```

For **Piper**, download a voice (for example `en_GB-alan-medium.onnx` and its `.json` from the Piper voices page), set its path in Settings → Voice, and choose the "piper" engine.

### Development mode

```bash
.venv/bin/python -m backend.main      # API on http://127.0.0.1:8765
cd frontend && npm run dev            # Vite + Electron with hot reload
./test.sh                             # pytest + type-check + Vitest
```

## What needs a key

Everything not listed works with no account at all.

| Plugin | Needs | Cost |
| --- | --- | --- |
| AI chat | Anthropic, NanoGPT **or** Google API key | pay-as-you-go |
| Image generation | Google API key (Gemini) or NanoGPT key | per image |
| Commute | Google Maps key with the Distance Matrix API enabled (falls back to your Google key) | Google Maps billing, free monthly credit |
| Calendar + Gmail | Google Cloud OAuth client JSON (Desktop app), then **Plugins → Connect Google account** | free |
| Smart home | Home Assistant URL and long-lived token | free |
| Spotify | Spotify developer app client ID/secret and refresh token; Premium for playback | free API |
| Telegram remote | bot token from @BotFather and your numeric user ID | free |
| To-do sync | Todoist token (optional, the list works locally) | free |
| Package tracking | 17TRACK API key | free tier |
| Flight status | AviationStack key | free tier |
| ElevenLabs voice | ElevenLabs key (optional) | paid |

Weather (Open-Meteo), news (RSS), web search (DuckDuckGo), stocks (Yahoo), crypto (CoinGecko), sports (ESPN), Wikipedia and currency rates (ECB) need no key.

## Safety and privacy

- Sending email, deleting files or notes, closing apps, running scripts, writing code files, creating calendar events and every power action **ask for confirmation** first. You can approve with the buttons, by saying "yes"/"no", or with a 👍/👎 gesture. Requests from Telegram are approved on the desktop.
- The microphone and camera stay off until you turn them on, and the top bar shows **MIC** / **CAM** while they're live. Clipboard history and camera vision are off by default.
- Conversations, notes, memory, settings and API keys entered in the UI live in `data/jarvis.db` on your machine. Text only goes to the AI provider you picked and to the services of plugins you enable. **Settings → Export my data** downloads all of it.

## Architecture

```
backend/
  main.py            FastAPI app factory
  core/assistant.py  conversation loop: memory + history → LLM → tools → streamed reply
  core/llm.py        Claude (Anthropic SDK) and NanoGPT/Gemini (OpenAI-compatible) providers
  core/plugins.py    plugin base class, @tool decorator, auto-discovery, confirmation gate
  core/memory.py     long-term memory with local embeddings
  api/               REST + WebSocket (/ws chat and events, /ws/audio wake word)
  voice/             faster-whisper STT, Piper/ElevenLabs TTS, openWakeWord
  plugins/           one file per skill
frontend/
  electron/          window, global push-to-talk hotkey, mini mode
  src/lib/           API client, WebSocket store, mic pipeline, speech queue
  src/tabs/          the 11 tabs
```

Replies stream token by token. The backend also emits whole sentences so the voice starts speaking before the reply has finished. Pressing the mic, the hotkey or the orb, saying the wake word, or an open-palm gesture stops speech immediately (barge-in) and starts listening.

### Writing a plugin

Drop a file in `backend/plugins/`. It is discovered at startup and shows up in the Plugins tab:

```python
from ..core.plugins import Plugin, tool

class JokesPlugin(Plugin):
    name, title, category, icon = "jokes", "Jokes", "extras", "laugh"
    description = "Tells a random joke."
    settings_schema = {"api_key": {"label": "API key", "type": "string", "secret": True, "env": "JOKES_KEY"}}
    requires = ("api_key",)        # shows "Not configured" until set

    @tool("Tell a random joke.", {"topic": {"type": "string"}}, required=[])
    async def tell(self, topic: str = ""):
        r = await self.ctx.http.get("https://example.com/joke", params={"q": topic})
        return r.json()
```

Use `confirm=True` on any tool that is destructive or reaches outside your computer. Add a test in `backend/tests/test_plugins.py`.

## Known limitations

- Speaker recognition (telling different people's voices apart) is not built yet.
- Media, brightness and window control use OS tools: `pactl`/`brightnessctl`/`playerctl`/`wmctrl` on Linux, AppleScript on macOS (the `brightness` CLI for brightness), PowerShell on Windows. Results vary by desktop environment.
- The NanoGPT image endpoint follows the OpenAI images API format. If your NanoGPT model rejects it, switch the image provider to Gemini.
- Gesture control downloads MediaPipe's model from Google's CDN the first time you turn it on.
