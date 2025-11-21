# dotty-mcp

A Model Context Protocol (MCP) server for Scala 3 (Dotty) compiler development.

## Overview

`dotty-mcp` provides a streamlined interface for interacting with the Scala 3 compiler through SBT. It maintains a persistent SBT session and exposes compiler functionality through the MCP protocol, making it ideal for AI-assisted compiler development workflows.

## Features

- **Persistent SBT Session**: Maintains a long-running SBT process for fast compilation
- **Direct scalac Access**: Compile individual files with custom compiler options
- **MCP Integration**: Works seamlessly with Claude Code and other MCP clients

## Installation

### For Claude Code

```bash
cd /path/to/dotty-mcp
uv sync
claude mcp add dotty-mcp -- uv run --directory /path/to/dotty-mcp dotty-mcp --root /path/to/dotty-project
```

Replace `/path/to/dotty-mcp` with the actual path to this repository and `/path/to/dotty-project` with your Dotty compiler repository path.

### Manual Installation

```bash
# Install dependencies
uv sync

# Run the server
uv run dotty-mcp --root /path/to/dotty-project
```

## Usage

The server provides a single tool:

### `scalac(file: str, options: List[str] = None) -> str`

Compiles a Scala file using the Dotty compiler through SBT.

**Parameters:**
- `file`: Relative path from project root to the Scala file (e.g., `"tests/pos/HelloWorld.scala"`)
- `options`: Optional list of compiler options (e.g., `["-Xprint:typer", "-explain"]`)

**Returns:**
Compilation output including errors, warnings, or success messages.

**Example:**
```python
scalac("tests/pos/Test.scala", ["-Xprint:typer"])
```

## Requirements

- Python >= 3.10
- SBT (must be in PATH)
- A Dotty/Scala 3 project with a `build.sbt` file

## Architecture

The tool consists of three main components:

1. **SBTProcess**: Manages the persistent SBT process using `pexpect`
2. **DottyProject**: Wraps the SBT process and provides high-level compilation operations
3. **MCP Server**: Exposes functionality through the FastMCP framework

## Development

This project uses `uv` for dependency management:

```bash
# Install dependencies
uv sync

# Run tests (if available)
uv run pytest
```

## License

MIT
