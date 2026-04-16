"""
05 - FastAPI + MCP over HTTP (SSE Transport)
=============================================
Serves MCP over HTTP using Server-Sent Events (SSE) instead of stdio.
This lets any HTTP client (browser, curl, Postman…) talk to the MCP server,
and makes it easy to host on a cloud platform.

The FastMCP instance is mounted as a sub-application inside FastAPI so you
can add ordinary REST endpoints alongside MCP endpoints.

Demonstrates:
  - SSE (HTTP) transport instead of stdio
  - Mounting FastMCP inside a FastAPI app
  - Adding custom REST endpoints alongside MCP
  - CORS configuration for browser clients
  - Lifespan events for startup / shutdown logic

Tech stack: mcp[cli], fastapi, uvicorn, httpx
Transport:  HTTP + SSE  (endpoint: GET /mcp/sse)

Run:
    pip install -r requirements.txt
    uvicorn server:app --reload --port 8000

Connect an MCP client to: http://localhost:8000/mcp/sse
Or browse the REST docs:   http://localhost:8000/docs
"""

import platform
import time
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Create the MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("fastapi-http-example")

SERVER_START_TIME = time.time()


@mcp.tool()
def ping() -> str:
    """Check that the server is alive."""
    return "pong"


@mcp.tool()
def server_info() -> dict:
    """Return metadata about this MCP server process."""
    return {
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 1),
        "python": platform.python_version(),
        "platform": platform.system(),
        "transport": "http+sse",
    }


@mcp.tool()
def echo(message: str) -> str:
    """Echo a message back to the caller."""
    return message


@mcp.tool()
async def fetch_url(url: str) -> dict:
    """
    Fetch a URL and return its status code and content-type.

    Args:
        url: The HTTP/HTTPS URL to fetch.
    """
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        resp = await client.get(url)
    return {
        "url": str(resp.url),
        "status_code": resp.status_code,
        "content_type": resp.headers.get("content-type", ""),
        "content_length": len(resp.content),
    }


@mcp.tool()
def calculate(expression: str) -> dict:
    """
    Safely evaluate a simple mathematical expression.

    Args:
        expression: A Python math expression, e.g. '2 ** 10 + 3 * 7'.
                    Only numeric operations are allowed.
    """
    # Restrict to safe characters only
    allowed = set("0123456789+-*/.()% \t")
    if not all(c in allowed for c in expression):
        raise ValueError("Expression contains disallowed characters.")
    result = eval(expression, {"__builtins__": {}})  # noqa: S307
    return {"expression": expression, "result": result}


# ---------------------------------------------------------------------------
# Build the FastAPI app with the MCP sub-app mounted
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 MCP + FastAPI server starting up…")
    yield
    print("👋 Server shutting down.")


app = FastAPI(
    title="MCP + FastAPI Example",
    description="MCP tools served over HTTP/SSE alongside REST endpoints.",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow all origins for local development — tighten this in production!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the MCP server at /mcp — SSE endpoint will be at /mcp/sse
app.mount("/mcp", mcp.get_asgi_app())


# ---------------------------------------------------------------------------
# Regular REST endpoints (running alongside MCP)
# ---------------------------------------------------------------------------

@app.get("/", tags=["meta"])
def root():
    """API root — links to available endpoints."""
    return {
        "message": "MCP + FastAPI demo server",
        "mcp_sse_endpoint": "/mcp/sse",
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
def health():
    """Health-check endpoint."""
    return {"status": "ok", "uptime_seconds": round(time.time() - SERVER_START_TIME, 1)}


@app.get("/info", tags=["meta"])
def info():
    """Server information."""
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "arch": platform.machine(),
    }


# ---------------------------------------------------------------------------
# Entry point (for direct `python server.py` execution)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
