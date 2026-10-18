from ..core.plugins import Plugin, tool

# factor to the base unit of each dimension
UNITS = {
    "length": {"m": 1, "km": 1000, "cm": 0.01, "mm": 0.001, "mi": 1609.344, "yd": 0.9144, "ft": 0.3048,
               "in": 0.0254, "nmi": 1852},
    "mass": {"kg": 1, "g": 0.001, "mg": 1e-6, "t": 1000, "lb": 0.45359237, "oz": 0.028349523125, "st": 6.35029318},
    "volume": {"l": 1, "ml": 0.001, "m3": 1000, "gal": 3.785411784, "qt": 0.946352946, "pt": 0.473176473,
               "cup": 0.2365882365, "floz": 0.0295735295625, "tbsp": 0.01478676478, "tsp": 0.00492892159},
    "speed": {"m/s": 1, "km/h": 1 / 3.6, "mph": 0.44704, "knot": 0.514444},
    "data": {"b": 1, "kb": 1e3, "mb": 1e6, "gb": 1e9, "tb": 1e12, "kib": 1024, "mib": 1024 ** 2, "gib": 1024 ** 3},
    "time": {"s": 1, "min": 60, "h": 3600, "day": 86400, "week": 604800},
    "area": {"m2": 1, "km2": 1e6, "ha": 1e4, "acre": 4046.8564224, "ft2": 0.09290304},
}
ALIASES = {"meter": "m", "meters": "m", "metre": "m", "kilometer": "km", "kilometers": "km", "mile": "mi",
           "miles": "mi", "foot": "ft", "feet": "ft", "inch": "in", "inches": "in", "kilogram": "kg",
           "kilograms": "kg", "kilo": "kg", "kilos": "kg", "pound": "lb", "pounds": "lb", "lbs": "lb", "gram": "g",
           "grams": "g", "ounce": "oz", "ounces": "oz", "liter": "l", "litre": "l", "liters": "l", "gallon": "gal",
           "gallons": "gal", "kph": "km/h", "hour": "h", "hours": "h", "minute": "min", "minutes": "min",
           "second": "s", "seconds": "s", "days": "day", "c": "celsius", "f": "fahrenheit", "k": "kelvin"}
TEMPS = {"celsius", "fahrenheit", "kelvin"}


def convert_units(value: float, src: str, dst: str) -> float:
    src, dst = ALIASES.get(src.lower(), src.lower()), ALIASES.get(dst.lower(), dst.lower())
    if src in TEMPS and dst in TEMPS:
        c = value if src == "celsius" else (value - 32) * 5 / 9 if src == "fahrenheit" else value - 273.15
        return c if dst == "celsius" else c * 9 / 5 + 32 if dst == "fahrenheit" else c + 273.15
    for table in UNITS.values():
        if src in table and dst in table:
            return value * table[src] / table[dst]
    raise ValueError(f"Can't convert {src} to {dst}")


class ConvertPlugin(Plugin):
    name, title, category, icon = "convert", "Unit & currency converter", "info", "arrow-left-right"
    description = "Converts units offline and currencies with free ECB rates (frankfurter.app)."

    @tool("Convert a value between units (length, mass, volume, temperature, speed, data, time, area).", {
        "value": {"type": "number"}, "from_unit": {"type": "string"}, "to_unit": {"type": "string"}})
    async def units(self, value: float, from_unit: str, to_unit: str):
        return {"value": value, "from": from_unit, "to": to_unit,
                "result": round(convert_units(float(value), from_unit, to_unit), 6)}

    @tool("Convert money between currencies (ISO codes like USD, EUR, GBP).", {
        "amount": {"type": "number"}, "from_currency": {"type": "string"}, "to_currency": {"type": "string"}})
    async def currency(self, amount: float, from_currency: str, to_currency: str):
        src, dst = from_currency.upper(), to_currency.upper()
        r = await self.ctx.http.get("https://api.frankfurter.app/latest", params={"from": src, "to": dst})
        r.raise_for_status()
        rate = r.json()["rates"][dst]
        return {"amount": amount, "from": src, "to": dst, "rate": rate, "result": round(float(amount) * rate, 2)}
