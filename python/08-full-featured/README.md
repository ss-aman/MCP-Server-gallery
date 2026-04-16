# 08 · Full-Featured MCP Server — Code Review Assistant

The most complete example in this gallery. Uses the **low-level `Server` API** to expose all three MCP primitives: **Tools**, **Prompts**, and **Resources**.

## What it shows

| Concept | Detail |
|---------|--------|
| **Library** | Low-level `mcp.server.Server` (no FastMCP) |
| **Transport** | stdio |
| **Primitives** | **Tools** + **Prompts** + **Resources** (all three) |
| **Stdlib** | `ast`, `difflib`, `tokenize` |
| **Key patterns** | Shared in-memory state across primitives, `GetPromptResult`, `EmbeddedResource`, `PromptMessage` |

## Tools

| Tool | Description |
|------|-------------|
| `analyse_python` | AST analysis: function/class/import counts, type hint detection |
| `lint_python` | Lightweight static analysis without external linters |
| `diff_snippets` | Unified diff between two code versions |
| `save_snippet` | Save code to the session store |
| `get_snippet` | Retrieve a saved snippet |
| `list_snippets` | List all snippet names |
| `token_count` | Count Python tokens by type |

## Prompts

| Prompt | Arguments | Description |
|--------|-----------|-------------|
| `review_code` | `code`, `focus?` | Structured code review request |
| `explain_issue` | `issue`, `code?` | Explain a problem and suggest a fix |
| `refactor_suggestion` | `code`, `goal?` | Request a refactored version |

## Resources

| URI | Description |
|-----|-------------|
| `snippet://<name>` | Any saved code snippet (dynamic) |
| `docs://review-checklist` | Python code review checklist |
| `docs://python-style-guide` | PEP 8 quick reference |

## Quick start

```bash
pip install -r requirements.txt
python server.py        # stdio
mcp dev server.py       # browser inspector
```

## MCP primitives — how they relate

```
                  LLM
                   │
    ┌──────────────┼──────────────────┐
    │              │                  │
  Tools         Prompts          Resources
(actions)    (templates)       (reference data)
    │              │                  │
analyse_python  review_code     docs://review-checklist
lint_python     explain_issue   snippet://my_code
diff_snippets   refactor        docs://python-style-guide
```

Prompts can *embed resources* and tools can *write resources* — they share the same in-memory snippet store.
