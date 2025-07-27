import uvicorn


import click
import logging
from mcp_server import server
from common.settings import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host", default=settings.MCP_SERVER_HOST, help="Host to bind the MCP server to.")
@click.option("--port", default=settings.MCP_SERVER_PORT, type=int, help="Port for the MCP server.")
@click.option("--transport", default="sse", help="MCP transport type (e.g., sse, stdio).")
def main(host: str, port: int, transport: str):
  """Starts the dedicated MCP server for the AgriConnect system."""
  # This correctly calls the 'serve' function from the server module
  server.serve(host, port, transport)

if __name__ == "__main__":
  main()