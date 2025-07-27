# agriconnect-refactored/common/settings.py

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pathlib import Path

# Explicitly find and load the .env file from the project root.
# This approach is robust for both local and containerized execution.
project_root = Path(__file__).resolve().parent.parent
dotenv_path = project_root / '.env'

# --- CHANGE: Add logging configuration for printing during setup ---
# This print statement will be visible when the container starts.
print(f"Searching for .env file at: {dotenv_path.resolve()}")
if dotenv_path.is_file():
    print("Found .env file, loading environment variables.")
    load_dotenv(dotenv_path=dotenv_path)
else:
    print("Warning: .env file not found. Relying on system environment variables.")
# --- END CHANGE ---


class Settings(BaseSettings):
    """
    Centralized configuration settings for the entire application,
    loaded from environment variables.
    """
    model_config = SettingsConfigDict(extra='ignore')
    
    # This will hold the public URL of the Cloud Run service.
    # It's optional so local/docker testing (which doesn't need it) won't break.
    PUBLIC_GATEWAY_URL: str | None = None

    # Google / Gemini Config
    GOOGLE_API_KEY: str
    GOOGLE_GENAI_USE_VERTEXAI: bool = True
    GOOGLE_CLOUD_PROJECT: str
    GOOGLE_CLOUD_LOCATION: str
    GOOGLE_MODEL_NAME: str = "gemini-1.5-flash-latest"
    GOOGLE_EMBEDDING_MODEL: str = "models/embedding-001"

    # Vertex AI Search Datastores
    BUYER_DATASTORE_ID: str
    BUYER_DATASTORE_REGION: str
    PRICE_DATASTORE_ID: str
    PRICE_DATASTORE_REGION: str

    # Agent Network Config
    MCP_SERVER_HOST: str = "localhost"
    MCP_SERVER_PORT: int = 10000
    MCP_SERVER_URL: str

    GATEWAY_SERVER_HOST: str = "localhost"
    GATEWAY_SERVER_PORT: int = 9000
    GATEWAY_SERVER_URL: str

    # Internal Agent URLs (used by MCP for routing)
    PRICE_PREDICTION_AGENT_URL: str
    BUYER_MATCHING_AGENT_URL: str
    TRADE_COORDINATION_AGENT_URL: str
    
    # --- CHANGE: Add LOG_FILE_PATH to settings ---
    LOG_FILE_PATH: str = "app.log" # Keep it consistent with logger_config.py

settings = Settings()

# --- CHANGE: Import and call setup_logging from logger_config ---
# This ensures logging is configured as soon as settings are loaded.
try:
    from .logger_config import setup_logging, LOG_FILE_PATH as SETTINGS_LOG_FILE_PATH
    setup_logging()
    # Update settings.LOG_FILE_PATH with the resolved path from logger_config if needed
    # (though for a simple filename, it's often fine as is).
    # settings.LOG_FILE_PATH = SETTINGS_LOG_FILE_PATH.as_posix() # Example if you need the string path
except ImportError:
    print("Warning: Could not import or setup logging from common.logger_config.")
    # Fallback to basic logging if setup fails
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
# --- END CHANGE ---
