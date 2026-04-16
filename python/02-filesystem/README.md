# 02 · Filesystem MCP Server

A sandboxed filesystem server that exposes local files as **resources** and file operations as **tools**.

## What it shows

| Concept | Detail |
|---------|--------|
| **Library** | `FastMCP` |
| **Transport** | stdio |
| **Primitives** | Tools + Resources |
| **Stdlib** | `pathlib` |
| **Safety** | All paths confined to a sandbox root |

## Tools

| Tool | Description |
|------|-------------|
| `list_directory` | List files and subdirectories |
| `read_file` | Read a file's text content |
| `write_file` | Write (or overwrite) a file |
| `append_file` | Append text to a file |
| `delete_file` | Delete a file |
| `create_directory` | Create a directory tree |
| `search_files` | Glob search inside the sandbox |
| `file_info` | Get size, type, extension metadata |

## Resources

| URI pattern | Description |
|-------------|-------------|
| `file://{path}` | Read a file directly as a resource |

## Quick start

```bash
pip install -r requirements.txt

# Point the server at a directory (defaults to ~/mcp-sandbox)
ROOT_DIR=/tmp/my-sandbox mcp dev server.py
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": { "ROOT_DIR": "/tmp/my-sandbox" }
    }
  }
}
```

> **Safety note**: The server prevents path traversal attacks — any path that resolves outside `ROOT_DIR` is rejected.
