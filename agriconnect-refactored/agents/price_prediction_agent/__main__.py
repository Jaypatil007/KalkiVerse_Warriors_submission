import uvicorn
import click
import logging
import json
from pathlib import Path

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard

# Import the new executor and centralized settings
from .executor import PricePredictionAgentExecutor
from common.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host", default="localhost", help="Host to bind the server to.")
@click.option("--port", default=10001, type=int, help="Port for the server.")
def main(host: str, port: int):
    """Starts the A2A server for the Price Prediction Agent."""
    logger.info(f"Starting Smart Price Prediction Agent Server on http://{host}:{port}")

    card_path = Path(__file__).parent.parent.parent / "agent_cards" / "price_prediction_agent.json"
    if not card_path.exists():
        raise FileNotFoundError(f"Agent card not found at {card_path}")
        
    with card_path.open('r') as f:
        agent_card_data = json.load(f)
    
    # --- CHANGE HERE ---
    # Modify the dictionary before creating the AgentCard object to avoid deprecation warnings.
    agent_card_data["url"] = settings.PRICE_PREDICTION_AGENT_URL
    agent_card = AgentCard(**agent_card_data)
    # --- END CHANGE ---
    
    request_handler = DefaultRequestHandler(
        agent_executor=PricePredictionAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )

    uvicorn.run(server.build(), host=host, port=port)

if __name__ == "__main__":
    main()