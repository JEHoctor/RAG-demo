#!/bin/bash
set -euo pipefail

/home/ubuntu/.local/bin/uv run chat "$@" || true

exec /bin/bash
