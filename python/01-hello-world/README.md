# 01 · Hello World MCP Server

The simplest possible MCP server — the "Hello World" of MCP.

## What it shows

| Concept | Detail |
|---------|--------|
| **Library** | `FastMCP` (decorator API) |
| **Transport** | stdio (default) |
| **Primitives** | Tools only |
| **Async** | No (sync tools) |

## Tools

| Tool | Description |
|------|-------------|
| `add` | Add two numbers |
| `subtract` | Subtract two numbers |
| `multiply` | Multiply two numbers |
| `divide` | Divide two numbers (guards zero division) |
| `greet` | Greet in 7 languages |
| `reverse_string` | Reverse a string |
| `word_count` | Count words / chars / lines |
| `to_case` | Convert case: upper / lower / title / snake / camel / kebab |

## Quick start

```bash
pip install -r requirements.txt

# Run in dev mode (opens browser inspector)
mcp dev server.py

# Or run directly (for use with an MCP client)
python server.py
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "hello-world": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```
