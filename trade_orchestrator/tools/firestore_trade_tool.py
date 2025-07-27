# GenAIProject/trade_orchestrator/tools/firestore_trade_tool.py

# Removed BaseTool import as we're not inheriting from it directly
from typing import Dict, Any, List, Optional
import os
import json
from datetime import datetime
import logging
from google.adk.tools import FunctionTool # Import FunctionTool

# Import the Firestore client library
from google.cloud import firestore
from google.cloud.firestore_v1.transforms import Sentinel # Import Sentinel for type check

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
# Optionally add a StreamHandler if you want to see logs immediately in local testing
# This is usually not needed in Cloud Run as logs are captured automatically.
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
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set.")
        try:
            _firestore_db_client = firestore.Client(project=project_id)
            logger.info("Firestore client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise

def _to_json_serializable(obj: Any) -> Any:
    """
    Recursively converts non-JSON-serializable Firestore specific objects
    (like Sentinels or datetime objects) into JSON-serializable formats.
    This is now a standalone function.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Sentinel):
        logger.debug(f"Converting Firestore Sentinel object to None for JSON serialization.")
        return None 
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()} # Recursive call
    if isinstance(obj, list):
        return [_to_json_serializable(elem) for elem in obj]       # Recursive call
    return obj

# --- Main Firestore Function (This will be wrapped by FunctionTool) ---
def firestore_trade_function(
    operation: str,
    trade_data: Optional[Dict[str, Any]] = None,
    trade_id: Optional[str] = None,
    farmer_id: Optional[str] = None,
    query_filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Manages agricultural trade data in Google Cloud Firestore.
    Supports creating, retrieving, updating, and querying trade records.
    Requires a 'trades' collection in Firestore.

    Args:
        operation (str): The type of database operation ("CREATE_TRADE", "UPDATE_TRADE",
                         "GET_TRADE_BY_ID", "QUERY_TRADES").
        trade_data (Optional[Dict[str, Any]]): Data for creating or updating a trade.
        trade_id (Optional[str]): The ID of the trade for update or retrieval.
        farmer_id (Optional[str]): The ID of the farmer, used for queries or context.
        query_filters (Optional[Dict[str, Any]]): Filters for querying trades.

    Returns:
        Dict[str, Any]: A dictionary representing the result of the database operation.
    """
    _initialize_firestore_client() # Ensure client is initialized
    db = _firestore_db_client
    if db is None:
        return _to_json_serializable({"status": "error", "message": "Firestore client not initialized."})

    logger.info(f"FirestoreTool execution started: operation='{operation}'")

    # LOGGING INPUTS: Ensure all logged data is JSON serializable
    serializable_trade_data_for_log = _to_json_serializable(trade_data) if trade_data else None
    serializable_query_filters_for_log = _to_json_serializable(query_filters) if query_filters else None
    logger.debug(f"Input params - trade_id: {trade_id}, farmer_id: {farmer_id}, query_filters: {serializable_query_filters_for_log}, trade_data: {json.dumps(serializable_trade_data_for_log, indent=2) if serializable_trade_data_for_log else 'None'}")
    
    collection_ref = db.collection('trades')

    try:
        if operation == "CREATE_TRADE":
            if not trade_data:
                logger.warning("CREATE_TRADE called without trade_data.")
                return _to_json_serializable({"status": "error", "message": "trade_data is required for CREATE_TRADE."})
            
            # Prepare data to be sent to Firestore (this data will contain Sentinel)
            data_to_store_in_firestore = {**trade_data} # Create a shallow copy
            data_to_store_in_firestore["created_at"] = firestore.SERVER_TIMESTAMP
            data_to_store_in_firestore["last_updated_at"] = firestore.SERVER_TIMESTAMP
            data_to_store_in_firestore["logistics_status"] = trade_data.get("logistics_status", "PENDING_SETUP")
            data_to_store_in_firestore["payment_status"] = trade_data.get("payment_status", "PENDING_SETUP")

            # Log the data *after* it has been made serializable for display
            logger.info(f"Attempting to create trade with data (serializable for log): {json.dumps(_to_json_serializable(data_to_store_in_firestore), indent=2)}")

            doc_ref = collection_ref.add(data_to_store_in_firestore) 
            new_trade_id = doc_ref[1].id
            
            # Construct the return data, excluding Sentinels
            return_data_for_response = {**trade_data, "trade_id": new_trade_id}
            # The actual created_at/last_updated_at from Firestore will be datetimes if we fetch the doc.
            # Here, we omit them from the 'created_data' in the *response* because they were Sentinels in the *input*.
            # The client usually doesn't need to see the Sentinel constant in the response of a successful creation.
            
            logger.info(f"Trade created successfully in Firestore. Trade ID: {new_trade_id}")
            return _to_json_serializable({
                "status": "success",
                "operation": "CREATE_TRADE",
                "trade_id": new_trade_id,
                "message": f"Trade {new_trade_id} created in Firestore.",
                "created_data": return_data_for_response # This data should already be serializable from initial input
            })

        elif operation == "UPDATE_TRADE":
            if not trade_id:
                logger.warning("UPDATE_TRADE called without trade_id.")
                return _to_json_serializable({"status": "error", "message": "trade_id is required for UPDATE_TRADE."})
            if not trade_data:
                logger.warning(f"UPDATE_TRADE called for trade_id {trade_id} without trade_data.")
                return _to_json_serializable({"status": "error", "message": "trade_data is required for UPDATE_TRADE."})
            
            # Prepare data to be sent for update
            data_to_update_in_firestore = {**trade_data} # Create a shallow copy
            data_to_update_in_firestore["last_updated_at"] = firestore.SERVER_TIMESTAMP

            # Log the data after making it serializable
            logger.info(f"Attempting to update trade {trade_id} with data (serializable for log): {json.dumps(_to_json_serializable(data_to_update_in_firestore), indent=2)}")
            
            doc_ref = collection_ref.document(trade_id)
            doc_ref.update(data_to_update_in_firestore)
            
            # Construct the return data, excluding Sentinels
            return_data_for_response = {**trade_data}
            
            logger.info(f"Trade {trade_id} updated successfully in Firestore.")
            return _to_json_serializable({
                "status": "success",
                "operation": "UPDATE_TRADE",
                "trade_id": trade_id,
                "message": f"Trade {trade_id} updated in Firestore.",
                "updated_data": return_data_for_response
            })

        elif operation == "GET_TRADE_BY_ID":
            # ... (no changes needed here as retrieved data are already datetimes, not Sentinels) ...
            if not trade_id:
                logger.warning("GET_TRADE_BY_ID called without trade_id.")
                return _to_json_serializable({"status": "error", "message": "trade_id is required for GET_TRADE_BY_ID."})
            
            logger.info(f"Attempting to fetch trade by ID: {trade_id}")
            doc_ref = collection_ref.document(trade_id)
            doc = doc_ref.get()
            if doc.exists:
                trade_data_from_db = doc.to_dict() # This will contain actual datetime objects, not Sentinels
                logger.info(f"Trade {trade_id} fetched successfully. Data: {json.dumps(_to_json_serializable(trade_data_from_db), indent=2)}")
                return _to_json_serializable({
                    "status": "success",
                    "operation": "GET_TRADE_BY_ID",
                    "trade_id": trade_id,
                    "data": trade_data_from_db, 
                    "message": f"Trade {trade_id} retrieved successfully."
                })
            else:
                logger.info(f"Trade {trade_id} not found in Firestore.")
                return _to_json_serializable({"status": "error", "message": f"Trade {trade_id} not found."})

        elif operation == "QUERY_TRADES":
            # ... (no changes needed here as retrieved data are already datetimes, not Sentinels) ...
            logger.info(f"Attempting to query trades with filters: {serializable_query_filters_for_log}")
            query = collection_ref
            
            if query_filters:
                for field, value in query_filters.items():
                    if field == "farmer_id":
                        query = query.where('farmer_id', '==', value)
                    elif field == "payment_status":
                        query = query.where('payment_status', '==', value)
                    elif field == "logistics_status":
                        query = query.where('logistics_status', '==', value)
            
            results = []
            docs = query.stream() 
            for doc in docs:
                trade_info = doc.to_dict()
                trade_info["trade_id"] = doc.id
                results.append(trade_info)

            logger.info(f"Query returned {len(results)} trades. Results: {json.dumps(_to_json_serializable(results), indent=2)}")
            return _to_json_serializable({
                "status": "success",
                "operation": "QUERY_TRADES",
                "data": results,
                "message": f"Found {len(results)} trades matching query."
            })
        
        else:
            logger.error(f"Unknown database operation: {operation}")
            return _to_json_serializable({"status": "error", "message": f"Unknown database operation: {operation}"})

    except Exception as e:
        logger.exception(f"Firestore operation '{operation}' failed with an exception.")
        return _to_json_serializable({"status": "error", "message": f"Firestore operation failed: {str(e)}"})

# Instantiate the tool for use by agents
firestore_trade_tool = FunctionTool(func=firestore_trade_function)