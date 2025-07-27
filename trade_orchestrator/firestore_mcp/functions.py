# trade_orchestrator/firestore_mcp/functions.py

from typing import Dict, Any, List, Optional
import os
import json
from datetime import datetime, timedelta
import logging
import random

from google.cloud import firestore
from google.cloud.firestore_v1.transforms import Sentinel
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# --- Firestore Client Initialization (Global Singleton) ---
_firestore_db_client: Optional[firestore.Client] = None

def _initialize_firestore_client():
    global _firestore_db_client
    if _firestore_db_client is None:
        logger.info("Initializing Firestore client (global singleton).")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            logger.error("GOOGLE_CLOUD_PROJECT environment variable not set. Firestore client will fail.")
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set. Please set it to your GCP project ID.")
        try:
            _firestore_db_client = firestore.Client(project=project_id)
            logger.info("Firestore client initialized successfully for project: %s", project_id)
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}", exc_info=True)
            raise

def _get_db_client() -> firestore.Client:
    _initialize_firestore_client()
    if _firestore_db_client is None:
        logger.critical("Firestore client is uninitialized after _initialize_firestore_client call.")
        raise RuntimeError("Firestore client failed to initialize.")
    return _firestore_db_client

# --- Pub/Sub Client Initialization (Global Singleton) ---
_pubsub_publisher_client: Optional[pubsub_v1.PublisherClient] = None
_pubsub_project_id: Optional[str] = None

def _initialize_pubsub_client():
    global _pubsub_publisher_client, _pubsub_project_id
    if _pubsub_publisher_client is None:
        logger.info("Initializing Pub/Sub publisher client (global singleton).")
        _pubsub_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not _pubsub_project_id:
            logger.error("GOOGLE_CLOUD_PROJECT environment variable not set. Pub/Sub client will fail.")
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set.")
        try:
            _pubsub_publisher_client = pubsub_v1.PublisherClient()
            logger.info("Pub/Sub publisher client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub client: {e}", exc_info=True)
            raise

# --- Serialization Helper ---
def _to_json_serializable(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Sentinel):
        return "server_timestamp_placeholder"
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_serializable(elem) for elem in obj]
    return obj


# --- Individual Tool Functions ---

# Firestore Tools
def create_trade(trade_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Attempting to create trade.")
    db = _get_db_client()
    collection_ref = db.collection('trades')

    if not trade_data:
        raise ValueError("trade_data is required for CREATE_TRADE.")

    data_to_store_in_firestore = {**trade_data}
    data_to_store_in_firestore["created_at"] = firestore.SERVER_TIMESTAMP
    data_to_store_in_firestore["last_updated_at"] = firestore.SERVER_TIMESTAMP
    data_to_store_in_firestore["logistics_status"] = trade_data.get("logistics_status", "PENDING_SETUP")
    data_to_store_in_firestore["payment_status"] = trade_data.get("payment_status", "PENDING_SETUP")

    try:
        update_time, doc_ref = collection_ref.add(data_to_store_in_firestore)
        new_trade_id = doc_ref.id
        
        full_log_data = {"status": "success", "operation": "CREATE_TRADE", "trade_id": new_trade_id, 
                         "message": f"Trade {new_trade_id} created in Firestore (full log).",
                         "data_stored": _to_json_serializable(data_to_store_in_firestore)}
        logger.info(f"Trade created successfully in Firestore. Logged full data: {json.dumps(full_log_data, indent=2)}")

        return {
            "status": "success",
            "trade_id": new_trade_id,
            "message": "Trade created successfully."
        }
    except Exception as e:
        logger.exception(f"Failed to create trade with data {trade_data}.")
        raise RuntimeError(f"Failed to create trade: {e}")

def update_trade(trade_id: str, trade_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Attempting to update trade with ID: {trade_id}")
    db = _get_db_client()
    collection_ref = db.collection('trades')

    if not trade_id:
        raise ValueError("trade_id is required for UPDATE_TRADE.")
    if not trade_data:
        raise ValueError("trade_data is required for UPDATE_TRADE.")

    data_to_update_in_firestore = {**trade_data}
    data_to_update_in_firestore["last_updated_at"] = firestore.SERVER_TIMESTAMP
    
    try:
        doc_ref = collection_ref.document(trade_id)
        doc_ref.update(data_to_update_in_firestore)
        
        full_log_data = {"status": "success", "operation": "UPDATE_TRADE", "trade_id": trade_id, 
                         "message": f"Trade {trade_id} updated in Firestore (full log).",
                         "data_updated": _to_json_serializable(data_to_update_in_firestore)}
        logger.info(f"Trade {trade_id} updated successfully in Firestore. Logged full data: {json.dumps(full_log_data, indent=2)}")

        return {
            "status": "success",
            "trade_id": trade_id,
            "message": "Trade updated successfully."
        }
    except Exception as e:
        logger.exception(f"Failed to update trade {trade_id} with data {trade_data}.")
        raise RuntimeError(f"Failed to update trade {trade_id}: {e}")


def get_trade_by_id(trade_id: str) -> Dict[str, Any]:
    logger.info(f"Attempting to get trade by ID: {trade_id}")
    db = _get_db_client()
    collection_ref = db.collection('trades')

    if not trade_id:
        raise ValueError("trade_id is required for GET_TRADE_BY_ID.")

    try:
        doc_ref = collection_ref.document(trade_id)
        doc = doc_ref.get()
        if doc.exists:
            trade_data = doc.to_dict()
            logger.info(f"Trade {trade_id} fetched successfully.")
            return {
                "status": "success",
                "operation": "GET_TRADE_BY_ID",
                "trade_id": trade_id,
                "data": _to_json_serializable(trade_data),
                "message": f"Trade {trade_id} retrieved successfully."
            }
        else:
            logger.warning(f"Trade {trade_id} not found in Firestore.")
            return {
                "status": "not_found",
                "operation": "GET_TRADE_BY_ID",
                "trade_id": trade_id,
                "message": f"Trade {trade_id} not found."
            }
    except Exception as e:
        logger.exception(f"Failed to retrieve trade {trade_id}.")
        raise RuntimeError(f"Failed to retrieve trade {trade_id}: {e}")


def query_trades(query_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    logger.info(f"Attempting to query trades with filters: {query_filters}")
    db = _get_db_client()
    collection_ref = db.collection('trades')

    query = collection_ref
    if query_filters:
        for field, value in query_filters.items():
            if field in ["farmer_id", "payment_status", "logistics_status"]:
                query = query.where(field, '==', value)
            else:
                logger.warning(f"Unsupported query filter field: {field}")

    results = []
    try:
        docs = query.stream()
        for doc in docs:
            trade_info = doc.to_dict()
            trade_info["trade_id"] = doc.id
            results.append(trade_info)

        logger.info(f"Query returned {len(results)} trades.")
        return {
            "status": "success",
            "operation": "QUERY_TRADES",
            "data": _to_json_serializable(results),
            "message": f"Found {len(results)} trades matching query."
        }
    except Exception as e:
        logger.exception(f"Failed to query trades with filters {query_filters}.")
        raise RuntimeError(f"Failed to query trades: {e}")


# Pub/Sub Tool
def pubsub_notification_function(
    topic_id: str,
    message_data: Dict[str, Any],
    event_type: str = "GENERIC_EVENT"
) -> Dict[str, Any]:
    """
    Publishes a JSON message to a specified Google Cloud Pub/Sub topic. Logs full data, returns minimal.
    """
    _initialize_pubsub_client()
    publisher = _pubsub_publisher_client
    project_id = _pubsub_project_id
    if publisher is None or project_id is None:
        return {"status": "error", "message": "Pub/Sub client not initialized."}

    logger.info(f"Pub/Sub tool execution started: Publishing message to topic '{topic_id}', event_type='{event_type}'")

    # --- FIX: Define topic_path before try block ---
    topic_path = publisher.topic_path(project_id, topic_id)
    # --- END FIX ---

    message_data_with_metadata = {
        **message_data,
        "event_type": event_type,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        data = json.dumps(message_data_with_metadata).encode("utf-8")
        future = publisher.publish(topic_path, data)
        message_id = future.result() 

        full_log_data = {"status": "success", "operation": "PUBLISH_MESSAGE", "topic_id": topic_id, 
                         "message_id": message_id, "message_data_sent": message_data_with_metadata,
                         "message": f"Message published to Pub/Sub topic '{topic_id}' successfully (full log)."}
        logger.info(f"Pub/Sub message published. Logged full data: {json.dumps(full_log_data, indent=2)}")

        return {
            "status": "success",
            "message_id": message_id,
            "topic_id": topic_id,
            "message": f"Message published successfully."
        }
    except Exception as e:
        logger.exception(f"Failed to publish to Pub/Sub topic '{topic_id}'.")
        raise RuntimeError(f"Failed to publish to Pub/Sub topic '{topic_id}': {str(e)}")


# Datetime Parser Tool
def simulated_datetime_parser_function(natural_language_datetime: str) -> Dict[str, Any]:
    logger.info(f"Simulated datetime parser called for: '{natural_language_datetime}'")
    
    now = datetime.now()
    parsed_datetime_obj = None

    lower_nl = natural_language_datetime.lower()
    if "tomorrow" in lower_nl:
        parsed_datetime_obj = now + timedelta(days=1)
    elif "next week" in lower_nl:
        parsed_datetime_obj = now + timedelta(weeks=1)
    elif "today" in lower_nl:
        parsed_datetime_obj = now
    else:
        parsed_datetime_obj = now # Default
        
    if parsed_datetime_obj:
        if "morning" in lower_nl:
            parsed_datetime_obj = parsed_datetime_obj.replace(hour=9, minute=0, second=0, microsecond=0)
        elif "afternoon" in lower_nl:
            parsed_datetime_obj = parsed_datetime_obj.replace(hour=14, minute=0, second=0, microsecond=0)
        elif "evening" in lower_nl:
            parsed_datetime_obj = parsed_datetime_obj.replace(hour=19, minute=0, second=0, microsecond=0)
        elif "midnight" in lower_nl:
            parsed_datetime_obj = parsed_datetime_obj.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            if parsed_datetime_obj.date() > now.date():
                parsed_datetime_obj = parsed_datetime_obj.replace(hour=9, minute=0, second=0, microsecond=0)
            else:
                parsed_datetime_obj = now

    if parsed_datetime_obj:
        iso_datetime = parsed_datetime_obj.isoformat()
        logger.info(f"Parsed '{natural_language_datetime}' to '{iso_datetime}' (simulated).")
        return {
            "status": "success",
            "original_input": natural_language_datetime,
            "parsed_iso_datetime": iso_datetime,
            "message": "Simulated datetime parsing successful."
        }
    else:
        logger.warning(f"Simulated datetime parser failed for: '{natural_language_datetime}'")
        return {
            "status": "error",
            "original_input": natural_language_datetime,
            "parsed_iso_datetime": None,
            "message": "Failed to parse datetime from natural language."
        }

# Tool to format the final alert notification output
def format_final_alert_output(
    workflow_status: str,
    trade_id: str,
    final_trade_data: Dict[str, Any],
    pubsub_notification_result: Dict[str, Any],
    summary: str
) -> Dict[str, Any]:
    logger.info(f"Consolidating final alert output for trade_id: {trade_id}")
    final_output = {
        "workflow_status": workflow_status,
        "trade_id": trade_id,
        "final_trade_data": _to_json_serializable(final_trade_data),
        "pubsub_notification_result": _to_json_serializable(pubsub_notification_result),
        "summary": summary
    }
    logger.debug(f"Final alert output constructed: {json.dumps(final_output, indent=2)}")
    return final_output
