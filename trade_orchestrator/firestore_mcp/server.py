# trade_orchestrator/firestore_mcp/server.py

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

current_dir = Path(__file__).parent.resolve()
project_root = current_dir.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

from mcp import types as mcp_types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Import all tool functions from the consolidated functions.py
from trade_orchestrator.firestore_mcp.functions import (
    create_trade,
    update_trade,
    get_trade_by_id,
    query_trades,
    pubsub_notification_function,
    simulated_datetime_parser_function,
    format_final_alert_output, # NEW
    _initialize_firestore_client,
    _initialize_pubsub_client
)

load_dotenv(os.path.join(project_root, '.env'))

# --- Logging Setup ---
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "mcp_firestore_server.log")

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, mode="w"),
        logging.StreamHandler()
    ],
)
# --- End Logging Setup ---

# Initialize clients once when the server starts
try:
    _initialize_firestore_client()
    _initialize_pubsub_client()
    logging.info("Firestore and Pub/Sub clients verified for use by MCP server.")
except Exception as e:
    logging.critical(f"Failed to initialize one or more clients on startup: {e}. Exiting server.", exc_info=True)
    # sys.exit(1)


# --- Wrap ALL functions as ADK FunctionTools ---
ADK_FIRESTORE_TOOLS = {
    "create_trade": FunctionTool(func=create_trade),
    "update_trade": FunctionTool(func=update_trade),
    "get_trade_by_id": FunctionTool(func=get_trade_by_id),
    "query_trades": FunctionTool(func=query_trades),
    "pubsub_notification_function": FunctionTool(func=pubsub_notification_function),
    "simulated_datetime_parser_function": FunctionTool(func=simulated_datetime_parser_function),
    "format_final_alert_output": FunctionTool(func=format_final_alert_output), # NEW
}
logging.info(f"Defined {len(ADK_FIRESTORE_TOOLS)} total tools.")


# --- MCP Server Setup ---
logging.info("Creating MCP Server instance for Firestore Trades...")
app = Server("firestore-trade-mcp-server")


@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """MCP handler to list tools this server exposes."""
    logging.info("MCP Server: Received list_tools request.")
    mcp_tools_list = []
    for tool_name, adk_tool_instance in ADK_FIRESTORE_TOOLS.items():
        if not adk_tool_instance.name:
            adk_tool_instance.name = tool_name

        mcp_tool_schema = adk_to_mcp_tool_type(adk_tool_instance)
        logging.info(
            f"MCP Server: Advertising tool: {mcp_tool_schema.name}, "
            f"InputSchema: {json.dumps(mcp_tool_schema.inputSchema, indent=2) if mcp_tool_schema.inputSchema else 'None'}"
        )
        mcp_tools_list.append(mcp_tool_schema)
    return mcp_tools_list


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    """MCP handler to execute a tool call requested by an MCP client."""
    logging.info(
        f"MCP Server: Received call_tool request for '{name}' with args: {arguments}"
    )

    if name in ADK_FIRESTORE_TOOLS:
        adk_tool_instance = ADK_FIRESTORE_TOOLS[name]
        try:
            adk_tool_response = await adk_tool_instance.run_async(
                args=arguments,
                tool_context=None,  # type: ignore
            )
            logging.info(
                f"MCP Server: ADK tool '{name}' executed successfully. "
                f"Raw Response: {adk_tool_response}"
            )
            response_text = json.dumps(adk_tool_response, indent=2)
            return [mcp_types.TextContent(type="text", text=response_text)]

        except Exception as e:
            logging.error(
                f"MCP Server: Error executing ADK tool '{name}': {e}", exc_info=True
            )
            error_payload = {
                "status": "error",
                "message": f"Failed to execute tool '{name}': {str(e)}",
                "tool_name": name,
                "arguments": arguments,
            }
            error_text = json.dumps(error_payload)
            return [mcp_types.TextContent(type="text", text=error_text)]
    else:
        logging.warning(
            f"MCP Server: Tool '{name}' not found/exposed by this server."
        )
        error_payload = {
            "status": "error",
            "message": f"Tool '{name}' not implemented by this server.",
            "requested_tool": name,
        }
        error_text = json.dumps(error_payload)
        return [mcp_types.TextContent(type="text", text=error_text)]


# --- MCP Server Runner ---
async def run_mcp_stdio_server():
    """Runs the MCP server, listening for connections over standard input/output."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logging.info("MCP Stdio Server: Starting handshake with client...")
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
        logging.info("MCP Stdio Server: Run loop finished or client disconnected.")


if __name__ == "__main__":
    logging.info("Launching Firestore Trade MCP Server via stdio...")
    try:
        asyncio.run(run_mcp_stdio_server())
    except KeyboardInterrupt:
        logging.info("\nMCP Server (stdio) stopped by user.")
    except Exception as e:
        logging.critical(
            f"MCP Server (stdio) encountered an unhandled error: {e}", exc_info=True
        )
    finally:
        logging.info("MCP Server (stdio) process exiting.")