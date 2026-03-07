"""Entry point for running the MCP server as a module.

Usage:
    python -m src.mcp_server          # stdio transport
    python -m src.mcp_server --sse    # HTTP SSE transport
"""

import argparse
import logging
import sys

from src.mcp_server import mcp


def main() -> None:
    """Run the negotiation MCP server with stdio or SSE transport."""
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, force=True)

    parser = argparse.ArgumentParser(
        description="Negotiation Pipeline MCP Server"
    )
    parser.add_argument(
        "--sse", action="store_true", help="Run with SSE transport (HTTP)"
    )
    parser.add_argument(
        "--port", type=int, default=8002, help="Port for SSE server"
    )
    args = parser.parse_args()

    if args.sse:
        _run_sse(args.port)
    else:
        mcp.run()


def _run_sse(port: int) -> None:
    """Run the server with SSE transport for HTTP access."""
    import uvicorn
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route

    sse_transport = SseServerTransport("/messages")

    async def handle_sse(request):  # type: ignore[no-untyped-def]
        """Handle an incoming SSE connection by running the MCP server session."""
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp._mcp_server.run(
                streams[0],
                streams[1],
                mcp._mcp_server.create_initialization_options(),
            )

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route(
                "/messages",
                endpoint=sse_transport.handle_post_message,
                methods=["POST"],
            ),
        ]
    )
    logging.getLogger(__name__).info(
        "Starting MCP server with SSE on port %d", port
    )
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
