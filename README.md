# RAG-demo

Chat with (a small portion of) Wikipedia

⚠️ RAG functionality is still under development. ⚠️

![app screenshot](screenshots/screenshot_062f205a.png "App screenshot (this AI response is not accurate)")

## Requirements

 1. [uv](https://docs.astral.sh/uv/)
 2. [Hugging Face login](https://huggingface.co/docs/huggingface_hub/quick-start#login)
 3. [Ollama](https://ollama.com/) (More LLM providers coming soon...)
 4. At least one of the following:
    - A suitable terminal emulator (in particular, on macOS consider using [iTerm2](https://iterm2.com/) instead of the default [Terminal.app](https://textual.textualize.io/FAQ/#why-doesnt-textual-look-good-on-macos))
    - A web browser

## Run from the repository

Clone this repository and then run one of the options below.

Run in a terminal:
```bash
uv run chat
```

Or run in a web browser:
```bash
uv run textual serve chat
```

## Run from the latest version on PyPI

Run in a terminal:
```bash
uvx --from=jehoctor-rag-demo chat
```

Or run in a web browser:
```bash
uvx --from=jehoctor-rag-demo textual serve chat
```