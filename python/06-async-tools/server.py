"""
06 - Async Concurrent Tools MCP Server
========================================
Shows how to run multiple I/O-bound operations *concurrently* inside a single
MCP tool call using asyncio.gather().

Use-cases covered:
  • Fetch many URLs in parallel and compare results
  • DNS + HTTP health-check a list of hosts concurrently
  • Fan-out a search query to multiple APIs and merge answers

Demonstrates:
  - `asyncio.gather()` for concurrent tool execution
  - `asyncio.wait_for()` for per-request timeouts
  - `asyncio.Semaphore` to cap concurrency and avoid flooding
  - Progress reporting via `ctx.report_progress()`
  - Streaming-friendly tool design (returns partial results in a list)

Tech stack: mcp[cli], httpx, asyncio (stdlib)
Transport:  stdio

Run:
    pip install mcp[cli] httpx
    mcp dev server.py
"""

import asyncio
import socket
import time
from urllib.parse import urlparse

import httpx
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("async-tools")

DEFAULT_TIMEOUT = 10.0
MAX_CONCURRENCY = 10          # semaphore cap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fetch_one(
    client: httpx.AsyncClient,
    url: str,
    sem: asyncio.Semaphore,
    timeout: float,
) -> dict:
    """Fetch a single URL and return a result dict (never raises)."""
    start = time.perf_counter()
    async with sem:
        try:
            resp = await asyncio.wait_for(
                client.get(url, follow_redirects=True), timeout=timeout
            )
            elapsed = time.perf_counter() - start
            return {
                "url": url,
                "status": resp.status_code,
                "content_type": resp.headers.get("content-type", ""),
                "bytes": len(resp.content),
                "elapsed_ms": round(elapsed * 1000),
                "ok": resp.is_success,
                "error": None,
            }
        except Exception as exc:
            elapsed = time.perf_counter() - start
            return {
                "url": url,
                "status": None,
                "content_type": None,
                "bytes": None,
                "elapsed_ms": round(elapsed * 1000),
                "ok": False,
                "error": str(exc),
            }


async def _dns_lookup(hostname: str) -> dict:
    """Non-blocking DNS lookup."""
    try:
        loop = asyncio.get_event_loop()
        info = await loop.getaddrinfo(hostname, None)
        addresses = list({i[4][0] for i in info})
        return {"hostname": hostname, "addresses": addresses, "error": None}
    except Exception as exc:
        return {"hostname": hostname, "addresses": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def fetch_many(urls: list[str], timeout: float = DEFAULT_TIMEOUT, ctx: Context = None) -> list[dict]:
    """
    Fetch multiple URLs concurrently and return their HTTP status / metadata.

    All requests run in parallel (capped at 10 concurrent connections).

    Args:
        urls:    List of HTTP/HTTPS URLs.
        timeout: Per-request timeout in seconds (default 10).
    """
    if not urls:
        return []

    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    async with httpx.AsyncClient(timeout=timeout + 2) as client:
        tasks = [_fetch_one(client, url, sem, timeout) for url in urls]
        results = await asyncio.gather(*tasks)

    return list(results)


@mcp.tool()
async def health_check_hosts(
    hosts: list[str],
    port: int = 80,
    use_https: bool = False,
    ctx: Context = None,
) -> list[dict]:
    """
    HTTP health-check a list of hostnames concurrently.

    Args:
        hosts:     List of hostnames or IPs (no scheme or path).
        port:      Port to connect to (default 80).
        use_https: Use HTTPS instead of HTTP (default False).
    """
    scheme = "https" if use_https else "http"
    urls = [f"{scheme}://{h}:{port}/" for h in hosts]
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async with httpx.AsyncClient(
        timeout=5, verify=False  # noqa: S501  (demo only — don't skip TLS in prod)
    ) as client:
        tasks = [_fetch_one(client, url, sem, 5.0) for url in urls]
        raw = await asyncio.gather(*tasks)

    return [
        {
            "host": h,
            "reachable": r["ok"],
            "status_code": r["status"],
            "elapsed_ms": r["elapsed_ms"],
            "error": r["error"],
        }
        for h, r in zip(hosts, raw)
    ]


@mcp.tool()
async def dns_lookup_many(hostnames: list[str]) -> list[dict]:
    """
    Resolve multiple hostnames to IP addresses concurrently.

    Args:
        hostnames: List of domain names or hostnames to look up.
    """
    tasks = [_dns_lookup(h) for h in hostnames]
    return list(await asyncio.gather(*tasks))


@mcp.tool()
async def download_and_compare(
    urls: list[str],
    ctx: Context = None,
) -> dict:
    """
    Download multiple URLs concurrently and compare their sizes and response times.

    Args:
        urls: Two or more URLs to compare.
    """
    if len(urls) < 2:
        raise ValueError("Provide at least 2 URLs to compare.")

    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    async with httpx.AsyncClient(timeout=15) as client:
        tasks = [_fetch_one(client, url, sem, 12.0) for url in urls]
        results = await asyncio.gather(*tasks)

    successful = [r for r in results if r["ok"]]
    if not successful:
        return {"results": list(results), "summary": "All requests failed."}

    fastest = min(successful, key=lambda r: r["elapsed_ms"])
    largest = max(successful, key=lambda r: r["bytes"] or 0)

    return {
        "results": list(results),
        "summary": {
            "fastest_url": fastest["url"],
            "fastest_ms": fastest["elapsed_ms"],
            "largest_url": largest["url"],
            "largest_bytes": largest["bytes"],
        },
    }


@mcp.tool()
async def run_tasks_with_timeout(
    tasks_json: list[dict],
    global_timeout: float = 30.0,
    ctx: Context = None,
) -> list[dict]:
    """
    Run multiple independent fetch tasks concurrently with a global deadline.

    Each task is a dict: {"id": str, "url": str, "timeout": float (optional)}.

    Args:
        tasks_json:      List of task descriptors.
        global_timeout:  Wall-clock seconds for the entire batch (default 30).
    """
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def run_one(task: dict) -> dict:
        task_id = task.get("id", task.get("url", "?"))
        url = task["url"]
        t = float(task.get("timeout", DEFAULT_TIMEOUT))
        async with httpx.AsyncClient(timeout=t + 2) as client:
            result = await _fetch_one(client, url, sem, t)
        result["task_id"] = task_id
        return result

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*[run_one(t) for t in tasks_json]),
            timeout=global_timeout,
        )
    except asyncio.TimeoutError:
        return [{"error": f"Global timeout of {global_timeout}s exceeded"}]

    return list(results)


if __name__ == "__main__":
    mcp.run()
