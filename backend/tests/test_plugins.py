"""At least one test per plugin. Network calls are mocked with respx; OS calls are monkeypatched."""
import base64
import json
from datetime import datetime, timedelta

import httpx
import pytest
import respx

from backend.core import osctl

ALL_PLUGINS = {"alerts", "apps", "briefing", "calendar", "clipboard", "coding", "commute", "convert", "documents",
               "files", "finance", "flights", "focus", "gmail", "homeassistant", "images", "media", "meetings",
               "memory", "news", "notes", "packages", "power", "routines", "screen", "scripts", "sports", "spotify",
               "system", "telegram", "timers", "todo", "vision", "weather", "websearch", "wikipedia", "windows"}


def test_every_plugin_is_discovered(reg):
    assert set(reg.plugins) == ALL_PLUGINS


def test_every_plugin_reports_a_status_and_valid_tool_names(reg):
    import re
    for p in reg.plugins.values():
        assert p.status() in {"ok", "disabled", "not_configured", "missing_dependency"}
        for t in p.tools():
            assert re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", t.name), t.name


@pytest.fixture
def fake_run(monkeypatch):
    calls = []

    async def run(*cmd, timeout=15):
        calls.append(cmd)
        return {"ok": True, "stdout": "", "stderr": "", "code": 0}
    monkeypatch.setattr(osctl, "run", run)
    return calls


# --- core / productivity ---------------------------------------------------
async def test_memory(reg):
    await reg.call("memory__remember", {"fact": "Birthday is 4 July"})
    assert "4 July" in (await reg.call("memory__recall", {"query": "birthday"}))[0]["text"]


@respx.mock
async def test_weather(reg):
    respx.get("https://geocoding-api.open-meteo.com/v1/search").respond(json={"results": [
        {"name": "Paris", "country": "France", "latitude": 48.8, "longitude": 2.3}]})
    respx.get("https://api.open-meteo.com/v1/forecast").respond(json={
        "current": {"temperature_2m": 20, "apparent_temperature": 19, "relative_humidity_2m": 50,
                    "weather_code": 0, "wind_speed_10m": 5},
        "daily": {"time": ["2026-01-01"], "weather_code": [61], "temperature_2m_max": [22],
                  "temperature_2m_min": [12], "precipitation_probability_max": [40]}})
    res = await reg.call("weather__forecast", {"location": "Paris"})
    assert res["location"] == "Paris, France" and res["now"]["conditions"] == "clear"
    assert res["days"][0]["conditions"] == "light rain"


async def test_timers_and_reminders(reg, ctx):
    t = await reg.call("timers__start_timer", {"seconds": 60, "label": "tea"})
    assert (await reg.call("timers__list_timers"))[0]["label"] == "tea"
    assert (await reg.call("timers__cancel_timer", {"id": t["id"]}))["cancelled"]
    past = (datetime.now() - timedelta(minutes=1)).isoformat()
    await reg.call("timers__add_reminder", {"text": "call mum", "when": past})
    q = ctx.bus.subscribe()
    assert reg.plugins["timers"].check_due()[0]["text"] == "call mum"
    assert q.get_nowait()["type"] == "alert"


async def test_notes(reg, approve):
    n = await reg.call("notes__create_note", {"body": "buy milk", "title": "shopping"})
    await reg.call("notes__append_note", {"id": n["id"], "text": "and eggs"})
    found = await reg.call("notes__search_notes", {"query": "eggs"})
    assert found[0]["body"] == "buy milk\nand eggs"
    assert (await reg.call("notes__delete_note", {"id": n["id"]}))["deleted"]


async def test_system(reg):
    s = await reg.call("system__stats")
    assert 0 <= s["memory_percent"] <= 100 and s["cpu_count"] >= 1
    assert isinstance(await reg.call("system__top_processes", {"limit": 3}), list)


@respx.mock
async def test_websearch(reg):
    page = ('<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2F">'
            '<b>Example</b> Site</a><a class="result__snippet" href="#">An &amp; example</a>')
    respx.post("https://html.duckduckgo.com/html/").respond(text=page)
    res = await reg.call("websearch__search", {"query": "example"})
    assert res == [{"title": "Example Site", "url": "https://example.com/", "snippet": "An & example"}]


def test_calendar_needs_client_file(reg, ctx):
    cal = reg.plugins["calendar"]
    assert not cal.is_configured()
    ctx.settings.set("calendar.client_file", "/tmp/client.json")
    assert cal.is_configured()


@respx.mock
async def test_todo_with_todoist_sync(reg, ctx):
    route = respx.post("https://api.todoist.com/rest/v2/tasks").respond(json={"id": "1"})
    t = await reg.call("todo__add", {"text": "pay rent", "priority": 1})
    assert "todoist" not in t and not route.called
    ctx.settings.set("todo.todoist_token", "tok")
    t2 = await reg.call("todo__add", {"text": "gym", "priority": 3})
    assert t2["todoist"] and route.called
    await reg.call("todo__complete", {"id": t["id"]})
    assert [x["text"] for x in await reg.call("todo__list")] == ["gym"]


def test_gmail_builds_raw_message_and_send_requires_confirmation(reg):
    gm = reg.plugins["gmail"]
    raw = base64.urlsafe_b64decode(gm._raw("a@b.c", "Hi", "Body")).decode()
    assert "To: a@b.c" in raw.replace("to:", "To:") and "Subject: Hi" in raw.replace("subject:", "Subject:")
    assert next(t for t in gm.tools() if t.name == "gmail__send").confirm


async def test_meetings_summary_saved_as_note(reg):
    res = await reg.call("meetings__summarise", {"transcript": "We agreed to ship on Friday.", "title": "Standup"})
    assert res["summary"].startswith("SUMMARY") and res["note"]["title"] == "Standup – summary"


async def test_documents(reg, tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("Quarterly results were great.")
    res = await reg.call("documents__summarise", {"path": str(f)})
    assert res["characters"] == 29 and res["answer"].startswith("SUMMARY")
    assert "not found" in (await reg.call("documents__summarise", {"path": "/nope.pdf"}))["error"]


async def test_clipboard_records_history(reg, ctx):
    clip = reg.plugins["clipboard"]
    assert clip.status() == "disabled"  # opt-in
    assert clip.record("hello") and not clip.record("hello")
    ctx.settings.set("plugin.clipboard.enabled", True)
    assert (await reg.call("clipboard__history"))[0]["text"] == "hello"


async def test_focus(reg, ctx):
    ctx.settings.set("focus.work_minutes", 10)
    await reg.call("focus__start_focus", {"rounds": 2})
    st = await reg.call("focus__focus_status")
    assert st["active"] and st["phase"] == "work" and st["rounds"] == 2
    assert (await reg.call("focus__stop_focus"))["stopped"]


async def test_briefing_collects_available_sections(reg, monkeypatch):
    async def fake_forecast(location="", days=3):
        return {"location": "Here"}
    monkeypatch.setattr(reg.plugins["weather"], "forecast", fake_forecast)
    reg.plugins["weather"].forecast._tool = {"description": "", "params": {}, "required": [], "confirm": False}
    async def no_news(limit=8, topic=""):
        return []
    monkeypatch.setattr(reg.plugins["news"], "headlines", no_news)
    res = await reg.call("briefing__morning")
    assert res["calendar"] is None and res["commute"] is None and res["tasks"] == []


# --- info ---------------------------------------------------------------
RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Feed</title>
<item><title>Big story</title><link>https://x/1</link></item>
<item><title>Rocket launch</title><link>https://x/2</link></item></channel></rss>"""


@respx.mock
async def test_news(reg, ctx):
    ctx.settings.set("news.feeds", "https://feed.test/rss")
    respx.get("https://feed.test/rss").respond(content=RSS)
    assert [h["title"] for h in await reg.call("news__headlines", {"topic": "rocket"})] == ["Rocket launch"]


@respx.mock
async def test_finance(reg):
    respx.get("https://query1.finance.yahoo.com/v8/finance/chart/AAPL").respond(json={"chart": {"result": [{
        "meta": {"symbol": "AAPL", "regularMarketPrice": 110, "chartPreviousClose": 100, "currency": "USD"},
        "indicators": {"quote": [{"close": [100, None, 110]}]}}]}})
    respx.get("https://api.coingecko.com/api/v3/simple/price").respond(
        json={"bitcoin": {"usd": 50000, "usd_24h_change": -1.234}})
    assert (await reg.call("finance__stock", {"symbol": "aapl"}))["change_percent"] == 10.0
    assert (await reg.call("finance__crypto", {"ids": "bitcoin"}))[0]["change_percent"] == -1.23


@respx.mock
async def test_sports(reg):
    respx.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard").respond(json={"events": [{
        "name": "Lakers at Celtics", "status": {"type": {"description": "Final", "shortDetail": "Final"}},
        "competitions": [{"competitors": [{"team": {"displayName": "Celtics"}, "score": "101", "homeAway": "home"},
                                          {"team": {"displayName": "Lakers"}, "score": "99", "homeAway": "away"}]}]}]})
    games = await reg.call("sports__scores", {"league": "NBA", "team": "lakers"})
    assert games[0]["status"] == "Final" and games[0]["teams"][0]["score"] == "101"
    assert "Unknown league" in (await reg.call("sports__scores", {"league": "quidditch"}))["error"]


@respx.mock
async def test_wikipedia(reg):
    respx.get("https://en.wikipedia.org/w/api.php").respond(json=["mars", ["Mars"], [], []])
    respx.get("https://en.wikipedia.org/api/rest_v1/page/summary/Mars").respond(
        json={"title": "Mars", "extract": "Fourth planet.", "content_urls": {"desktop": {"page": "u"}}})
    assert (await reg.call("wikipedia__lookup", {"topic": "mars"}))["summary"] == "Fourth planet."


@respx.mock
async def test_convert(reg):
    assert (await reg.call("convert__units", {"value": 100, "from_unit": "celsius", "to_unit": "f"}))["result"] == 212
    assert (await reg.call("convert__units", {"value": 1, "from_unit": "miles", "to_unit": "km"}))["result"] == 1.609344
    respx.get("https://api.frankfurter.app/latest").respond(json={"rates": {"EUR": 0.9}})
    assert (await reg.call("convert__currency", {"amount": 10, "from_currency": "usd",
                                                 "to_currency": "eur"}))["result"] == 9.0


@respx.mock
async def test_packages(reg, ctx):
    assert reg.plugins["packages"].status() == "not_configured"
    ctx.settings.set("packages.api_key", "k")
    respx.post("https://api.17track.net/track/v2.2/register").respond(json={})
    respx.post("https://api.17track.net/track/v2.2/gettrackinfo").respond(json={"data": {"accepted": [{
        "track_info": {"latest_status": {"status": "InTransit"},
                       "latest_event": {"description": "Departed hub", "location": "Leeds"}}}]}})
    assert (await reg.call("packages__track", {"number": "XY1"}))["last_event"] == "Departed hub"


@respx.mock
async def test_flights(reg, ctx):
    ctx.settings.set("flights.api_key", "k")
    respx.get("http://api.aviationstack.com/v1/flights").respond(json={"data": [{
        "flight": {"iata": "BA117"}, "airline": {"name": "British Airways"}, "flight_status": "active",
        "departure": {"airport": "Heathrow"}, "arrival": {"airport": "JFK"}}]})
    res = await reg.call("flights__flight_status", {"flight": "ba 117"})
    assert res["status"] == "active" and res["arrival"]["airport"] == "JFK"


@respx.mock
async def test_commute_uses_google_key_fallback(reg, ctx):
    assert reg.plugins["commute"].status() == "not_configured"
    ctx.settings.set("google.api_key", "gkey")
    assert reg.plugins["commute"].status() == "ok"
    route = respx.get("https://maps.googleapis.com/maps/api/distancematrix/json").respond(json={
        "status": "OK", "origin_addresses": ["A"], "destination_addresses": ["B"], "rows": [{"elements": [{
            "status": "OK", "distance": {"text": "10 km"}, "duration": {"text": "20 mins", "value": 1200},
            "duration_in_traffic": {"text": "25 mins", "value": 1500}}]}]})
    res = await reg.call("commute__travel_time", {"origin": "A", "destination": "B"})
    assert res["minutes"] == 25 and route.calls[0].request.url.params["key"] == "gkey"


# --- computer control ---------------------------------------------------
async def test_apps(reg, fake_run):
    await reg.call("apps__open", {"target": "https://example.com"})
    assert fake_run and "https://example.com" in fake_run[0]
    assert next(t for t in reg.plugins["apps"].tools() if t.name == "apps__close").confirm


async def test_media(reg, fake_run, monkeypatch):
    monkeypatch.setattr(osctl, "SYSTEM", "Darwin")
    await reg.call("media__set_volume", {"level": 150})
    assert fake_run[0] == ("osascript", "-e", "set volume output volume 100")


def test_screen_needs_mss_and_uses_vision(reg):
    scr = reg.plugins["screen"]
    assert "mss" in scr.optional_deps


async def test_screen_look(reg, monkeypatch):
    scr = reg.plugins["screen"]
    monkeypatch.setattr(scr, "capture_png", lambda: b"png")
    assert (await scr.look("what app?"))["answer"].endswith("+image")


async def test_files(reg, ctx, tmp_path, approve):
    (tmp_path / "Report-2026.pdf").write_text("x")
    (tmp_path / "other.txt").write_text("x")
    ctx.settings.set("files.roots", str(tmp_path))
    res = await reg.call("files__search", {"pattern": "report"})
    assert [r["path"].endswith("Report-2026.pdf") for r in res] == [True]
    await reg.call("files__delete_file", {"path": str(tmp_path / "other.txt")})
    assert not (tmp_path / "other.txt").exists()


async def test_power_requires_confirmation(reg, fake_run, monkeypatch):
    async def no(*a, **k):
        return False
    monkeypatch.setattr(reg.ctx.confirm, "request", no)
    await reg.call("power__shutdown")
    assert fake_run == []
    assert all(t.confirm for t in reg.plugins["power"].tools())


async def test_scripts(reg, ctx, fake_run, approve):
    ctx.settings.set("scripts.scripts", json.dumps({"hello": "echo hi"}))
    await reg.call("scripts__run_script", {"name": "hello"})
    assert fake_run[0][-1] == "echo hi"
    assert "No saved script" in (await reg.call("scripts__run_script", {"name": "x"}))["error"]


async def test_windows(reg, fake_run, monkeypatch):
    monkeypatch.setattr(osctl, "SYSTEM", "Linux")
    monkeypatch.setattr(osctl, "have", lambda b: True)
    await reg.call("windows__focus", {"title": "Firefox"})
    assert fake_run[0] == ("wmctrl", "-a", "Firefox")


async def test_coding(reg, tmp_path, approve):
    await reg.call("coding__write_file", {"path": str(tmp_path / "a.py"), "content": "print(1)\n"})
    assert (await reg.call("coding__read_file", {"path": str(tmp_path / "a.py")}))["content"] == "print(1)"
    assert await reg.call("coding__list_dir", {"path": str(tmp_path)}) == ["a.py"]


@respx.mock
async def test_spotify(reg, ctx):
    for k in ("client_id", "client_secret", "refresh_token"):
        ctx.settings.set(f"spotify.{k}", "x")
    respx.post("https://accounts.spotify.com/api/token").respond(json={"access_token": "t", "expires_in": 3600})
    respx.get("https://api.spotify.com/v1/search").respond(json={"tracks": {"items": [
        {"name": "Back in Black", "uri": "spotify:track:1"}]}})
    play = respx.put("https://api.spotify.com/v1/me/player/play").respond(204)
    assert (await reg.call("spotify__play", {"query": "back in black"}))["playing"] == "Back in Black"
    assert json.loads(play.calls[0].request.content) == {"uris": ["spotify:track:1"]}


# --- home, vision, extras, automation, remote ------------------------------
@respx.mock
async def test_homeassistant(reg, ctx):
    ctx.settings.set("homeassistant.url", "http://ha.local:8123")
    ctx.settings.set("homeassistant.token", "t")
    respx.get("http://ha.local:8123/api/states").respond(json=[
        {"entity_id": "light.kitchen", "state": "off", "attributes": {"friendly_name": "Kitchen Light"}},
        {"entity_id": "sensor.temp", "state": "20", "attributes": {}}])
    svc = respx.post("http://ha.local:8123/api/services/light/turn_on").respond(json=[])
    assert len(await reg.call("homeassistant__devices")) == 1
    await reg.call("homeassistant__switch", {"target": "kitchen", "on": True, "brightness": 50})
    assert json.loads(svc.calls[0].request.content) == {"entity_id": "light.kitchen", "brightness_pct": 50}


async def test_vision_is_opt_in(reg, ctx):
    v = reg.plugins["vision"]
    assert v.status() == "disabled"
    ctx.settings.set("plugin.vision.enabled", True)
    assert await reg.call("vision__known_faces") == [] or isinstance(await reg.call("vision__known_faces"), list)


@respx.mock
async def test_images_gemini(reg, ctx):
    assert reg.plugins["images"].status() == "not_configured"
    ctx.settings.set("google.api_key", "g")
    png = base64.b64encode(b"\x89PNG fake").decode()
    respx.post(url__regex=r".*generateContent").respond(json={"candidates": [{"content": {"parts": [
        {"inlineData": {"mimeType": "image/png", "data": png}}]}}]})
    res = await reg.call("images__generate", {"prompt": "a cat"})
    assert res["url"].startswith("/api/p/images/file/")


@respx.mock
async def test_images_nanogpt(reg, ctx):
    ctx.settings.set("images.provider", "nanogpt")
    ctx.settings.set("nanogpt.api_key", "n")
    respx.post("https://nano-gpt.com/api/v1/images/generations").respond(
        json={"data": [{"b64_json": base64.b64encode(b"img").decode()}]})
    assert "file" in await reg.call("images__generate", {"prompt": "a dog"})


async def test_routines_match_and_run(reg):
    r = reg.plugins["routines"]
    await r.start()  # seeds defaults
    assert r.match("Hey Jarvis, good night!")["name"] == "Good night"
    assert r.match("good nightclub") is None
    out = await r.run({"name": "t", "steps": [{"say": "Done."}, {"tool": "convert__units",
                       "args": {"value": 1, "from_unit": "m", "to_unit": "cm"}}, {"tool": "missing__tool"}]})
    assert out.startswith("Done.") and "1 step(s) could not run" in out


async def test_alerts_battery(reg, ctx, monkeypatch):
    from types import SimpleNamespace

    import psutil
    monkeypatch.setattr(psutil, "sensors_battery", lambda: SimpleNamespace(percent=5, power_plugged=False),
                        raising=False)
    q = ctx.bus.subscribe()
    a = reg.plugins["alerts"]
    assert a.check_battery() and a.check_battery() is None  # warns once
    assert q.get_nowait()["title"].startswith("🔋")


@respx.mock
async def test_telegram_whitelist(reg, ctx):
    ctx.settings.set("telegram.bot_token", "T")
    ctx.settings.set("telegram.allowed_user_id", "42")
    tg = reg.plugins["telegram"]
    sent = respx.post("https://api.telegram.org/botT/sendMessage").respond(json={"ok": True})

    async def fake_handle(text, emit, conversation_id=None, source="desktop", images=None):
        await emit({"type": "start", "conversation_id": 7})
        return f"echo {text}"
    ctx.extra["assistant"] = type("A", (), {"handle": staticmethod(fake_handle)})
    assert await tg.handle_update({"message": {"from": {"id": 99}, "text": "hi"}}) is None
    assert await tg.handle_update({"message": {"from": {"id": 42}, "text": "hi"}}) == "echo hi"
    assert tg.conversation_id == 7 and json.loads(sent.calls[0].request.content)["text"] == "echo hi"
