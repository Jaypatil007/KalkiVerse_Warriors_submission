# test_client.py

import asyncio
import httpx
import json
import logging
import sys
from pathlib import Path

# --- Configuration ---
# !!! IMPORTANT: SET YOUR TARGET MCP SERVER URL HERE !!!
# If testing locally, this should be 'http://localhost:10000'
# If testing your deployed Cloud Run service, this should be the HTTPS URL
# e.g., 'https://your-agriconnect-server-xxxx.run.app'
# Ensure it points to your MCP server's public endpoint.
MCP_SERVER_URL = "https://agriconnect-server-537993269198.us-central1.run.app" # <-- UPDATE THIS WITH YOUR TARGET URL

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# --- Helper Functions ---

async def send_tool_call(client: httpx.AsyncClient, server_url: str, query: str):
    """
    Sends a tool call request to the MCP server's /call_tool endpoint.
    """
    call_tool_url = f"{server_url}/call_tool" # MCP's tool call endpoint

    tool_call_payload = {
        "name": "find_agent",
        "arguments": {"query": query}
    }
    
    headers = {
        "Content-Type": "application/json",
        # Add Authorization header if your Cloud Run service is not public or requires it
        # "Authorization": "Bearer YOUR_TOKEN" 
    }
    
    logger.info(f"Sending tool call to {call_tool_url} with payload: {tool_call_payload}")
    
    try:
        response = await client.post(call_tool_url, json=tool_call_payload, headers=headers, timeout=30.0)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        logger.info(f"Tool call sent successfully. Response status: {response.status_code}")
        # The response from POST /call_tool should contain the actual result of the tool execution.
        return response.json() # Return the JSON response from the POST request
        
    except httpx.ConnectError as e:
        logger.error(f"Connection Error: Could not connect to {call_tool_url} to send tool call. Error: {e}")
        return {"error": f"Connection error sending tool call: {e}"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Error sending tool call to {call_tool_url}: {e.response.status_code} - {e.response.text}")
        return {"error": f"HTTP error sending tool call: {e}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred sending tool call: {e}")
        return {"error": f"An unexpected error occurred sending tool call: {e}"}

async def main():
    # Test case: Ask the orchestrator to find a price prediction agent
    test_query = "I need to know the price for apples in Washington."
    
    print(f"\n--- Testing direct connection to MCP Server: {MCP_SERVER_URL} ---")
    
    # Use httpx directly for making the POST call to /call_tool
    async with httpx.AsyncClient() as client:
        result = await send_tool_call(client, MCP_SERVER_URL, test_query)
    
    print("\n--- Test Result ---")
    if result and "error" in result:
        print(f"Error: {result['error']}")
    elif result and "content" in result and result["content"] and isinstance(result["content"], list) and result["content"][0].get("text"):
        try:
            agent_card = json.loads(result["content"][0]["text"])
            print(f"Successfully found agent:")
            print(json.dumps(agent_card, indent=2))
        except json.JSONDecodeError:
            print(f"Received agent data, but it's not valid JSON: {result['content'][0]['text']}")
        except Exception as e:
            print(f"Error processing agent data: {e}")
    elif result and "content" in result:
        print(f"Received tool result, but unexpected format: {result['content']}")
    else:
        print(f"Unexpected result structure: {result}")

if __name__ == "__main__":
    # On Windows, the default event loop policy might cause issues with httpx streams.
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())