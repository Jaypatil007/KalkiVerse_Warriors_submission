# agriconnect-refactored/gateway_server/server.py

import httpx
from fastapi import FastAPI, Request, Response
from common.settings import settings # Import settings object
import logging
from pathlib import Path # Import Path

# This is our main public-facing application
app = FastAPI(title="AgriConnect Gateway")

# The root logger is already configured by common.settings.py
logger = logging.getLogger(__name__)

# The map of agent names to their INTERNAL URLs
AGENT_URL_MAP = {
    "smart_price_prediction_agent_v2": settings.PRICE_PREDICTION_AGENT_URL,
    "smart_buyer_matching_agent": settings.BUYER_MATCHING_AGENT_URL,
    "trade_coordination_agent": settings.TRADE_COORDINATION_AGENT_URL,
}

# --- CHANGE: Access LOG_FILE_PATH from the settings instance ---
@app.get("/logs")
async def get_logs(request: Request):
    """
    Serves the application log file.
    """
    # Access LOG_FILE_PATH from the already initialized settings object
    log_file_path_str = settings.LOG_FILE_PATH 
    log_file_path = Path(log_file_path_str) # Use the path from settings

    if not log_file_path.is_file():
        logger.warning(f"Log file not found at: {log_file_path.resolve()}")
        return Response(content="Log file not found.", status_code=404)

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            log_content = f.read()
        
        # Return the log file content
        return Response(
            content=log_content,
            status_code=200,
            media_type="text/plain", # Serve as plain text
            headers={"X-Log-File-Name": log_file_path.name} # Optional header with filename
        )
    except Exception as e:
        logger.error(f"Error reading log file {log_file_path.resolve()}: ", exc_info=True)
        return Response(content="Error reading log file.", status_code=500)
# --- END CHANGE ---


@app.post("/invoke/")
async def proxy_agent_call(agent_name: str, request: Request):
    """
    Receives an A2A call and forwards it to the correct internal agent.
    """
    target_url = AGENT_URL_MAP.get(agent_name)
    if not target_url:
        logger.error(f"Gateway received call for unknown agent: {agent_name}")
        return Response(content=f"Agent '{agent_name}' not found.", status_code=404)

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            body = await request.body()
            # Filter headers to only include relevant ones like Content-Type and Accept
            headers = {h: v for h, v in request.headers.items() if h.lower() in ['content-type', 'accept', 'authorization']} # Added authorization as it might be needed.
            
            # Construct the full target URL by appending path and query from the original request
            # The original request's path is usually empty for /invoke, but query params are important.
            full_target_url = f"{target_url}?{request.url.query}"
            
            logger.info(f"Gateway proxying request for agent '{agent_name}' to internal URL: {full_target_url}")

            response = await client.post(full_target_url, content=body, headers=headers)
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except httpx.ConnectError:
            logger.error(f"Gateway failed to connect to internal agent '{agent_name}' at {target_url}")
            return Response(content=f"Service unavailable: Could not connect to {agent_name}.", status_code=503)
        except Exception as e:
            logger.error(f"Gateway encountered an unexpected error proxying to '{agent_name}': ", exc_info=True)
            return Response(content="Internal server error in gateway.", status_code=500)

@app.get("/")
def read_root():
    return {"message": "AgriConnect Gateway is running."}