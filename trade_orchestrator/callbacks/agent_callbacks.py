# trade_orchestrator/callbacks/agent_callbacks.py

import os
import json
import logging
from typing import Optional, Any
from datetime import datetime

from google.adk.agents.callback_context import CallbackContext
from google.genai import types # For Content objects (used for type hinting, accessing parts)

# --- Callback Logging Setup ---
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
os.makedirs(LOG_DIR, exist_ok=True)

CALLBACK_LOG_FILE = os.path.join(LOG_DIR, "agent_callback_activity.log")

callback_logger = logging.getLogger("agent_callbacks_logger")
callback_logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

if not callback_logger.handlers:
    file_handler = logging.FileHandler(CALLBACK_LOG_FILE, mode="a")
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    callback_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(file_formatter)
    callback_logger.addHandler(stream_handler)

callback_logger.info("Agent Callbacks logging initialized to file: %s", CALLBACK_LOG_FILE)
# --- End Callback Logging Setup ---

# Helper function to safely serialize objects to JSON for logging
def _safe_json_dump(obj: Any) -> str:
    """Safely converts an object (potentially Pydantic model) to JSON string."""
    try:
        # Prioritize ADK's internal serialization for Pydantic models
        if hasattr(obj, 'model_dump'): # For Pydantic v2 models
            return json.dumps(obj.model_dump(), indent=2, default=str)
        if hasattr(obj, 'dict'): # For Pydantic v1 models
             return json.dumps(obj.dict(), indent=2, default=str)
        if hasattr(obj, 'to_dict'): # For ADK objects that might have this (e.g. content)
            return json.dumps(obj.to_dict(), indent=2, default=str)
        if isinstance(obj, (datetime, types.ImmutableList)): # Handle specific non-dict types
            return str(obj) # Convert datetimes or other complex types to string representation
        
        # Fallback for general JSON serializable types
        return json.dumps(obj, indent=2, default=str)
    except (TypeError, ValueError, AttributeError) as e:
        callback_logger.warning(f"Could not fully JSON dump object of type {type(obj)}: {e}")
        # Return string representation if cannot serialize
        return str(obj)

# --- Callback Functions ---

def before_logistics_agent_callback(
    callback_context: CallbackContext # Only argument provided to agent callbacks
) -> Optional[types.Content]:
    """
    Callback function executed just before the LogisticsDetailsAgent starts.
    Logs the incoming message/state.
    """
    agent_name = callback_context.agent_name
    
    # Access session_id from the session object within context if available, or invocation_id as fallback
    session_id = getattr(getattr(callback_context, 'session', None), 'id', None)
    if not session_id: # If session.id not found, try invocation_id hint
        session_id = getattr(callback_context, 'invocation_id', 'N/A_id')
    
    callback_logger.info(f"[{agent_name} - Before Agent Callback] Session/Invocation ID: {session_id}")
    
    # Attempt to retrieve the triggering message (if passed directly)
    # This might be None or an empty content object in sequential flows.
    incoming_message = getattr(callback_context, 'new_message', None)
    if incoming_message:
        callback_logger.debug(f"[{agent_name} - Before Agent Callback] Direct new_message argument:")
        callback_logger.debug(_safe_json_dump(incoming_message))
    else:
        callback_logger.debug(f"[{agent_name} - Before Agent Callback] No direct new_message argument (expected for sub-agents).")


    # For sub-agents in a SequentialAgent, the actual input is from previous agent's output in state.
    current_state_object = getattr(callback_context, 'state', None)
    if current_state_object:
        callback_logger.info(f"[{agent_name} - Before Agent Callback] Current shared state (callback_context.state):")
        # Log the entire state for debugging, or specific keys like trade_initiation_result
        callback_logger.debug(_safe_json_dump(current_state_object))
        
        # Log specific input for this agent from the state
        if hasattr(current_state_object, 'trade_initiation_result'):
            input_for_logistics_agent = current_state_object.trade_initiation_result
            callback_logger.info(f"[{agent_name} - Before Agent Callback] Input from previous agent (state.trade_initiation_result):")
            callback_logger.info(_safe_json_dump(input_for_logistics_agent))
        else:
            callback_logger.warning(f"[{agent_name} - Before Agent Callback] 'trade_initiation_result' not found in shared state (input to agent).")

    else:
        callback_logger.warning(f"[{agent_name} - Before Agent Callback] No shared state object (callback_context.state) available.")


    callback_logger.info(f"[{agent_name} - Before Agent Callback] Finished processing input inspection.")
    
    # Always return None or a Content object (if overriding)
    # Since we are just observing, return None.
    return None


def after_logistics_agent_callback(
    callback_context: CallbackContext # Only argument provided to agent callbacks
) -> Optional[types.Content]:
    """
    Callback function executed just after the LogisticsDetailsAgent finishes.
    Logs the agent's final output (result).
    """
    agent_name = callback_context.agent_name
    
    # Access session_id from the session object within context if available, or invocation_id as fallback
    session_id = getattr(getattr(callback_context, 'session', None), 'id', None)
    if not session_id:
        session_id = getattr(callback_context, 'invocation_id', 'N/A_id')

    callback_logger.info(f"[{agent_name} - After Agent Callback] Session/Invocation ID: {session_id}")

    # Attempt to retrieve the final result (if passed directly)
    outgoing_result = getattr(callback_context, 'current_output', None)
    if outgoing_result:
        callback_logger.info(f"[{agent_name} - After Agent Callback] Direct current_output argument:")
        callback_logger.info(_safe_json_dump(outgoing_result))
    else:
        callback_logger.warning(f"[{agent_name} - After Agent Callback] No direct current_output argument.")


    # For sub-agents in a SequentialAgent, the actual output is written to the state.
    current_state_object = getattr(callback_context, 'state', None)
    if current_state_object:
        callback_logger.info(f"[{agent_name} - After Agent Callback] Updated shared state (callback_context.state):")
        # Log the entire state for debugging, or specific keys like logistics_details_result
        callback_logger.debug(_safe_json_dump(current_state_object))

        # Log specific output from this agent in the state
        if hasattr(current_state_object, 'logistics_details_result'):
            output_from_logistics_agent = current_state_object.logistics_details_result
            callback_logger.info(f"[{agent_name} - After Agent Callback] Agent's final output (state.logistics_details_result):")
            callback_logger.info(_safe_json_dump(output_from_logistics_agent))
        else:
            callback_logger.warning(f"[{agent_name} - After Agent Callback] 'logistics_details_result' not found in shared state after agent execution.")

    else:
        callback_logger.warning(f"[{agent_name} - After Agent Callback] No shared state object (callback_context.state) available after agent execution.")

    callback_logger.info(f"[{agent_name} - After Agent Callback] Finished processing output inspection.")

    # Always return None or a Content object (if overriding)
    # Since we are just observing, return None.
    return None