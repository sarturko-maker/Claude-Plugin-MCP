#!/usr/bin/env bash
# Start the negotiation pipeline MCP server.
# Auto-detects paths relative to its own location.

set -euo pipefail

# Resolve directories relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check Python version (require 3.11+)
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.11 or later." >&2
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    echo "ERROR: Python 3.11+ required, found Python $PY_VERSION" >&2
    exit 1
fi

export PYTHONPATH="$REPO_ROOT"
cd "$REPO_ROOT"
exec python3 -m src.mcp_server "$@"
