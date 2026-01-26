#!/bin/bash
set -euo pipefail

/home/user/.local/bin/uvx --torch-backend=auto --from=jehoctor-rag-demo@latest chat || true

exec /bin/bash
