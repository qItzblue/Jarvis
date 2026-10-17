# Jarvis web

A browser-based J.A.R.V.I.S. assistant backed by [NanoGPT](https://nano-gpt.com) and, optionally, Google Gemini
(set `GEMINI_API_KEY`; Gemini models appear in the picker as `google-direct/...`).
Streaming chat, model picker, voice input (browser speech recognition) and natural spoken replies
(NanoGPT text-to-speech; set `TTS_MODEL` / `TTS_VOICE`, falls back to the browser voice).
Your NanoGPT key stays on the server; `APP_PASSWORD` keeps others from using it.

## Run locally
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your key
set -a; . ./.env; set +a
uvicorn server:app --port 8800
```
Open http://localhost:8800.

## Host on a VPS (Ubuntu) as a real website
1. Point a domain's **A record** at the VPS IP.
2. On the VPS, as root:
   ```bash
   apt install -y git python3-venv caddy
   git clone -b claude/dazzling-wozniak-vwcarw https://github.com/qitzblue/jarvis /opt/jarvis-web
   cd /opt/jarvis-web
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   cp .env.example .env && nano .env        # key + password
   cp deploy/jarvis-web.service /etc/systemd/system/
   systemctl daemon-reload && systemctl enable --now jarvis-web
   sed "s/jarvis.example.com/YOUR.DOMAIN/" deploy/Caddyfile > /etc/caddy/Caddyfile
   systemctl reload caddy
   ufw allow 80,443/tcp
   ```
Caddy gets an HTTPS certificate automatically. HTTPS is required for the microphone button.

Update later: `cd /opt/jarvis-web && git pull && systemctl restart jarvis-web`.
