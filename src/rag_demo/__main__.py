import time

# Measure the application start time.
APPLICATION_START_TIME = time.time()

# Disable "module import not at top of file" (aka E402) when importing Typer and other early imports. This is necessary
# so that the initialization of these modules is included in the application startup time.
from typing import Annotated  # noqa: E402

import typer  # noqa: E402

from rag_demo.constants import LocalProviderType  # noqa: E402


def _main(
    name: Annotated[str | None, typer.Option(help="The name you want to want the AI to use with you.")] = None,
    provider: Annotated[LocalProviderType | None, typer.Option(help="The local provider to prefer.")] = None,
) -> None:
    """Talk to Wikipedia."""
    # Import here so that imports run within the typer.run context for prettier stack traces if errors occur.
    # We ignore PLC0415 because we do not want these imports to be at the top of the module as is usually preferred.
    import transformers  # noqa: PLC0415

    from rag_demo.app import RAGDemo  # noqa: PLC0415
    from rag_demo.logic import Logic  # noqa: PLC0415

    # The transformers library likes to print text that interferes with the TUI. Disable it.
    transformers.logging.set_verbosity(verbosity=transformers.logging.CRITICAL)
    transformers.logging.disable_progress_bar()

    logic = Logic(username=name, preferred_provider_type=provider, application_start_time=APPLICATION_START_TIME)
    app = RAGDemo(logic)
    app.run()


def main() -> None:
    """Entrypoint for the rag demo, specifically the `chat` command."""
    typer.run(_main)


if __name__ == "__main__":
    main()
