import asyncio
import base64
from email.mime.text import MIMEText

from ..core import google_auth
from ..core.plugins import Plugin, tool


class GmailPlugin(Plugin):
    name, title, category, icon = "gmail", "Gmail", "productivity", "mail"
    description = "Reads your inbox and drafts replies. Sending always needs your confirmation."
    optional_deps = ("googleapiclient", "google_auth_oauthlib")
    settings_schema = {"client_file": {"label": "Google OAuth client JSON path", "type": "string",
                                       "env": "GOOGLE_OAUTH_CLIENT_FILE"}}
    requires = ("client_file",)

    @staticmethod
    def _raw(to: str, subject: str, body: str) -> str:
        msg = MIMEText(body)
        msg["to"], msg["subject"] = to, subject
        return base64.urlsafe_b64encode(msg.as_bytes()).decode()

    @tool("List recent emails (optionally with a Gmail search query like 'is:unread').",
          {"query": {"type": "string"}, "limit": {"type": "integer"}}, required=[])
    async def inbox(self, query: str = "is:unread", limit: int = 10):
        def run():
            svc = google_auth.service("gmail", "v1")
            ids = svc.users().messages().list(userId="me", q=query, maxResults=int(limit)).execute()
            out = []
            for m in ids.get("messages", []):
                full = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                                  metadataHeaders=["From", "Subject", "Date"]).execute()
                h = {x["name"]: x["value"] for x in full["payload"]["headers"]}
                out.append({"id": m["id"], "from": h.get("From"), "subject": h.get("Subject"),
                            "date": h.get("Date"), "snippet": full.get("snippet")})
            return out
        return await asyncio.to_thread(run)

    @tool("Read the full text of one email.", {"id": {"type": "string"}})
    async def read(self, id: str):
        def run():
            msg = google_auth.service("gmail", "v1").users().messages().get(userId="me", id=id).execute()
            def walk(p):
                if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
                    return base64.urlsafe_b64decode(p["body"]["data"]).decode(errors="replace")
                return next((t for t in (walk(c) for c in p.get("parts", [])) if t), "")
            return {"id": id, "snippet": msg.get("snippet"), "body": walk(msg["payload"])[:8000]}
        return await asyncio.to_thread(run)

    @tool("Save an email draft (does not send).", {"to": {"type": "string"}, "subject": {"type": "string"},
                                                     "body": {"type": "string"}})
    async def draft(self, to: str, subject: str, body: str):
        raw = self._raw(to, subject, body)
        d = await asyncio.to_thread(lambda: google_auth.service("gmail", "v1").users().drafts().create(
            userId="me", body={"message": {"raw": raw}}).execute())
        return {"draft_id": d.get("id")}

    @tool("Send an email.", {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
          confirm=True)
    async def send(self, to: str, subject: str, body: str):
        raw = self._raw(to, subject, body)
        m = await asyncio.to_thread(lambda: google_auth.service("gmail", "v1").users().messages().send(
            userId="me", body={"raw": raw}).execute())
        return {"sent": m.get("id")}
