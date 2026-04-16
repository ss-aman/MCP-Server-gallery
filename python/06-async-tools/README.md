# 06 · Async Concurrent Tools MCP Server

Demonstrates how to run **multiple I/O operations in parallel** inside a single MCP tool using `asyncio.gather()`.

## What it shows

| Concept | Detail |
|---------|--------|
| **Library** | `FastMCP` + `httpx` + `asyncio` |
| **Transport** | stdio |
| **Primitives** | Tools (all async) |
| **Key patterns** | `asyncio.gather()`, `asyncio.Semaphore`, `asyncio.wait_for()`, per-request timeout |

## Tools

| Tool | Description |
|------|-------------|
| `fetch_many` | Fetch a list of URLs concurrently, return status / size / timing |
| `health_check_hosts` | HTTP health-check multiple hostnames at once |
| `dns_lookup_many` | Resolve multiple hostnames to IPs concurrently |
| `download_and_compare` | Fetch ≥2 URLs and compare sizes / response times |
| `run_tasks_with_timeout` | Fan-out batch tasks with a global wall-clock deadline |

## Quick start

```bash
pip install -r requirements.txt
mcp dev server.py
```

Example prompts:
- *"Fetch these 5 URLs and tell me which is the fastest."*
- *"Are github.com, gitlab.com and bitbucket.org all reachable?"*
- *"Look up the IPs for google.com, cloudflare.com and openai.com."*

## Concurrency model

```
Tool call arrives
      │
      ├─ asyncio.gather() ──┬── fetch URL 1 ─ httpx async
      │                     ├── fetch URL 2 ─ httpx async
      │                     └── fetch URL N ─ httpx async
      │                          (capped by Semaphore(10))
      └─ all results merged and returned
```
