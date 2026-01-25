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
    uv run textual console -x EVENT

# Open a Textual dev console excluding all messages but INFO
console-info:
    uv run textual console -x EVENT -x DEBUG -x WARNING -x ERROR -x PRINT -x SYSTEM -x LOGGING -x WORKER

# Run the chat command from PyPI
chat-pypi:
    uv tool run --no-cache --torch-backend=auto --from=jehoctor-rag-demo@latest chat

# Run the chat command from TestPyPI
chat-testpypi:
    uv tool run --no-cache --torch-backend=auto --index=https://test.pypi.org/simple/ --index-strategy=unsafe-best-match --from=jehoctor-rag-demo@latest chat

# Test
test:
    uv run pytest -vv --cov=src --cov-report=term --cov-fail-under=5 tests/

# Format
format:
    uv run ruff format src/ tests/

# Lint
lint:
    uv run ruff check src/ tests/

# Type check
typecheck:
    uv run mypy src/ tests/
