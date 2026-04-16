# 05 · FastAPI + MCP over HTTP (SSE Transport)

MCP served over **HTTP with Server-Sent Events** instead of stdio — ideal for cloud deployments and browser-based clients.

## What it shows

| Concept | Detail |
|---------|--------|
| **Library** | `FastMCP` mounted inside `FastAPI` |
| **Transport** | HTTP + SSE (not stdio) |
| **Primitives** | Tools |
| **Key pattern** | `mcp.get_asgi_app()`, CORS middleware, lifespan events, REST + MCP side-by-side |

## Tools

| Tool | Description |
|------|-------------|
| `ping` | Liveness check |
| `server_info` | Uptime, Python version, platform |
| `echo` | Echo a message back |
| `fetch_url` | HEAD-style info about a URL |
| `calculate` | Safe math expression evaluator |

## Quick start

```bash
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

### Endpoints

| URL | Description |
|-----|-------------|
| `GET /` | API root |
| `GET /health` | Health check |
| `GET /docs` | Swagger UI (REST endpoints) |
| `GET /mcp/sse` | **MCP SSE endpoint** (connect your MCP client here) |

## Connect an MCP client

Point your MCP client at `http://localhost:8000/mcp/sse`.

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "fastapi-http": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

## Architecture

```
Browser / MCP Client
        │
        ▼
  FastAPI app  (:8000)
  ├── GET /              → REST
  ├── GET /health        → REST
  ├── GET /docs          → Swagger
  └── /mcp/* (mounted)
        └── GET /mcp/sse → MCP over SSE
```
