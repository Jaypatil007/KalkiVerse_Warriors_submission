# test_client.py

import asyncio
import httpx
import json
import logging
from pathlib import Path

# Import your local settings to get the MCP Server URL
# If running this script outside the container, ensure your local .env is loaded
# or pass the URL directly.
try:
    from agriconnect-refactored.common.settings import settings
    # For Cloud Run, you'll need to manually set the MCP_SERVER_URL if it's not in the environment
    # or if you're running this script locally to test the deployed service.
    MCP_SERVER_URL = settings.MCP_SERVER_URL # This might be 'http://localhost:10000' locally
    print(f"Using MCP Server URL from local settings: {MCP_SERVER_URL}")
except ImportError:
    print("Could not import local settings. Please ensure you are running from the project root or set MCP_SERVER_URL manually.")
    # Fallback or manual URL if settings are not accessible
    # Replace with your actual Cloud Run service URL for the MCP server
    MCP_SERVER_URL = "https://your-cloud-run-service-url.run.app:10000" # <<-- UPDATE THIS URL FOR CLOUD RUN
    print(f"Using fallback/manual MCP Server URL: {MCP_SERVER_URL}")

# --- Configuration ---
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# --- Helper Functions ---

async def call_mcp_find_agent(query: str, server_url: str):
    """
    Connects to the MCP server's SSE endpoint and calls the 'find_agent' tool.
    """
    mcp_sse_url = f"{server_url}/sse"
    
    # If your Cloud Run service is mapped to a domain that doesn't use default port 443
    # you might need to explicitly include the port, e.g., "https://example.com:port/sse"
    # However, Cloud Run usually handles port mapping. If it's HTTP (not recommended for prod),
    # the port might be 80 or the one you specified. Assuming HTTPS default for Cloud Run.
    
    # For Cloud Run, it's typically HTTPS. If your server_url is http://localhost:10000,
    # it won't work for a deployed HTTPS service. Ensure it's the correct public URL.
    
    # Add a placeholder for authentication if your Cloud Run service requires it
    # For an unauthenticated service, this would be empty or omitted.
    # If you've set up IAP or other auth, you'd add headers here.
    # Example for simple HTTP basic auth (not recommended for prod):
    # auth = ("user", "password") 
    # Example for Bearer token:
    # headers = {"Authorization": "Bearer YOUR_TOKEN"}
    
    logger.info(f"Attempting to connect to MCP SSE endpoint: {mcp_sse_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            # For SSE, we need to use stream=True and handle the response iteratively
            async with client.stream("GET", mcp_sse_url, timeout=30.0) as response:
                if response.status_code != 200:
                    logger.error(f"Failed to connect to SSE endpoint. Status code: {response.status_code}")
                    logger.error(f"Response content: {await response.text()}")
                    return {"error": f"SSE connection failed with status {response.status_code}"}
                
                logger.info("SSE connection established. Reading stream...")
                
                # MCP server sends messages in SSE format (data: ...)
                # We need to parse these messages. The first message is likely the initialization.
                # Then we send our tool call.
                
                # Process initial SSE messages if any
                async for chunk in response.aiter_bytes():
                    data = chunk.decode('utf-8')
                    # Basic SSE parsing: lines starting with "data:" contain the actual data
                    for line in data.splitlines():
                        if line.startswith("data:"):
                            message_str = line[len("data:"):].strip()
                            try:
                                message_data = json.loads(message_str)
                                logger.info(f"Received raw SSE data: {message_data}")
                                
                                # Check if it's an initialization confirmation or a tool response
                                if message_data.get("content") and "tool_result" in message_data["content"]:
                                    tool_result = message_data["content"]["tool_result"]
                                    tool_name = tool_result.get("name")
                                    tool_response_content = tool_result.get("content", [])
                                    
                                    if tool_name == "find_agent":
                                        logger.info(f"Received tool result for 'find_agent'.")
                                        if tool_response_content and isinstance(tool_response_content, list) and tool_response_content[0].get("text"):
                                            agent_card_json = tool_response_content[0]["text"]
                                            logger.info(f"Successfully found agent: {agent_card_json}")
                                            return json.loads(agent_card_json)
                                        else:
                                            logger.warning("Tool result for 'find_agent' did not contain expected agent card data.")
                                            return {"error": "No agent card found in tool result."}
                                    else:
                                        logger.warning(f"Received tool result for unexpected tool: {tool_name}")
                                        
                                elif "event" in message_data and message_data["event"] == "ping":
                                    logger.info("Received ping from server, sending tool call...")
                                    # Send the tool call after receiving a ping or initial message
                                    await send_tool_call(client, server_url, query)
                                    # We need to continue listening for the actual response after sending the call.
                                    # This loop structure might need adjustment based on how MCP handles client requests vs SSE streams.
                                    # A common pattern is to send the request via a separate HTTP POST to the MCP's /call_tool endpoint
                                    # and then listen for the SSE stream for the response.
                                    # Let's try sending the call directly.
                                    
                                elif "state" in message_data and message_data["state"] == "connected":
                                    logger.info("MCP server connected successfully. Sending tool call...")
                                    await send_tool_call(client, server_url, query)

                                else:
                                    logger.debug(f"Received non-tool message: {message_data}")
                                    
                            except json.JSONDecodeError:
                                logger.error(f"Failed to decode JSON from SSE data: {message_str}")
                            except Exception as e:
                                logger.exception(f"An error occurred processing SSE data: {message_str}")
                                return {"error": f"Error processing SSE data: {e}"}
                    
                logger.info("SSE stream ended.")
                return {"error": "SSE stream ended without a valid response."}

    except httpx.ConnectError as e:
        logger.error(f"Connection Error: Could not connect to {mcp_sse_url}. Is the MCP server running and accessible? Error: {e}")
        return {"error": f"Connection error: {e}"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Error connecting to {mcp_sse_url}: {e.response.status_code} - {e.response.text}")
        return {"error": f"HTTP error: {e}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred during MCP client operation: {e}")
        return {"error": f"An unexpected error occurred: {e}"}

async def send_tool_call(client: httpx.AsyncClient, server_url: str, query: str):
    """
    Sends a tool call request to the MCP server's /call_tool endpoint.
    This is typically done via HTTP POST, not through the SSE stream itself.
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
        
        logger.info(f"Tool call successful. Response status: {response.status_code}")
        # The response from POST /call_tool is usually the result directly, not part of SSE stream.
        # However, MCP's design might differ. If thesse_client is meant to capture this,
        # the logic might be different. For now, assuming POST returns the tool result.
        
        # The SSE stream handler should pick up this result if it's also sent over SSE.
        # If not, we might need a separate handler for the POST response.
        # Let's refine the SSE stream handler to expect the *result* of the call.
        # The provided code assumes the SSE stream *will* eventually contain the tool result.
        
        return {"status": "sent"}
        
    except httpx.ConnectError as e:
        logger.error(f"Connection Error: Could not connect to {call_tool_url} to send tool call. Error: {e}")
        return {"error": f"Connection error sending tool call: {e}"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Error sending tool call to {call_tool_url}: {e.response.status_code} - {e.response.text}")
        return {"error": f"HTTP error sending tool call: {e}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred sending tool call: {e}")
        return {"error": f"An unexpected error occurred sending tool call: {e}"}


# --- Main Execution ---

async def main():
    # Test case: Ask the orchestrator to find a price prediction agent
    test_query = "I need to know the price for apples in Washington."
    
    # --- IMPORTANT ---
    # If testing your deployed Cloud Run service:
    # 1. Ensure your Cloud Run service is running.
    # 2. Get its public URL (e.g., from `gcloud run services describe ... --format='value(status.url)'`).
    # 3. Set `MCP_SERVER_URL` in this script to point to that service's MCP port.
    #    It will likely be like: "https://your-service-name-xyz.run.app:10000"
    #    Or if Cloud Run maps port 80/443 to your container's 10000, it's just the base URL.
    #    The current setup assumes your Cloud Run service is exposed on port 10000.
    #    If Cloud Run exposes it on a different port (e.g., 80/443), you might not need `:10000`.
    #    For HTTPS Cloud Run: use `https://your-service-name-xyz.run.app`. The `:10000` might be implicit or handled by the gateway.
    #    Let's assume for now your service is listening on port 10000 and you're accessing it via HTTPS.
    
    # If your Cloud Run service exposes port 9000 (Gateway) and 10000 (MCP) directly:
    # You might need to set MCP_SERVER_URL to `https://your-service-name-xyz.run.app:10000`
    # Or if the Gateway is the only entry point: `https://your-service-name-xyz.run.app` (and the gateway routes internally)
    
    # For this test, we are directly calling the MCP server.
    # If you want to test the full flow (Gateway -> MCP -> Agents):
    # You would call your GATEWAY_SERVER_URL instead.
    # Example for Gateway:
    # GATEWAY_URL = "https://your-cloud-run-service-url.run.app" # Or whatever port it's exposed on
    # result = await call_gateway_for_orchestrator(GATEWAY_URL, "I need to know the price for apples in Washington.")
    
    # For now, testing MCP directly:
    print(f"\n--- Testing direct connection to MCP Server: {MCP_SERVER_URL} ---")
    
    # It's crucial that MCP_SERVER_URL is correct and points to your deployed MCP service.
    # If your Cloud Run service runs MCP on port 10000 and is mapped to HTTPS 443,
    # your MCP_SERVER_URL should be `https://your-cloud-run-service.run.app`.
    # If it's exposed on a custom domain with a port, include it.
    
    # You might need to adjust how the client connects to SSE streams over HTTPS,
    # especially if your Cloud Run service is configured to use HTTP or a non-standard port mapping.
    # For typical Cloud Run HTTPS deployments, `https://your-domain.run.app` should work.
    # If the MCP server is actually listening on port 10000 internally, and Cloud Run maps 443 to it,
    # then `https://your-domain.run.app` is the correct base URL.
    
    # If you are sure your Cloud Run service is *only* exposing MCP on port 10000,
    # and you are accessing it via `your-service.run.app:10000` (which is unusual for Cloud Run default deployments)
    # then use `https://your-service.run.app:10000`.
    
    # For this script, let's try assuming a standard Cloud Run setup where the public URL
    # is the entry point for HTTPS. The internal service ports are handled by the container.
    # If your Cloud Run service is named 'agriconnect-server', the URL might be `https://agriconnect-server-xxxx.run.app`.
    
    # If you're testing locally, MCP_SERVER_URL should be http://localhost:10000
    # If you're testing deployed, ensure MCP_SERVER_URL is the correct public URL for MCP.
    
    # !!! IMPORTANT: Replace 'your-cloud-run-service-url.run.app' with your actual Cloud Run service name and domain. !!!
    # Example if running against deployed service:
    # MCP_SERVER_URL_CLOUD_RUN = "https://agriconnect-server-a1b2c3d4e5.uc.r.appspot.com" # Replace with your actual Cloud Run URL
    # result = await call_mcp_find_agent(test_query, MCP_SERVER_URL_CLOUD_RUN)
    
    # For now, sticking to the MCP_SERVER_URL from settings, assuming it's configured correctly for your deployment.
    
    if "localhost" in MCP_SERVER_URL:
        logger.warning("Testing against localhost MCP. Ensure it's running if not testing deployed service.")
        # You might need to adjust the URL format if running locally and MCP is behind Gateway
        # For direct MCP test: http://localhost:10000
        
    result = await call_mcp_find_agent(test_query, MCP_SERVER_URL)
    
    print("\n--- Test Result ---")
    if result and "error" in result:
        print(f"Error: {result['error']}")
    elif result and "name" in result:
        print(f"Successfully found agent:")
        print(json.dumps(result, indent=2))
    else:
        print(f"Unexpected result: {result}")

if __name__ == "__main__":
    # On Windows, the default event loop policy might cause issues with httpx streams.
    # This line helps ensure compatibility.
    if Path(sys.platform.startswith('win')):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
