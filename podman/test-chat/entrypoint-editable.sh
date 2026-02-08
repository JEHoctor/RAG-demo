#!/bin/bash
set -euo pipefail

/home/ubuntu/.local/bin/uv run textual run --dev --host=host.containers.internal -c chat "$@" || true

exec /bin/bash
