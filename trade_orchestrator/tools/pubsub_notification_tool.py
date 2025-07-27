# trade_orchestrator/tools/pubsub_notification_tool.py

from typing import Dict, Any, Optional
import os
import json
from datetime import datetime
import logging
from google.adk.tools import FunctionTool

# Import the Pub/Sub client library
from google.cloud import pubsub_v1

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# --- Pub/Sub Client Initialization (Global Singleton) ---
_pubsub_publisher_client: Optional[pubsub_v1.PublisherClient] = None
_project_id: Optional[str] = None

def _initialize_pubsub_client():
    global _pubsub_publisher_client, _project_id
    if _pubsub_publisher_client is None:
        logger.info("Initializing Pub/Sub publisher client (global singleton).")
        _project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not _project_id:
            logger.error("GOOGLE_CLOUD_PROJECT environment variable not set. Pub/Sub client will fail.")
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set.")
        try:
            _pubsub_publisher_client = pubsub_v1.PublisherClient()
            logger.info("Pub/Sub publisher client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub client: {e}")
            raise

# --- Main Pub/Sub Function (This will be wrapped by FunctionTool) ---
def pubsub_notification_function(
    topic_id: str,
    message_data: Dict[str, Any],
    event_type: str = "GENERIC_EVENT"
) -> Dict[str, Any]:
    """
    Publishes a JSON message to a specified Google Cloud Pub/Sub topic.

    Args:
        topic_id (str): The ID of the Pub/Sub topic (e.g., 'trade-notifications').
        message_data (Dict[str, Any]): The content of the message as a dictionary.
                                This will be serialized to JSON.
        event_type (str): A string indicating the type of event (e.g., 'TRADE_CREATED', 'LOGISTICS_UPDATED').
                        Used to categorize the notification.

    Returns:
        Dict[str, Any]: A dictionary representing the result of the publish operation.
    """
    _initialize_pubsub_client() # Ensure client is initialized
    publisher = _pubsub_publisher_client
    project_id = _project_id
    if publisher is None or project_id is None:
        return {"status": "error", "message": "Pub/Sub client not initialized."}

    logger.info(f"Pub/Sub tool execution started: Publishing message to topic '{topic_id}', event_type='{event_type}'")
    logger.debug(f"Message data to publish: {json.dumps(message_data, indent=2)}")

    topic_path = publisher.topic_path(project_id, topic_id)
    
    # Add metadata to the message_data
    message_data_with_metadata = {
        **message_data, # Copy original data
        "event_type": event_type,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        data = json.dumps(message_data_with_metadata).encode("utf-8")
        future = publisher.publish(topic_path, data)
        message_id = future.result() 

        logger.info(f"Message published successfully to topic '{topic_id}' with ID: {message_id}")
        return {
            "status": "success",
            "operation": "PUBLISH_MESSAGE",
            "topic_id": topic_id,
            "message_id": message_id,
            "message_data_sent": message_data_with_metadata,
            "message": f"Message published to Pub/Sub topic '{topic_id}' successfully."
        }
    except Exception as e:
        logger.exception(f"Failed to publish to Pub/Sub topic '{topic_id}'.")
        return {"status": "error", "message": f"Failed to publish to Pub/Sub topic '{topic_id}': {str(e)}"}

# Instantiate the tool for use by agents - now a FunctionTool
pubsub_notification_tool = FunctionTool(func=pubsub_notification_function)
