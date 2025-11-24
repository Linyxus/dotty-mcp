"""
dotty-mcp MCP Server - A Scala 3 (Dotty) compiler wrapper MCP server
"""

import argparse
import atexit
import re
from pathlib import Path
from typing import List, Optional

import pexpect
from mcp.server.fastmcp import FastMCP


class SBTProcess:
    """Manages a persistent SBT process for the Dotty compiler."""

    def __init__(self, root: Path):
        """
        Initialize an SBT process.

        Args:
            root: Root directory of the Dotty project
        """
        self.root = root
        self.process: Optional[pexpect.spawn] = None
        self._start_process()

    def _start_process(self):
        """Start the SBT process and wait for it to be ready."""
        if not self.root.exists():
            raise ValueError(f"Project root {self.root} does not exist.")

        # Check for build.sbt to verify this is an SBT project
        if not (self.root / "build.sbt").exists():
            raise ValueError(f"No build.sbt found in {self.root}. Not a valid SBT project.")

        try:
            self.process = pexpect.spawn(
                'sbt -no-colors',
                cwd=str(self.root),
                encoding='utf-8',
                timeout=300,
                echo=False
            )

            # Wait for SBT prompt - now without ANSI color codes
            index = self.process.expect([
                r'sbt:\w+>\s*',        # Standard prompt like "sbt:scala3> "
                r'>\s*$',              # Simple > prompt
                pexpect.TIMEOUT,
                pexpect.EOF
            ], timeout=120)

            if index >= 3:  # TIMEOUT or EOF
                raise RuntimeError(f"Failed to match prompt. Index: {index}")

        except pexpect.exceptions.TIMEOUT:
            buffer_content = self.process.buffer if hasattr(self.process, 'buffer') else 'N/A'
            before_content = self.process.before if hasattr(self.process, 'before') else 'N/A'
            raise RuntimeError(
                f"SBT process failed to start within timeout period.\n"
                f"Buffer: {buffer_content}\n"
                f"Before: {before_content}"
            )
        except pexpect.exceptions.EOF:
            before_content = self.process.before if hasattr(self.process, 'before') else 'N/A'
            raise RuntimeError(
                f"SBT process terminated unexpectedly during startup.\n"
                f"Before: {before_content}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start SBT process: {e}")

    def execute_command(self, command: str, timeout: int = 300) -> tuple[str, int]:
        """
        Execute a command in the SBT console.

        Args:
            command: The SBT command to execute
            timeout: Timeout in seconds

        Returns:
            Tuple of (output, exit_code)
        """
        if self.process is None or not self.process.isalive():
            raise RuntimeError("SBT process is not running")

        try:
            # Send the command
            self.process.sendline(command)

            # Wait for the command to complete and return to prompt
            # No ANSI codes since we started with -no-colors
            self.process.expect(r'sbt:\w+>\s*', timeout=timeout)

            # Get the output (everything before the next prompt)
            output = self.process.before

            # Clean up the output - remove the command echo and extra whitespace
            lines = output.split('\n')
            if lines and command in lines[0]:
                lines = lines[1:]  # Remove command echo
            output = '\n'.join(lines).strip()

            # Check if compilation was successful
            # SBT returns success/error status in the prompt, but we'll check output
            exit_code = 1 if '[error]' in output.lower() else 0

            return output, exit_code

        except pexpect.exceptions.TIMEOUT:
            return f"Command timed out after {timeout} seconds", 1
        except pexpect.exceptions.EOF:
            return "SBT process terminated unexpectedly", 1
        except Exception as e:
            return f"Error executing command: {e}", 1

    def close(self):
        """Close the SBT process."""
        if self.process and self.process.isalive():
            try:
                self.process.sendline('exit')
                self.process.expect(pexpect.EOF, timeout=10)
            except:
                self.process.terminate(force=True)

    def __del__(self):
        """Cleanup when the object is destroyed."""
        self.close()


class DottyProject:
    """Represents a Dotty project and provides compilation operations."""

    def __init__(self, root: Path):
        """
        Initialize a Dotty project.

        Args:
            root: Root directory of the Dotty project
        """
        self.root = root
        self.sbt_process: Optional[SBTProcess] = None

    def ensure_sbt_running(self):
        """Ensure the SBT process is running."""
        if self.sbt_process is None:
            self.sbt_process = SBTProcess(self.root)

    def scalac(self, file: str, options: List[str]) -> str:
        """
        Compile a Scala file using the Dotty compiler through SBT.

        Args:
            file: The file path to compile (relative to project root)
            options: List of compiler options to pass to scalac

        Returns:
            Compilation output as a string

        Note:
            The -color:never option is automatically added to ensure clean,
            parseable output without ANSI escape codes.
        """
        try:
            self.ensure_sbt_running()

            # Always add -color:never for clean output without ANSI codes
            all_options = ['-color:never'] + (options if options else [])

            # Construct the scalac command
            options_str = ' '.join(all_options)
            command = f"scalac {file} {options_str}"

            # Execute the command
            output, exit_code = self.sbt_process.execute_command(command)

            # Format the output
            if exit_code == 0 and not output:
                return f"Successfully compiled {file}"
            elif exit_code == 0 and output:
                return f"Successfully compiled {file}\n\nOutput:\n{output}"
            else:
                return f"Compilation failed for {file}\n\n{output}"

        except ValueError as e:
            return f"Error: {e}"
        except RuntimeError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    def testCompilation(self, pattern: str) -> str:
        """
        Run the compilation test suite with an optional filter pattern.

        Args:
            pattern: A substring to filter tests by path. If empty, runs all tests.

        Returns:
            Test output as a string
        """
        try:
            self.ensure_sbt_running()

            # Construct the testCompilation command
            if pattern:
                command = f"testCompilation {pattern}"
            else:
                command = "testCompilation"

            # Execute the command
            output, exit_code = self.sbt_process.execute_command(command)

            # Format the output
            if exit_code == 0:
                return f"Test compilation succeeded\n\n{output}" if output else "Test compilation succeeded"
            else:
                return f"Test compilation failed\n\n{output}"

        except ValueError as e:
            return f"Error: {e}"
        except RuntimeError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

    def close(self):
        """Close the SBT process."""
        if self.sbt_process:
            self.sbt_process.close()


# Global project instance
PROJECT: Optional[DottyProject] = None


# Initialize the MCP server
mcp = FastMCP("dotty-mcp")


@mcp.tool()
def scalac(file: str, options: List[str] = None) -> str:
    """
    Compile a Scala file using the Dotty (Scala 3) compiler under development through SBT.

    This tool provides direct access to the development scalac compiler within an SBT session,
    allowing you to compile individual Scala files with custom compiler options.

    The -color:never option is automatically added to all compilations to ensure
    clean, parseable output without ANSI escape codes. You don't need to specify
    this option manually.

    A small trick: you can pass empty arguments to this tool, i.e. `scalac("", [])`,
    to check whether the development compiler compiles.

    Args:
        file: Relative path from project root to the Scala file to compile
              (e.g., "tests/pos/HelloWorld.scala")
        options: List of compiler options to pass to scalac
                (e.g., ["-Xprint:typer", "-Xprint:cc", "-Ycc-verbose"])
                Note: -color:never is automatically prepended

    Returns:
        Compilation output including any errors, warnings, or success messages.

    Example:
        scalac("tests/pos/Test.scala", ["-Xprint:typer"])
    """
    if PROJECT is None:
        return "Error: No Dotty project root specified. Use --root argument."

    if options is None:
        options = []

    return PROJECT.scalac(file, options)


@mcp.tool()
def testCompilation(pattern: str = "") -> str:
    """
    Run the compilation test suite of the development compiler.

    This tool runs the Dotty compiler's compilation test suite, which tests
    the compiler against a collection of Scala source files.

    Args:
        pattern: A simple substring (not a regex) to filter tests. All compilation
                 tests whose path contains this substring will be run.
                 When empty, runs all compilation tests.

    Returns:
        Test output including pass/fail status and any error messages.

    Example:
        testCompilation("pos/i1234")  # Run tests with "pos/i1234" in their path
        testCompilation("")           # Run all compilation tests
    """
    if PROJECT is None:
        return "Error: No Dotty project root specified. Use --root argument."

    return PROJECT.testCompilation(pattern)


def main():
    """Main entry point for the dotty-mcp MCP server."""
    global PROJECT

    parser = argparse.ArgumentParser(
        description="Scala 3 (Dotty) compiler wrapper MCP server"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory of the Dotty project (defaults to current directory)"
    )

    args = parser.parse_args()
    PROJECT = DottyProject(args.root.resolve())

    # Register cleanup handler
    def cleanup():
        if PROJECT:
            PROJECT.close()

    atexit.register(cleanup)

    # Run the server with stdio transport
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
