# dotty-mcp

A Model Context Protocol (MCP) server for developping [the Scala 3 compiler](https://github.com/scala/scala3).

It provides one single tool:
- `scalac(file, options)` which compiles a test file with the development compiler, and returns the outputs.


## Installation

### For Claude Code

```bash
# If running from within your Dotty project directory
claude mcp add dotty-mcp -- uvx dotty-mcp
```

## License

MIT
