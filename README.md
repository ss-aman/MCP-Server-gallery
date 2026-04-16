# MCP Server Gallery

A collection of Model Context Protocol (MCP) server examples in Python, covering a wide range of use cases, libraries, and techniques.

Each example is self-contained with its own `server.py`, `requirements.txt`, and `README.md`.

---

## Python Examples

| # | Example | Key Tech | Primitives | Transport | Highlights |
|---|---------|----------|------------|-----------|------------|
| 01 | [hello-world](python/01-hello-world/) | `FastMCP` | Tools | stdio | Simplest possible server; math + string tools |
| 02 | [filesystem](python/02-filesystem/) | `FastMCP` + `pathlib` | Tools + Resources | stdio | Sandboxed file I/O; `file://` resource URIs |
| 03 | [sqlite-database](python/03-sqlite-database/) | Low-level `Server` + `sqlite3` | Tools + Resources | stdio | Full CRUD; low-level API; table schemas as resources |
| 04 | [weather-api](python/04-weather-api/) | `FastMCP` + `httpx` | Tools (async) | stdio | Real HTTP API; no key required; async tools |
| 05 | [fastapi-http](python/05-fastapi-http/) | `FastMCP` + `FastAPI` | Tools | **HTTP + SSE** | MCP over the network; REST + MCP side-by-side |
| 06 | [async-tools](python/06-async-tools/) | `FastMCP` + `asyncio` + `httpx` | Tools (async) | stdio | `asyncio.gather`; Semaphore; concurrent fan-out |
| 07 | [data-analysis](python/07-data-analysis/) | `FastMCP` + `pandas` + `numpy` | Tools | stdio | Session state; CSV loading; stats / group-by / filter |
| 08 | [full-featured](python/08-full-featured/) | Low-level `Server` + stdlib | **Tools + Prompts + Resources** | stdio | All three MCP primitives; code review assistant |

---

## Key concepts covered

### MCP Primitives

| Primitive | What it is | Examples |
|-----------|-----------|---------|
| **Tools** | Callable actions the LLM invokes | All examples |
| **Resources** | Static/dynamic content the LLM reads (like GET endpoints) | 02, 03, 08 |
| **Prompts** | Reusable prompt templates with arguments | 08 |

### API styles

| Style | When to use | Examples |
|-------|-------------|---------|
| `FastMCP` (decorator) | Quick start, simple servers | 01, 02, 04, 05, 06, 07 |
| Low-level `Server` | Full control, all primitives, production | 03, 08 |

### Transports

| Transport | Best for | Examples |
|-----------|---------|---------|
| **stdio** | Claude Desktop, Claude Code, local tools | 01–04, 06–08 |
| **HTTP + SSE** | Cloud hosting, browser clients, multi-user | 05 |

### Async patterns

| Pattern | Used in |
|---------|---------|
| `async def` tool | 04, 06 |
| `asyncio.gather()` fan-out | 06 |
| `asyncio.Semaphore` | 06 |
| `asyncio.wait_for()` timeout | 06 |
| `httpx.AsyncClient` | 04, 05, 06 |

---

## Quick start (any example)

```bash
cd python/01-hello-world
pip install -r requirements.txt

# Interactive browser inspector
mcp dev server.py

# Or run directly (for use with an MCP client over stdio)
python server.py
```

## Claude Desktop config (stdio)

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

## Claude Desktop config (HTTP/SSE — example 05)

```json
{
  "mcpServers": {
    "my-server": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

---

## Prerequisites

- Python 3.10+
- `pip install mcp[cli]` (or just `mcp` for the low-level API)
- Per-example dependencies listed in each `requirements.txt`
