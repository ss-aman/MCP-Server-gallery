"""
02 - Filesystem MCP Server
===========================
Exposes local filesystem operations as MCP tools AND resources.

Demonstrates:
  - MCP Resources  (read files via resource URIs)
  - MCP Tools      (list, search, read, write, delete files)
  - FastMCP resource decorators
  - Path safety (operations are confined to a configurable root directory)

Tech stack: mcp[cli], pathlib (stdlib)
Transport:  stdio

Run:
    ROOT_DIR=/tmp/sandbox mcp dev server.py
    ROOT_DIR=/tmp/sandbox python server.py
"""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("filesystem")

# All file operations are confined to this root directory.
# Override via the ROOT_DIR env variable.
ROOT = Path(os.environ.get("ROOT_DIR", Path.home() / "mcp-sandbox")).resolve()
ROOT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_path(relative: str) -> Path:
    """Resolve a user-supplied path and ensure it stays inside ROOT."""
    target = (ROOT / relative).resolve()
    if not target.is_relative_to(ROOT):
        raise PermissionError(f"Path '{relative}' escapes the sandbox root.")
    return target


# ---------------------------------------------------------------------------
# Resources  —  file:// URIs let the client read files without calling a tool
# ---------------------------------------------------------------------------

@mcp.resource("file://{path}")
def read_file_resource(path: str) -> str:
    """
    Read a file as an MCP resource.

    URI pattern: file://relative/path/to/file.txt
    """
    target = _safe_path(path)
    if not target.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    return target.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_directory(path: str = "") -> dict:
    """
    List the contents of a directory inside the sandbox.

    Args:
        path: Relative path from sandbox root (default: root itself).

    Returns a dict with 'files' and 'directories' lists.
    """
    target = _safe_path(path)
    if not target.is_dir():
        raise NotADirectoryError(f"'{path}' is not a directory.")
    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
    return {
        "root": str(ROOT),
        "path": path or ".",
        "directories": [e.name for e in entries if e.is_dir()],
        "files": [e.name for e in entries if e.is_file()],
    }


@mcp.tool()
def read_file(path: str) -> str:
    """
    Read the text content of a file.

    Args:
        path: Relative path from sandbox root.
    """
    target = _safe_path(path)
    if not target.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    return target.read_text(encoding="utf-8")


@mcp.tool()
def write_file(path: str, content: str, overwrite: bool = False) -> str:
    """
    Write text content to a file (creates parent directories as needed).

    Args:
        path:      Relative path from sandbox root.
        content:   Text to write.
        overwrite: If False (default), raises an error if the file already exists.
    """
    target = _safe_path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"'{path}' already exists. Set overwrite=True to replace it.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written {len(content)} characters to {path}"


@mcp.tool()
def append_file(path: str, content: str) -> str:
    """
    Append text to the end of a file (creates it if it doesn't exist).

    Args:
        path:    Relative path from sandbox root.
        content: Text to append.
    """
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(content)
    return f"Appended {len(content)} characters to {path}"


@mcp.tool()
def delete_file(path: str) -> str:
    """
    Delete a file from the sandbox.

    Args:
        path: Relative path from sandbox root.
    """
    target = _safe_path(path)
    if not target.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    target.unlink()
    return f"Deleted {path}"


@mcp.tool()
def create_directory(path: str) -> str:
    """
    Create a directory (and any missing parents) inside the sandbox.

    Args:
        path: Relative path from sandbox root.
    """
    target = _safe_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return f"Directory '{path}' is ready."


@mcp.tool()
def search_files(pattern: str, path: str = "") -> list[str]:
    """
    Search for files matching a glob pattern inside the sandbox.

    Args:
        pattern: Glob pattern, e.g. '**/*.py' or '*.txt'.
        path:    Sub-directory to search in (default: sandbox root).

    Returns a list of relative paths.
    """
    base = _safe_path(path)
    if not base.is_dir():
        raise NotADirectoryError(f"'{path}' is not a directory.")
    results = [str(p.relative_to(ROOT)) for p in base.glob(pattern)]
    return sorted(results)


@mcp.tool()
def file_info(path: str) -> dict:
    """
    Return metadata about a file or directory.

    Args:
        path: Relative path from sandbox root.
    """
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"No such path: {path}")
    stat = target.stat()
    return {
        "path": path,
        "type": "directory" if target.is_dir() else "file",
        "size_bytes": stat.st_size,
        "extension": target.suffix,
    }


if __name__ == "__main__":
    mcp.run()
