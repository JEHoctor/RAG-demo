"""This script coordinates the system for testing the app in a podman container."""  # noqa: INP001

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.syntax import Syntax

chat_test_image = "jehoctor/chat-test-image"
chat_test_image_editable = "jehoctor/chat-test-image-editable"

app = typer.Typer()


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


@app.command()
def build(
    *,
    editable: Annotated[bool, typer.Option(help="Build the editable version of the image")] = False,
    dry_run: Annotated[bool, typer.Option(help="Print the command instead of running it")] = False,
) -> None:
    """Build the podman image for testing."""
    args: list[str] = ["podman", "build", "--format=docker"]
    if editable:
        args.extend(
            [
                "-t",
                chat_test_image_editable,
                "--build-arg",
                "VARIANT=editable",
                "--build-context",
                f"project={Path.cwd()}",
            ],
        )
    else:
        args.extend(["-t", chat_test_image, "--build-arg", "VARIANT=pypi"])
    args.append("podman/test-chat/")

    if dry_run:
        console = Console()
        syntax = Syntax(
            code=" ".join(shlex.quote(arg) for arg in args),
            lexer="bash",
            theme="monokai",
        )
        console.print(syntax)
        return

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
) -> None:
    """Run podman with options needed for testing the rag demo in (semi-)isolated containers."""
    if editable or build_always:
        build(editable=editable, dry_run=dry_run)

    args: list[str] = ["podman", "run", "--rm", "-it", "--init"]
    if use_cache:
        args.extend(["--userns=keep-id", "-v", f"{uv_cache_dir()}:/home/ubuntu/.cache/uv:Z", "-e", "UV_LINK_MODE=copy"])
    if shell:
        args.append("--entrypoint=/bin/bash")
    args.append(chat_test_image_editable if editable else chat_test_image)
    if additional_arguments:
        args.extend(additional_arguments)

    if dry_run:
        console = Console()
        syntax = Syntax(
            code=" ".join(shlex.quote(arg) for arg in args),
            lexer="bash",
            theme="monokai",
        )
        console.print(syntax)
        return

    result = subprocess.run(args=args, check=False)

    if result.returncode != 0:
        raise typer.Exit(result.returncode)


def main() -> None:
    """Entrypoint for the script."""
    app()


if __name__ == "__main__":
    main()
