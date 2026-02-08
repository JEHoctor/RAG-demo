#!/bin/bash
set -euo pipefail

/home/ubuntu/.local/bin/uv run textual run --dev --host="$TEXTUAL_CONSOLE_HOST" -c chat "$@" || true

exec /bin/bash
