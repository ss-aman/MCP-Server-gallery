"""
04 - Weather API MCP Server
=============================
Fetches real weather data using two free, no-key-required APIs:
  • Open-Meteo  — current conditions + forecasts
  • Nominatim   — city → latitude/longitude geocoding

Demonstrates:
  - Async tools with `httpx.AsyncClient`
  - Tool composition (geocode → weather)
  - Returning rich structured data
  - Using `context` (mcp.server.fastmcp.Context) for logging

Tech stack: mcp[cli], httpx
Transport:  stdio

Run:
    pip install mcp[cli] httpx
    mcp dev server.py
"""

import httpx
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("weather-api")

GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _geocode(city: str) -> tuple[float, float, str]:
    """Return (latitude, longitude, display_name) for a city name."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            GEOCODE_URL,
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "mcp-weather-example/1.0"},
        )
        resp.raise_for_status()
        results = resp.json()

    if not results:
        raise ValueError(f"City not found: '{city}'")
    r = results[0]
    return float(r["lat"]), float(r["lon"]), r["display_name"]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_current_weather(city: str, ctx: Context) -> dict:
    """
    Get the current weather conditions for a city.

    Args:
        city: City name, e.g. "Paris", "New York", "Tokyo".

    Returns current temperature, wind speed, weather description, and more.
    """
    await ctx.info(f"Geocoding '{city}'…")
    lat, lon, display_name = await _geocode(city)
    await ctx.info(f"Found: {display_name} ({lat:.4f}, {lon:.4f})")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            WEATHER_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "weather_code",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "surface_pressure",
                ],
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    current = data["current"]
    code = current.get("weather_code", 0)
    return {
        "city": display_name,
        "latitude": lat,
        "longitude": lon,
        "time": current["time"],
        "temperature_c": current["temperature_2m"],
        "feels_like_c": current["apparent_temperature"],
        "humidity_pct": current["relative_humidity_2m"],
        "wind_speed_kmh": current["wind_speed_10m"],
        "wind_direction_deg": current["wind_direction_10m"],
        "pressure_hpa": current["surface_pressure"],
        "condition": WMO_CODES.get(code, f"Code {code}"),
    }


@mcp.tool()
async def get_forecast(city: str, days: int = 7, ctx: Context = None) -> dict:
    """
    Get a daily weather forecast for up to 16 days.

    Args:
        city: City name.
        days: Number of forecast days (1–16, default 7).
    """
    days = max(1, min(days, 16))
    lat, lon, display_name = await _geocode(city)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            WEATHER_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "wind_speed_10m_max",
                ],
                "forecast_days": days,
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "timezone": "auto",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    daily = data["daily"]
    forecast = []
    for i, date in enumerate(daily["time"]):
        code = daily["weather_code"][i]
        forecast.append({
            "date": date,
            "condition": WMO_CODES.get(code, f"Code {code}"),
            "max_temp_c": daily["temperature_2m_max"][i],
            "min_temp_c": daily["temperature_2m_min"][i],
            "precipitation_mm": daily["precipitation_sum"][i],
            "max_wind_kmh": daily["wind_speed_10m_max"][i],
        })

    return {"city": display_name, "timezone": data.get("timezone"), "forecast": forecast}


@mcp.tool()
async def geocode_city(city: str) -> dict:
    """
    Convert a city name to geographic coordinates.

    Args:
        city: City name to geocode.
    """
    lat, lon, display_name = await _geocode(city)
    return {"city": display_name, "latitude": lat, "longitude": lon}


@mcp.tool()
async def get_weather_by_coordinates(
    latitude: float, longitude: float, ctx: Context
) -> dict:
    """
    Get current weather for an exact latitude/longitude position.

    Args:
        latitude:  Latitude in decimal degrees (-90 to 90).
        longitude: Longitude in decimal degrees (-180 to 180).
    """
    await ctx.info(f"Fetching weather for ({latitude}, {longitude})…")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "weather_code",
                    "wind_speed_10m",
                ],
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    current = data["current"]
    code = current.get("weather_code", 0)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "time": current["time"],
        "temperature_c": current["temperature_2m"],
        "feels_like_c": current["apparent_temperature"],
        "humidity_pct": current["relative_humidity_2m"],
        "wind_speed_kmh": current["wind_speed_10m"],
        "condition": WMO_CODES.get(code, f"Code {code}"),
    }


if __name__ == "__main__":
    mcp.run()
