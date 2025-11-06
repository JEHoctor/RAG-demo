# List available commands
default:
    @just --list

# Build the package
build:
    uv build

# Upload package to PyPI
publish: build
    uv publish

# Upload package to TestPyPI
publish-test: build
    uv publish --index testpypi

# Run the chat command from the worktree
chat:
    uv run chat

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