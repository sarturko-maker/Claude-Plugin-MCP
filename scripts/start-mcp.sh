#!/usr/bin/env bash
# Start the negotiation pipeline MCP server.
# Uses absolute paths to avoid environment issues when spawned by Claude Code.

export PYTHONPATH="/home/sarturko/.local/lib/python3.11/site-packages:/home/sarturko/VibeLegalStudio_ClaudeSDK/adeu/src:/usr/local/lib/python3.11/dist-packages:/usr/lib/python3/dist-packages"

cd /home/sarturko/Claude-Plugin || exit 1
exec /usr/bin/python -m src.mcp_server "$@"
