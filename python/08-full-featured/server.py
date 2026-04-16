"""
08 - Full-Featured MCP Server (Code Review Assistant)
=======================================================
A production-style MCP server that exposes ALL THREE MCP primitives:

  ┌──────────────────────────────────────────────────────────────┐
  │  TOOLS      — callable actions (analyse, lint, diff, …)     │
  │  PROMPTS    — reusable prompt templates with arguments       │
  │  RESOURCES  — static/dynamic content the LLM can read       │
  └──────────────────────────────────────────────────────────────┘

The domain is "code review" — a realistic use case where an LLM needs
structured tool results, pre-built prompt templates, AND reference docs.

Demonstrates:
  - Low-level `mcp.server.Server` API (no FastMCP) in its full form
  - `list_tools` / `call_tool`
  - `list_prompts` / `get_prompt`
  - `list_resources` / `read_resource`
  - Returning `TextContent`, `EmbeddedResource`, prompt `Message` objects
  - In-process snippet store (shared state across primitives)

Tech stack: mcp, ast (stdlib), difflib (stdlib), tokenize (stdlib)
Transport:  stdio

Run:
    pip install mcp
    python server.py
"""

import ast
import asyncio
import difflib
import json
import keyword
import textwrap
import tokenize
import io
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

server = Server("code-review-assistant")

# ---------------------------------------------------------------------------
# In-memory snippet store  (shared by tools + resources)
# ---------------------------------------------------------------------------

_snippets: dict[str, str] = {
    "example_good": textwrap.dedent("""\
        def calculate_average(numbers: list[float]) -> float:
            \"\"\"Return the arithmetic mean of a list of numbers.\"\"\"
            if not numbers:
                raise ValueError("Cannot calculate average of empty list")
            return sum(numbers) / len(numbers)
    """),
    "example_bad": textwrap.dedent("""\
        def calc(l):
            s = 0
            for i in range(len(l)):
                s = s + l[i]
            return s / len(l)
    """),
}


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def _parse_python(code: str) -> ast.Module | str:
    try:
        return ast.parse(code)
    except SyntaxError as e:
        return str(e)


def _count_tokens(code: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        for tok in tokens:
            name = tokenize.tok_name.get(tok.type, "UNKNOWN")
            counts[name] = counts.get(name, 0) + 1
    except tokenize.TokenError:
        pass
    return counts


def _lint_python(code: str) -> list[dict]:
    """Very lightweight static analysis — no external linters required."""
    issues = []
    tree = _parse_python(code)
    if isinstance(tree, str):
        return [{"line": 0, "severity": "error", "message": f"SyntaxError: {tree}"}]

    for node in ast.walk(tree):
        # Missing docstrings on functions/classes
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)):
                issues.append({
                    "line": node.lineno,
                    "severity": "warning",
                    "message": f"'{node.name}' is missing a docstring.",
                })
        # Bare `except:` (no exception type)
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append({
                "line": node.lineno,
                "severity": "warning",
                "message": "Bare `except:` clause catches all exceptions. Prefer `except Exception:`.",
            })
        # `print()` calls (may be fine, but worth flagging in libraries)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "print":
                issues.append({
                    "line": node.lineno,
                    "severity": "info",
                    "message": "`print()` found — consider using `logging` in library code.",
                })
        # Short variable names (single letter except i,j,k,x,y,z,n)
        if isinstance(node, ast.Name) and len(node.id) == 1 and node.id not in "ijkxyzn_":
            issues.append({
                "line": getattr(node, "lineno", 0),
                "severity": "info",
                "message": f"Single-character variable '{node.id}' — consider a more descriptive name.",
            })

    return issues


# ---------------------------------------------------------------------------
# Resources  —  list_resources / read_resource
# ---------------------------------------------------------------------------

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    dynamic = [
        types.Resource(
            uri=f"snippet://{name}",
            name=f"Code snippet: {name}",
            description=f"Stored Python snippet '{name}'",
            mimeType="text/x-python",
        )
        for name in _snippets
    ]
    static = [
        types.Resource(
            uri="docs://review-checklist",
            name="Code Review Checklist",
            description="Checklist of common things to look for in a Python code review.",
            mimeType="text/markdown",
        ),
        types.Resource(
            uri="docs://python-style-guide",
            name="Python Style Guide (summary)",
            description="Quick reference for PEP 8 and common Python best practices.",
            mimeType="text/markdown",
        ),
    ]
    return dynamic + static


@server.read_resource()
async def handle_read_resource(uri: types.AnyUrl) -> str:
    uri_str = str(uri)

    if uri_str.startswith("snippet://"):
        name = uri_str.removeprefix("snippet://")
        if name not in _snippets:
            raise ValueError(f"Snippet '{name}' not found.")
        return _snippets[name]

    if uri_str == "docs://review-checklist":
        return textwrap.dedent("""\
            # Python Code Review Checklist

            ## Correctness
            - [ ] Logic handles edge cases (empty input, None, overflow)
            - [ ] No off-by-one errors in loops/slices
            - [ ] Exception handling is specific, not bare `except:`

            ## Readability
            - [ ] Functions and variables have descriptive names
            - [ ] Public functions/classes have docstrings
            - [ ] Complex logic has inline comments

            ## Performance
            - [ ] No O(n²) loops where a dict/set would give O(1)
            - [ ] Large data not copied unnecessarily
            - [ ] I/O is async where latency matters

            ## Security
            - [ ] No hardcoded secrets or credentials
            - [ ] External input is validated / sanitised
            - [ ] SQL uses parameterised queries, not f-strings

            ## Maintainability
            - [ ] Functions are short and single-purpose
            - [ ] No magic numbers — use named constants
            - [ ] Tests exist for new logic
        """)

    if uri_str == "docs://python-style-guide":
        return textwrap.dedent("""\
            # Python Style Guide (Quick Reference)

            ## Naming
            - `snake_case` for variables, functions, modules
            - `PascalCase` for classes
            - `UPPER_SNAKE_CASE` for module-level constants
            - Avoid single-letter names except loop indices (i, j, k)

            ## Functions
            - Keep functions ≤ 20 lines where possible
            - Single responsibility: one function, one job
            - Use type hints for public APIs
            - Write docstrings in Google or NumPy style

            ## Formatting (PEP 8)
            - 4-space indentation (no tabs)
            - Lines ≤ 88 characters (Black default)
            - Two blank lines between top-level definitions
            - One blank line between methods inside a class

            ## Imports
            - Group: stdlib → third-party → local (blank line between groups)
            - Absolute imports preferred over relative
            - No wildcard imports (`from module import *`)

            ## Error handling
            - Catch specific exceptions, not bare `except:`
            - Use `logging` in libraries, not `print()`
            - Raise `ValueError` / `TypeError` for bad input

            ## Modern Python (3.10+)
            - Use `match/case` instead of long if/elif chains
            - Use `X | Y` union type hints
            - Use `@dataclass` or `TypedDict` for structured data
        """)

    raise ValueError(f"Unknown resource URI: {uri_str}")


# ---------------------------------------------------------------------------
# Prompts  —  list_prompts / get_prompt
# ---------------------------------------------------------------------------

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="review_code",
            description="Generate a thorough code review for a Python snippet.",
            arguments=[
                types.PromptArgument(name="code", description="Python code to review", required=True),
                types.PromptArgument(name="focus", description="Optional focus area: security, performance, readability", required=False),
            ],
        ),
        types.Prompt(
            name="explain_issue",
            description="Explain a specific code issue and suggest a fix.",
            arguments=[
                types.PromptArgument(name="issue", description="Description of the issue", required=True),
                types.PromptArgument(name="code", description="Relevant code snippet", required=False),
            ],
        ),
        types.Prompt(
            name="refactor_suggestion",
            description="Ask for a refactored version of a code snippet.",
            arguments=[
                types.PromptArgument(name="code", description="Code to refactor", required=True),
                types.PromptArgument(name="goal", description="Refactoring goal (e.g. readability, performance)", required=False),
            ],
        ),
    ]


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    args = arguments or {}

    if name == "review_code":
        code = args.get("code", "(no code provided)")
        focus = args.get("focus", "general")
        return types.GetPromptResult(
            description="Code review prompt",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=textwrap.dedent(f"""\
                            Please review the following Python code. Focus on: **{focus}**.

                            ```python
                            {code}
                            ```

                            Structure your review as:
                            1. **Summary** — one-sentence overall assessment
                            2. **Issues** — numbered list of specific problems (severity: error/warning/info)
                            3. **Suggestions** — concrete improvement recommendations
                            4. **Revised code** — a corrected version if changes are needed
                        """),
                    ),
                )
            ],
        )

    if name == "explain_issue":
        issue = args.get("issue", "(no issue provided)")
        code = args.get("code", "")
        code_block = f"\n```python\n{code}\n```\n" if code else ""
        return types.GetPromptResult(
            description="Explain issue prompt",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=textwrap.dedent(f"""\
                            Explain this code issue clearly for a developer:

                            **Issue:** {issue}
                            {code_block}
                            Please explain:
                            - Why this is a problem
                            - What can go wrong at runtime
                            - How to fix it (with a code example)
                        """),
                    ),
                )
            ],
        )

    if name == "refactor_suggestion":
        code = args.get("code", "(no code provided)")
        goal = args.get("goal", "readability and maintainability")
        return types.GetPromptResult(
            description="Refactor suggestion prompt",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=textwrap.dedent(f"""\
                            Refactor the following Python code with the goal of improving **{goal}**.

                            ```python
                            {code}
                            ```

                            Provide:
                            1. The refactored code
                            2. A brief explanation of each change made
                            3. Any trade-offs introduced by the refactor
                        """),
                    ),
                )
            ],
        )

    raise ValueError(f"Unknown prompt: {name}")


# ---------------------------------------------------------------------------
# Tools  —  list_tools / call_tool
# ---------------------------------------------------------------------------

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="analyse_python",
            description="Parse Python code and return AST stats: function count, class count, imports, complexity hints.",
            inputSchema={
                "type": "object",
                "properties": {"code": {"type": "string", "description": "Python source code"}},
                "required": ["code"],
            },
        ),
        types.Tool(
            name="lint_python",
            description="Run lightweight static analysis on Python code without external linters.",
            inputSchema={
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        ),
        types.Tool(
            name="diff_snippets",
            description="Produce a unified diff between two code strings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "before": {"type": "string", "description": "Original code"},
                    "after": {"type": "string", "description": "Revised code"},
                    "label": {"type": "string", "description": "Filename label for the diff header", "default": "code"},
                },
                "required": ["before", "after"],
            },
        ),
        types.Tool(
            name="save_snippet",
            description="Save a code snippet to the session store (also exposed as a resource).",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "code": {"type": "string"},
                },
                "required": ["name", "code"],
            },
        ),
        types.Tool(
            name="get_snippet",
            description="Retrieve a previously saved code snippet by name.",
            inputSchema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        ),
        types.Tool(
            name="list_snippets",
            description="List all snippet names in the session store.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="token_count",
            description="Count Python tokens by type (NAME, OP, NUMBER, STRING, …).",
            inputSchema={
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.EmbeddedResource]:
    args = arguments or {}

    def text(obj: Any) -> list[types.TextContent]:
        s = json.dumps(obj, indent=2, default=str) if not isinstance(obj, str) else obj
        return [types.TextContent(type="text", text=s)]

    # ------------------------------------------------------------------
    if name == "analyse_python":
        code = args["code"]
        tree = _parse_python(code)
        if isinstance(tree, str):
            return text({"error": tree})

        functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        returns = [n for n in ast.walk(tree) if isinstance(n, ast.Return)]

        return text({
            "lines": len(code.splitlines()),
            "functions": [{"name": f.name, "line": f.lineno, "args": len(f.args.args)} for f in functions],
            "classes": [{"name": c.name, "line": c.lineno} for c in classes],
            "imports": [ast.unparse(i) for i in imports],
            "return_statements": len(returns),
            "has_type_hints": any(
                f.returns or any(a.annotation for a in f.args.args)
                for f in functions
            ),
        })

    # ------------------------------------------------------------------
    elif name == "lint_python":
        issues = _lint_python(args["code"])
        return text({
            "issue_count": len(issues),
            "errors": [i for i in issues if i["severity"] == "error"],
            "warnings": [i for i in issues if i["severity"] == "warning"],
            "info": [i for i in issues if i["severity"] == "info"],
        })

    # ------------------------------------------------------------------
    elif name == "diff_snippets":
        before_lines = args["before"].splitlines(keepends=True)
        after_lines = args["after"].splitlines(keepends=True)
        label = args.get("label", "code")
        diff = "".join(difflib.unified_diff(
            before_lines, after_lines,
            fromfile=f"{label} (before)",
            tofile=f"{label} (after)",
        ))
        return text(diff or "No differences found.")

    # ------------------------------------------------------------------
    elif name == "save_snippet":
        _snippets[args["name"]] = args["code"]
        return text(f"Snippet '{args['name']}' saved. Access it via resource URI: snippet://{args['name']}")

    # ------------------------------------------------------------------
    elif name == "get_snippet":
        snippet_name = args["name"]
        if snippet_name not in _snippets:
            raise ValueError(f"Snippet '{snippet_name}' not found. Use list_snippets to see available names.")
        return text(_snippets[snippet_name])

    # ------------------------------------------------------------------
    elif name == "list_snippets":
        return text(list(_snippets.keys()))

    # ------------------------------------------------------------------
    elif name == "token_count":
        counts = _count_tokens(args["code"])
        return text(counts)

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
                server_name="code-review-assistant",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
