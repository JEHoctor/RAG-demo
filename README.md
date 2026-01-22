# RAG-demo

Chat with (a small portion of) Wikipedia

⚠️ RAG functionality is still under development. ⚠️

![app screenshot](screenshots/screenshot_062f205a.png "App screenshot (this AI response is not accurate)")

## Requirements

 1. [uv](https://docs.astral.sh/uv/)
 2. At least one of the following:
    - A suitable terminal emulator. In particular, on macOS consider using [iTerm2](https://iterm2.com/) instead of the default Terminal.app ([explanation](https://textual.textualize.io/FAQ/#why-doesnt-textual-look-good-on-macos)). On Linux, you might want to try [kitty](https://sw.kovidgoyal.net/kitty/), [wezterm](https://wezterm.org/), [alacritty](https://alacritty.org/), or [ghostty](https://ghostty.org/) instead of the terminal that came with your DE ([reason](https://darren.codes/posts/textual-copy-paste/)). Windows Terminal should be fine as far as I know.
    - Any common web browser

## Optional stuff that could make your experience better

 1. [Hugging Face login](https://huggingface.co/docs/huggingface_hub/quick-start#login)
 2. API key for your favorite LLM provider (support coming soon)
 3. Ollama installed on your system if you have a GPU
 4. Run RAG-demo on a more capable (bigger GPU) machine over SSH if you can. It is a terminal app after all.


## Run from the repository

First, clone this repository. Then, run one of the options below.

Run in a terminal:
```bash
uv run chat
```

Or run in a web browser:
```bash
uv run textual serve chat
```

## Run from the latest version on PyPI

TODO: test uv automatic torch backend selection:
https://docs.astral.sh/uv/guides/integration/pytorch/#automatic-backend-selection

Run in a terminal:
```bash
uvx --from=jehoctor-rag-demo chat
```

Or run in a web browser:
```bash
uvx --from=jehoctor-rag-demo textual serve chat
```

## CUDA acceleration via Llama.cpp

If you have an NVIDIA GPU with CUDA and build tools installed, you might be able to get CUDA acceleration without installing Ollama.

```bash
CMAKE_ARGS="-DGGML_CUDA=on" uv run chat
```

## Metal acceleration via Llama.cpp (on Apple Silicon)

On an Apple Silicon machine, make sure `uv` runs an ARM interpreter as this should cause it to install Llama.cpp with Metal support.

## Ollama on Linux

Remember that you have to keep Ollama up-to-date manually on Linux.
A recent version of Ollama (v0.11.10 or later) is required to run the [embedding model we use](https://ollama.com/library/embeddinggemma).
See this FAQ: https://docs.ollama.com/faq#how-can-i-upgrade-ollama.
