# 04 · Weather API MCP Server

Real weather data — **no API key required**. Uses Open-Meteo (weather) and Nominatim (geocoding).

## What it shows

| Concept | Detail |
|---------|--------|
| **Library** | `FastMCP` + `httpx` |
| **Transport** | stdio |
| **Primitives** | Tools (async) |
| **Key pattern** | `async def` tools, `Context` for progress logging, `httpx.AsyncClient` |

## Tools

| Tool | Description |
|------|-------------|
| `get_current_weather` | Current conditions for a named city |
| `get_forecast` | Daily forecast up to 16 days |
| `geocode_city` | City name → latitude/longitude |
| `get_weather_by_coordinates` | Current weather at exact coordinates |

## Quick start

```bash
pip install -r requirements.txt
mcp dev server.py
```

Example prompts once connected:
- *"What's the weather in Tokyo?"*
- *"Give me a 5-day forecast for Buenos Aires."*
- *"Is it raining in London right now?"*

## APIs used

| Service | URL | Key needed? |
|---------|-----|-------------|
| Open-Meteo | `api.open-meteo.com` | No |
| Nominatim (OSM) | `nominatim.openstreetmap.org` | No |

## Claude Desktop config

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```
