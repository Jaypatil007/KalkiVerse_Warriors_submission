#### 13. `trade_orchestrator/sub_agents/logistics_status_update_agent/agent.py` (**MODIFIED: No callbacks, uses `prompt.py`, new output format**)

# trade_orchestrator/sub_agents/logistics_status_update_agent/agent.py

import os
import json
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

from dotenv import load_dotenv
from trade_orchestrator.sub_agents.logistics_status_update_agent.prompt import LOGISTICS_UPDATE_INSTRUCTION # NEW import

orchestrator_root = Path(__file__).parent.parent.parent.resolve() # three levels up
load_dotenv(os.path.join(orchestrator_root, '.env'))

MODEL_NAME = os.getenv("MODEL", "gemini-2.0-flash-001")

PATH_TO_FIRESTORE_MCP_SERVER = str(orchestrator_root / "firestore_mcp" / "server.py")

if not Path(PATH_TO_FIRESTORE_MCP_SERVER).exists():
    print(f"WARNING: MCP Server script NOT FOUND at {PATH_TO_FIRESTORE_MCP_SERVER}. "
          "This agent's tools may not function.")

logistics_status_update_agent = LlmAgent(
    name="LogisticsStatusUpdateAgent",
    model=MODEL_NAME,
    description="Updates specific fields (tags) of an existing trade record directly in Firestore. Can update any valid field.",
    instruction=LOGISTICS_UPDATE_INSTRUCTION, # Instruction from prompt.py
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="python3",
                args=[PATH_TO_FIRESTORE_MCP_SERVER],
                env={
                    "PYTHONPATH": str(orchestrator_root) + os.pathsep + os.getenv("PYTHONPATH", ""),
                    **os.environ
                }
            ),
            tool_filter=['get_trade_by_id', 'update_trade'] # Only provide relevant tools
        )
    ],
    output_key="logistics_status_update_result" # Name for this agent's output in state
)