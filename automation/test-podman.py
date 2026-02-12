"""This script coordinates the system for testing the app in a podman container."""  # noqa: INP001

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

if TYPE_CHECKING:
    from collections.abc import Sequence

chat_test_image = "jehoctor/chat-test-image"
chat_test_image_editable = "jehoctor/chat-test-image-editable"

app = typer.Typer()

console = Console()
err_console = Console(stderr=True, style="bold red")


def uv_cache_dir() -> Path:
    """Get the location of the host's uv cache."""
    try:
        result = subprocess.run(
            args=["uv", "cache", "dir"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.home() / ".cache" / "uv"
    return Path(result.stdout.strip())


def flatten_arg_groups(arg_groups: Sequence[Sequence[str]]) -> list[str]:
    """Flatten a list of argument groups into a list of arguments."""
    return [arg for arg_group in arg_groups for arg in arg_group]


def print_for_dry_run(*, arg_groups: Sequence[Sequence[str]]) -> None:
    """Pretty print a command on multiple lines with bash syntax highlighting.

    Args:
        command_title (str): The title of the command to be displayed above
        arg_groups (Sequence[Sequence[str]]): The groups of arguments to display on each line
    """
    code = ""
    first_line = True
    for arg_group in arg_groups:
        if first_line:
            first_line = False
        else:
            code += " \\\n\t"
        code += " ".join(shlex.quote(arg) for arg in arg_group)
    console.print(code)


@app.command()
def build(
    *,
    editable: Annotated[bool, typer.Option(help="Build the editable version of the image")] = False,
    dry_run: Annotated[bool, typer.Option(help="Print the command instead of running it")] = False,
) -> None:
    """Build the podman image for testing."""
    arg_groups: list[list[str]] = [["podman", "build", "--format=docker"]]
    if editable:
        arg_groups.append(["-t", chat_test_image_editable])
        arg_groups.append(["--build-arg", "VARIANT=editable"])
        arg_groups.append(["--build-context", f"project={Path.cwd()}"])
    else:
        arg_groups.append(["-t", chat_test_image])
        arg_groups.append(["--build-arg", "VARIANT=pypi"])
    arg_groups.append([str(Path.cwd() / "podman" / "test-chat")])

    if dry_run:
        print_for_dry_run(arg_groups=arg_groups)
        return

    args = flatten_arg_groups(arg_groups)
    result = subprocess.run(args=args, check=False)

    if result.returncode != 0:
        raise typer.Exit(result.returncode)


@app.command()
def run(  # noqa: PLR0913
    additional_arguments: Annotated[
        list[str],
        typer.Argument(help="Additional arguments to pass to the container's entrypoint. Can be empty."),
    ] = [],  # noqa: B006
    *,
    shell: Annotated[bool, typer.Option(help="Run bash instead of the default entrypoint")] = False,
    editable: Annotated[bool, typer.Option(help="Run the editable version of the image")] = False,
    use_cache: Annotated[bool, typer.Option(help="Use the host's uv cache")] = True,
    dry_run: Annotated[bool, typer.Option(help="Print the command instead of running it")] = False,
    build_always: Annotated[
        bool,
        typer.Option(help="Build the image before running. (This is always done when running in editable mode.)"),
    ] = False,
    host_ollama: Annotated[bool, typer.Option(help="Connect to Ollama running on the host")] = False,
) -> None:
    """Run podman with options needed for testing the rag demo in (semi-)isolated containers."""
    # base command
    arg_groups: list[list[str]] = [["podman", "run", "--rm", "-it", "--init"]]
    # Forward terminal info so the container can look up the terminal capabilities.
    term: str | None = os.environ.get("TERM")
    if term is not None:
        arg_groups.append(["-e", f"TERM={term}"])
    terminfo: str = os.environ.get("TERMINFO", "/usr/share/terminfo")
    arg_groups.append(["-v", f"{terminfo}:/usr/share/terminfo:ro"])
    arg_groups.append(["-e", "TERMINFO=/usr/share/terminfo"])
    # Handle `--host-ollama`.
    if host_ollama:
        arg_groups.append(["--network=pasta:-T,8081,-T,11434"])
        arg_groups.append(["-e", "TEXTUAL_CONSOLE_HOST=127.0.0.1"])
    else:
        arg_groups.append(["-e", "TEXTUAL_CONSOLE_HOST=host.containers.internal"])
    # Handle `--use-cache`.
    if use_cache:
        arg_groups.append(["--userns=keep-id"])
        arg_groups.append(["-v", f"{uv_cache_dir()}:/home/ubuntu/.cache/uv:z"])
        arg_groups.append(["-e", "UV_LINK_MODE=copy"])
    # Handle `--shell`.
    if shell:
        arg_groups.append(["--entrypoint=/bin/bash"])
    # Handle `--editable`.
    arg_groups.append([chat_test_image_editable if editable else chat_test_image])
    # Handle extra positional arguments.
    if additional_arguments:
        if shell:
            err_console.print(__file__, "Warning: additional arguments are ignored when running in shell mode.")
        else:
            arg_groups.append(additional_arguments)

    # Handle `--build-always` (respecting `--editable` as well).
    if editable or build_always:
        build(editable=editable, dry_run=dry_run)

    if dry_run:
        print_for_dry_run(arg_groups=arg_groups)
        return

    args = flatten_arg_groups(arg_groups)
    result = subprocess.run(args=args, check=False)

    if result.returncode != 0:
        raise typer.Exit(result.returncode)


def main() -> None:
    """Entrypoint for the script."""
    app()


if __name__ == "__main__":
    main()
