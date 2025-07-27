# mcp_server/server.py

import json
from pathlib import Path
import logging
import google.generativeai as genai
import numpy as np
import pandas as pd

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger

from common.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AGENT_CARDS_DIR = Path(__file__).parent.parent / "agent_cards"

def init_api_key():
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set")
    genai.configure(api_key=settings.GOOGLE_API_KEY)

def generate_embeddings(text: str) -> list:
    try:
        return genai.embed_content(model=settings.GOOGLE_EMBEDDING_MODEL, content=text, task_type="retrieval_document")["embedding"]
    except Exception:
        logger.error(f"Failed to generate embeddings: {text[:100]}...", exc_info=True)
        return []

def load_agent_cards() -> list:
    """
    Loads agent card data and crucially sets the URL to point to the GATEWAY.
    """
    agent_cards_data = []
    if not AGENT_CARDS_DIR.is_dir():
        return []

    # Determine the correct base URL to use.
    # For Cloud Run deployment, use the public URL.
    # For local/docker runs, fall back to the internal gateway URL.
    base_gateway_url = settings.PUBLIC_GATEWAY_URL if settings.PUBLIC_GATEWAY_URL else settings.GATEWAY_SERVER_URL
    logger.info(f"Loading agent cards and pointing them to gateway using base URL: {base_gateway_url}")

    for file_path in AGENT_CARDS_DIR.glob("*.json"):
        with file_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            agent_name = data.get("name")
            
            # Use the determined base URL to construct the final URL
            data["url"] = f"{base_gateway_url}/invoke/?agent_name={agent_name}"
            
            agent_cards_data.append(data)
    return agent_cards_data

def build_agent_card_embeddings() -> pd.DataFrame | None:
    agent_cards = load_agent_cards()
    if not agent_cards: return None
    logger.info("Generating embeddings for agent cards...")
    df = pd.DataFrame({'agent_card': agent_cards})
    df['text_for_embedding'] = df['agent_card'].apply(lambda card: f"Name: {card.get('name')}. Description: {card.get('description')}. Skills: {' '.join([s.get('description', '') for s in card.get('skills', [])])}")
    df['card_embeddings'] = df['text_for_embedding'].apply(generate_embeddings)
    df = df[df['card_embeddings'].str.len() > 0].reset_index(drop=True)
    logger.info("Done generating embeddings.")
    return df

def serve(host, port, transport):
    """Initializes and runs the dedicated AgriConnect MCP server."""
    init_api_key()
    mcp = FastMCP("agriconnect-mcp", host=host, port=port)
    df_agents = build_agent_card_embeddings()

    @mcp.tool(name="find_agent", description="Finds the most relevant agent for a given task.")
    def find_agent(query: str) -> str:
        if df_agents is None or df_agents.empty:
            logger.error("Agent card DataFrame is not available.")
            return json.dumps({"error": "No agents available."})
            
        try:
            query_embedding = genai.embed_content(model=settings.GOOGLE_EMBEDDING_MODEL, content=query, task_type="retrieval_query")["embedding"]
            dot_products = np.dot(np.stack(df_agents['card_embeddings']), query_embedding)
            best_match_index = np.argmax(dot_products)
            best_agent_card = df_agents.iloc[best_match_index]['agent_card']
            logger.info(f"MCP found best match: '{best_agent_card.get('name')}', returning card with gateway URL: {best_agent_card.get('url')}")
            return json.dumps(best_agent_card)
        except Exception as e:
            logger.error(f"Error during agent finding: {e}", exc_info=True)
            return json.dumps({"error": f"Failed to find agent due to an internal error: {e}"})


    logger.info(f"AgriConnect MCP Server running at http://{host}:{port} with transport {transport}")
    mcp.run(transport=transport)