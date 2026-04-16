# 03 · SQLite Database MCP Server

A full database CRUD server that intentionally uses the **low-level `Server` API** instead of FastMCP — great for understanding how MCP works under the hood.

## What it shows

| Concept | Detail |
|---------|--------|
| **Library** | Low-level `mcp.server.Server` |
| **Transport** | stdio |
| **Primitives** | Tools + Resources |
| **Stdlib** | `sqlite3` |
| **Key pattern** | Manual `list_tools` / `call_tool` / `list_resources` / `read_resource` handlers |

## Tools

| Tool | Description |
|------|-------------|
| `list_tables` | List all tables in the DB |
| `create_table` | Create a table with column definitions |
| `insert_row` | Insert a row via a column→value dict |
| `query` | Run a SELECT with `?` parameterised placeholders |
| `execute` | Run UPDATE / DELETE / DDL statements |
| `drop_table` | Drop a table |

## Resources

Each table's schema is exposed as a resource at `db://schema/<table_name>` so the LLM can inspect column names and types before writing queries.

## Quick start

```bash
pip install -r requirements.txt

# Use a specific DB file (defaults to ./mcp_demo.db)
DB_PATH=./demo.db mcp dev server.py
```

## Example session

```
list_tables                               → []
create_table(table="users",
  columns=[{"name":"id","type":"INTEGER","constraints":"PRIMARY KEY"},
           {"name":"name","type":"TEXT"},
           {"name":"age","type":"INTEGER"}])
insert_row(table="users", data={"name":"Alice","age":30})
query(sql="SELECT * FROM users WHERE age > ?", params=[18])
→ [{"id": 1, "name": "Alice", "age": 30}]
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "sqlite-db": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": { "DB_PATH": "/path/to/my.db" }
    }
  }
}
```
