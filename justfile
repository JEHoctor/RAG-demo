set shell := ["bash", "-c"]

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

# Run the chat command in Textual dev mode
chat-dev:
    uv run textual run --dev -c chat

# Run the chat command in a web browser
serve:
    uv run textual serve --dev chat

# Open a Textual dev console
console:
    uv run textual console

# Run the chat command from PyPI
chat-pypi:
    uv tool run --no-cache --from=jehoctor-rag-demo chat

# Run the chat command from TestPyPI
chat-testpypi:
    uv tool run --no-cache --index=https://test.pypi.org/simple/ --from=jehoctor-rag-demo chat

# Test
test:
    uv run pytest -vv

# Format
format:
    uv run ruff format src/ tests/

# Lint
lint:
    uv run ruff check src/ tests/

# Type check
typecheck:
    uv run mypy src/ tests/
