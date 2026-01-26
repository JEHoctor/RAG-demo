set shell := ["bash", "-c"]

chat_test_image := "jehoctor/chat-test-image"
uv_cache_dir := `uv cache dir 2>/dev/null || echo ~/.cache/uv`

# List available commands
default:
    @just --list

# Delete old package builds
clean:
    rm -rf dist/

# Build the package
build:
    uv build

# Upload package to PyPI
publish: clean build
    uv publish ${JEHOCTOR_RAG_DEMO_PUBLISH_TOKEN:+--token=$JEHOCTOR_RAG_DEMO_PUBLISH_TOKEN}

# Upload package to TestPyPI
publish-test: clean build
    uv publish ${JEHOCTOR_RAG_DEMO_TEST_PUBLISH_TOKEN:+--token=$JEHOCTOR_RAG_DEMO_TEST_PUBLISH_TOKEN} --index testpypi

# Run the chat command
chat:
    uv run chat

# Run the chat command in dev mode
chat-dev:
    uv run textual run --dev -c chat

# Run the chat command in a web browser
serve:
    uv run textual serve chat

# Run the chat command in a web browser in dev mode
serve-dev:
    uv run textual serve --dev chat

# Open a Textual dev console
console:
    uv run textual console -x EVENT

# Open a Textual dev console excluding all messages but INFO
console-info:
    uv run textual console -x EVENT -x DEBUG -x WARNING -x ERROR -x PRINT -x SYSTEM -x LOGGING -x WORKER

# Run the chat command from PyPI
chat-pypi:
    uvx --torch-backend=auto --from=jehoctor-rag-demo@latest chat

# Run the chat command from TestPyPI
chat-testpypi:
    uvx --torch-backend=auto --index=https://test.pypi.org/simple/ --index-strategy=unsafe-best-match --from=jehoctor-rag-demo@latest chat

# Build the container image for running from PyPI
build-podman-image:
    podman build --format docker -t {{chat_test_image}} podman/test-chat-pypi/

# Run the chat command from PyPI in a container
chat-podman:
    podman run --rm -it --init \
        --userns=keep-id \
        -v {{uv_cache_dir}}:/home/ubuntu/.cache/uv:Z \
        {{chat_test_image}}

# Run the chat command from PyPI in a container, isolated from the host uv cache
chat-podman-no-cache:
    podman run --rm -it --init \
        {{chat_test_image}}

# Run a shell in a container from the chat-podman image
shell-podman:
    podman run --rm -it --init \
        --userns=keep-id \
        -v {{uv_cache_dir}}:/home/ubuntu/.cache/uv:Z \
        --entrypoint=/bin/bash \
        {{chat_test_image}}

# Run a shell in a container from the chat-podman image, isolated from the host uv cache
shell-podman-no-cache:
    podman run --rm -it --init \
        --entrypoint=/bin/bash \
        {{chat_test_image}}

# Test
test:
    uv run --group=test --no-dev pytest -vv --cov=src --cov-report=term --cov-fail-under=35 tests/

# Format
format:
    uv run ruff format src/ tests/

# Lint
lint:
    uv run ruff check src/ tests/

# Type check
typecheck:
    uv run ty check src/ tests/

# Type check with mypy
typecheck-alternate:
    uv run mypy src/ tests/

# Type check with all type checkers
typecheck-all: typecheck typecheck-alternate
