from ..core.plugins import Plugin, tool

CODES = {0: "clear", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "fog", 51: "light drizzle",
         53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 71: "light snow",
         73: "snow", 75: "heavy snow", 80: "rain showers", 81: "rain showers", 82: "violent showers",
         95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail"}


class WeatherPlugin(Plugin):
    name, title, category, icon = "weather", "Weather", "info", "cloud-sun"
    description = "Current weather and forecast. Free via Open-Meteo; OpenWeather optional."
    settings_schema = {
        "location": {"label": "Default location", "type": "string", "default": "London"},
        "units": {"label": "Units", "type": "select", "options": ["metric", "imperial"], "default": "metric"},
        "openweather_key": {"label": "OpenWeather API key (optional)", "type": "string", "secret": True,
                            "env": "OPENWEATHER_API_KEY"},
    }

    async def geocode(self, place: str) -> dict:
        r = await self.ctx.http.get("https://geocoding-api.open-meteo.com/v1/search",
                                    params={"name": place, "count": 1})
        r.raise_for_status()
        res = (r.json().get("results") or [None])[0]
        if not res:
            raise ValueError(f"Unknown location: {place}")
        return {"name": f"{res['name']}, {res.get('country', '')}".strip(", "),
                "lat": res["latitude"], "lon": res["longitude"]}

    @tool("Get current weather and a short forecast.", {
        "location": {"type": "string", "description": "City; omit for the default location"},
        "days": {"type": "integer", "description": "Forecast days (1-7)"}}, required=[])
    async def forecast(self, location: str = "", days: int = 3):
        loc = await self.geocode(location or self.setting("location"))
        imperial = self.setting("units") == "imperial"
        params = {"latitude": loc["lat"], "longitude": loc["lon"], "forecast_days": max(1, min(int(days), 7)),
                  "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                  "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                  "timezone": "auto"}
        if imperial:
            params |= {"temperature_unit": "fahrenheit", "wind_speed_unit": "mph"}
        r = await self.ctx.http.get("https://api.open-meteo.com/v1/forecast", params=params)
        r.raise_for_status()
        d = r.json()
        cur = d["current"]
        daily = d["daily"]
        return {
            "location": loc["name"], "units": "°F" if imperial else "°C",
            "now": {"temp": cur["temperature_2m"], "feels_like": cur["apparent_temperature"],
                    "humidity": cur["relative_humidity_2m"], "wind": cur["wind_speed_10m"],
                    "conditions": CODES.get(cur["weather_code"], "unknown")},
            "days": [{"date": daily["time"][i], "high": daily["temperature_2m_max"][i],
                      "low": daily["temperature_2m_min"][i], "rain_chance": daily["precipitation_probability_max"][i],
                      "conditions": CODES.get(daily["weather_code"][i], "unknown")} for i in range(len(daily["time"]))],
        }
