import typer


def _main(
    name: str | None = typer.Option(None, help="The name you want to want the AI to use with you."),
) -> None:
    """Talk to Wikipedia."""
    # Import here so that imports run within the typer.run context for prettier stack traces if errors occur.
    # We ignore PLC0415 because we do not want these imports to be at the top of the module as is usually preferred.
    from rag_demo.app import RAGDemo  # noqa: PLC0415
    from rag_demo.logic import Logic  # noqa: PLC0415

    logic = Logic(username=name)
    app = RAGDemo(logic)
    app.run()


def main() -> None:
    """Entrypoint for the rag demo, specifically the `chat` command."""
    typer.run(_main)


if __name__ == "__main__":
    main()
