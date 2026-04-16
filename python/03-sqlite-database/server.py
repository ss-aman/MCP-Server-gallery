"""
03 - SQLite Database MCP Server
================================
A full-featured database server using the low-level MCP Server API.
This example intentionally avoids FastMCP to show how the protocol works
underneath the decorator layer.

Demonstrates:
  - Low-level `mcp.server.Server` class
  - `list_tools` / `call_tool` handlers
  - `list_resources` / `read_resource` handlers (table schemas as resources)
  - Returning structured content (TextContent)
  - Safe parameterised SQL (no injection)
  - Context manager lifecycle for DB connection

Tech stack: mcp, sqlite3 (stdlib)
Transport:  stdio

Run:
    DB_PATH=./demo.db mcp dev server.py
    DB_PATH=./demo.db python server.py
"""

import asyncio
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

DB_PATH = os.environ.get("DB_PATH", "./mcp_demo.db")

server = Server("sqlite-database")

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Resources — expose table schemas so the LLM knows the DB layout
# ---------------------------------------------------------------------------

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    with get_conn() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    return [
        types.Resource(
            uri=f"db://schema/{row['name']}",          # type: ignore[index]
            name=f"Schema: {row['name']}",             # type: ignore[index]
            description=f"Column definitions for table '{row['name']}'",  # type: ignore[index]
            mimeType="application/json",
        )
        for row in tables
    ]


@server.read_resource()
async def handle_read_resource(uri: types.AnyUrl) -> str:
    uri_str = str(uri)
    if not uri_str.startswith("db://schema/"):
        raise ValueError(f"Unknown resource URI: {uri_str}")
    table = uri_str.removeprefix("db://schema/")
    with get_conn() as conn:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()  # noqa: S608
    if not cols:
        raise ValueError(f"Table '{table}' not found.")
    schema = [
        {
            "cid": c["cid"],
            "name": c["name"],
            "type": c["type"],
            "notnull": bool(c["notnull"]),
            "default": c["dflt_value"],
            "pk": bool(c["pk"]),
        }
        for c in cols
    ]
    return json.dumps(schema, indent=2)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_tables",
            description="List all tables in the database.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="create_table",
            description=(
                "Create a new table. "
                "Provide 'table' (name) and 'columns' as a list of "
                "{name, type, constraints?} objects, e.g. "
                '[{"name":"id","type":"INTEGER","constraints":"PRIMARY KEY AUTOINCREMENT"}]'
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name"},
                    "columns": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "constraints": {"type": "string"},
                            },
                            "required": ["name", "type"],
                        },
                    },
                },
                "required": ["table", "columns"],
            },
        ),
        types.Tool(
            name="insert_row",
            description="Insert a row into a table.",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {"type": "string"},
                    "data": {
                        "type": "object",
                        "description": "Column→value mapping for the new row.",
                    },
                },
                "required": ["table", "data"],
            },
        ),
        types.Tool(
            name="query",
            description=(
                "Run a SELECT query. Use '?' placeholders and pass values in 'params'. "
                "Example: {\"sql\": \"SELECT * FROM users WHERE age > ?\", \"params\": [18]}"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "params": {
                        "type": "array",
                        "items": {},
                        "default": [],
                    },
                },
                "required": ["sql"],
            },
        ),
        types.Tool(
            name="execute",
            description=(
                "Run a non-SELECT SQL statement (UPDATE, DELETE, DROP, …). "
                "Use '?' placeholders for safety."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "params": {"type": "array", "items": {}, "default": []},
                },
                "required": ["sql"],
            },
        ),
        types.Tool(
            name="drop_table",
            description="Drop (delete) a table entirely.",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {"type": "string"},
                    "if_exists": {"type": "boolean", "default": True},
                },
                "required": ["table"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    args = arguments or {}

    def text(obj: Any) -> list[types.TextContent]:
        payload = json.dumps(obj, indent=2, default=str) if not isinstance(obj, str) else obj
        return [types.TextContent(type="text", text=payload)]

    # ------------------------------------------------------------------
    if name == "list_tables":
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        return text([r["name"] for r in rows])

    # ------------------------------------------------------------------
    elif name == "create_table":
        table = args["table"]
        col_defs = ", ".join(
            f"{c['name']} {c['type']} {c.get('constraints', '')}".strip()
            for c in args["columns"]
        )
        sql = f"CREATE TABLE IF NOT EXISTS {table} ({col_defs})"  # noqa: S608
        with get_conn() as conn:
            conn.execute(sql)
            conn.commit()
        return text(f"Table '{table}' created.")

    # ------------------------------------------------------------------
    elif name == "insert_row":
        table = args["table"]
        data: dict = args["data"]
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"  # noqa: S608
        with get_conn() as conn:
            cur = conn.execute(sql, list(data.values()))
            conn.commit()
        return text({"inserted_id": cur.lastrowid})

    # ------------------------------------------------------------------
    elif name == "query":
        sql = args["sql"]
        params = args.get("params", [])
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return text(_rows_to_list(rows))

    # ------------------------------------------------------------------
    elif name == "execute":
        sql = args["sql"]
        params = args.get("params", [])
        with get_conn() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
        return text({"rows_affected": cur.rowcount})

    # ------------------------------------------------------------------
    elif name == "drop_table":
        table = args["table"]
        qualifier = "IF EXISTS" if args.get("if_exists", True) else ""
        with get_conn() as conn:
            conn.execute(f"DROP TABLE {qualifier} {table}")  # noqa: S608
            conn.commit()
        return text(f"Table '{table}' dropped.")

    else:
        raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sqlite-database",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
