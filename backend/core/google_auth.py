"""Shared Google OAuth for Calendar and Gmail. Tokens stay in the local data folder."""
import asyncio
from pathlib import Path

from .. import config

SCOPES = ["https://www.googleapis.com/auth/calendar",
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.compose",
          "https://www.googleapis.com/auth/gmail.send"]
TOKEN = config.DATA_DIR / "google_token.json"


def credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    if not TOKEN.exists():
        raise RuntimeError("Google account not connected yet. Use 'Connect Google' in the Plugins tab.")
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    return creds


async def connect(client_file: str) -> dict:
    """Runs the browser OAuth consent flow once."""
    def flow():
        from google_auth_oauthlib.flow import InstalledAppFlow
        creds = InstalledAppFlow.from_client_secrets_file(client_file, SCOPES).run_local_server(port=0)
        TOKEN.write_text(creds.to_json())
    if not Path(client_file).exists():
        return {"error": f"OAuth client file not found: {client_file}"}
    await asyncio.to_thread(flow)
    return {"connected": True}


def service(api: str, version: str):
    from googleapiclient.discovery import build
    return build(api, version, credentials=credentials(), cache_discovery=False)
