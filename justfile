set shell := ["bash", "-c"]
set positional-arguments

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
chat *ARGS:
    uv run chat "$@"

# Run the chat command in dev mode
chat-dev *ARGS:
    uv run textual run --dev -c chat "$@"

# Run the chat command in a web browser
serve *ARGS:
    uv run textual serve chat "$@"

# Run the chat command in a web browser in dev mode
serve-dev *ARGS:
    uv run textual serve --dev chat "$@"

# Open a Textual dev console
console:
    uv run textual console -x EVENT

# Open a Textual dev console excluding all messages but INFO
console-info:
    uv run textual console -x EVENT -x DEBUG -x WARNING -x ERROR -x PRINT -x SYSTEM -x LOGGING -x WORKER

# Run the chat command from PyPI
chat-pypi *ARGS:
    uvx --torch-backend=auto --from=jehoctor-rag-demo@latest chat "$@"

# Run the chat command from TestPyPI
chat-testpypi *ARGS:
    uvx --torch-backend=auto --index=https://test.pypi.org/simple/ --index-strategy=unsafe-best-match --from=jehoctor-rag-demo@latest chat "$@"

# Run the podman-based isolated testing system (see automation/test-podman.py)
podman *ARGS:
    uv run automation/test-podman.py "$@"

# Test
test:
    uv run --group=test --no-dev pytest -vv --cov=src --cov-report=term --cov-fail-under=45 tests/

# Format
format:
    uv run ruff format src/ tests/

# Lint
lint:
    uv run ruff check src/ tests/

# Type check
typecheck:
    uv run ty check src/
    uv run --group=test ty check tests/

# Type check with mypy
typecheck-alternate:
    uv run mypy src/ tests/

# Type check with all type checkers
typecheck-all: typecheck typecheck-alternate

# Show outdated packages
outdated:
    uv run uv-outdated --show-headers --group-by-ancestor
