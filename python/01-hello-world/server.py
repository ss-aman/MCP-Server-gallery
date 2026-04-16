"""
01 - Hello World MCP Server
============================
The simplest possible MCP server using FastMCP.
Demonstrates: tools, type hints as schema, stdio transport.

Tech stack: mcp[cli] (FastMCP decorator API)
Transport:  stdio (default — works with Claude Desktop, Claude Code, etc.)

Run:
    python server.py          # stdio mode (used by MCP clients)
    mcp dev server.py         # interactive inspector in the browser
"""

from mcp.server.fastmcp import FastMCP

# FastMCP auto-generates the server name and capabilities
mcp = FastMCP("hello-world")


# --- Math tools -----------------------------------------------------------

@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b. Raises an error when b is zero."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


# --- String tools ---------------------------------------------------------

@mcp.tool()
def greet(name: str, language: str = "english") -> str:
    """
    Greet someone in different languages.

    Supported languages: english, spanish, french, german, japanese, portuguese, arabic.
    """
    greetings = {
        "english":    f"Hello, {name}!",
        "spanish":    f"¡Hola, {name}!",
        "french":     f"Bonjour, {name}!",
        "german":     f"Hallo, {name}!",
        "japanese":   f"こんにちは、{name}！",
        "portuguese": f"Olá, {name}!",
        "arabic":     f"مرحبا، {name}!",
    }
    lang = language.lower()
    if lang not in greetings:
        raise ValueError(f"Unknown language '{language}'. Supported: {', '.join(greetings)}")
    return greetings[lang]


@mcp.tool()
def reverse_string(text: str) -> str:
    """Reverse the characters in a string."""
    return text[::-1]


@mcp.tool()
def word_count(text: str) -> dict:
    """
    Count words, characters, and lines in the given text.

    Returns a dict with keys: words, characters, characters_no_spaces, lines.
    """
    return {
        "words": len(text.split()),
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "lines": len(text.splitlines()) or 1,
    }


@mcp.tool()
def to_case(text: str, case: str) -> str:
    """
    Convert text to a specific case.

    case options: upper, lower, title, snake, camel, kebab
    """
    match case.lower():
        case "upper":
            return text.upper()
        case "lower":
            return text.lower()
        case "title":
            return text.title()
        case "snake":
            return "_".join(text.lower().split())
        case "camel":
            words = text.split()
            return words[0].lower() + "".join(w.title() for w in words[1:])
        case "kebab":
            return "-".join(text.lower().split())
        case _:
            raise ValueError(f"Unknown case '{case}'. Use: upper, lower, title, snake, camel, kebab")


if __name__ == "__main__":
    mcp.run()
