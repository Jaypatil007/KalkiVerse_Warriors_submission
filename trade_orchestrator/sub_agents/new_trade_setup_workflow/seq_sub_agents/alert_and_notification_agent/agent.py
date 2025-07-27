# trade_orchestrator/sub_agents/new_trade_setup_workflow/seq_sub_agents/alert_and_notification_agent/agent.py

import os
import json
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

from dotenv import load_dotenv
# Import the template string
from trade_orchestrator.sub_agents.new_trade_setup_workflow.seq_sub_agents.alert_and_notification_agent.prompt import ALERT_NOTIFICATION_INSTRUCTION 

orchestrator_root = Path(__file__).parent.parent.parent.parent.parent.resolve() # five levels up
load_dotenv(os.path.join(orchestrator_root, '.env'))

MODEL_NAME = os.getenv("MODEL", "gemini-2.0-flash-001")
PUBSUB_TOPIC_ID = os.getenv("PUBSUB_TOPIC_ID", "trade-notifications") # Get the actual topic ID here


PATH_TO_FIRESTORE_MCP_SERVER = str(orchestrator_root / "firestore_mcp" / "server.py")

if not Path(PATH_TO_FIRESTORE_MCP_SERVER).exists():
    print(f"WARNING: MCP Server script NOT FOUND at {PATH_TO_FIRESTORE_MCP_SERVER}. "
          "This agent's tools may not function.")

alert_and_notification_agent = LlmAgent(
    name="AlertAndNotificationAgent",
    model=MODEL_NAME,
    description="Composes notifications and publishes them to Google Cloud Pub/Sub, then provides a consolidated summary of the New Trade Setup Workflow.",
    # --- FIX: Use an f-string here to inject the PUBSUB_TOPIC_ID ---
    instruction=ALERT_NOTIFICATION_INSTRUCTION,
    # --- END FIX ---,
    # Note: If there were other placeholders, you'd add them here too.
    # The .format() method makes it clearer these are placeholders.
    # --- END FIX ---
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters( # Keep StdioServerParameters for local testing / orchestrator structure
                command="python3",
                args=[PATH_TO_FIRESTORE_MCP_SERVER],
                env={
                    "PYTHONPATH": str(orchestrator_root) + os.pathsep + os.getenv("PYTHONPATH", ""),
                    **os.environ
                }
            ),
            tool_filter=['get_trade_by_id', 'pubsub_notification_function', 'format_final_alert_output']
        )
    ],
    output_key="alert_notification_result"
)