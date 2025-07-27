# trade_orchestrator/sub_agents/new_trade_setup_workflow/seq_sub_agents/trade_initiation_agent/agent.py

import os
import json
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

from dotenv import load_dotenv
from trade_orchestrator.sub_agents.new_trade_setup_workflow.seq_sub_agents.trade_initiation_agent.prompt import TRADE_INITIATION_INSTRUCTION

orchestrator_root = Path(__file__).parent.parent.parent.parent.parent.resolve() # five levels up
load_dotenv(os.path.join(orchestrator_root, '.env'))

MODEL_NAME = os.getenv("MODEL", "gemini-2.0-flash-001")

PATH_TO_FIRESTORE_MCP_SERVER = str(orchestrator_root / "firestore_mcp" / "server.py")

if not Path(PATH_TO_FIRESTORE_MCP_SERVER).exists():
    print(f"WARNING: MCP Server script NOT FOUND at {PATH_TO_FIRESTORE_MCP_SERVER}. "
          "This agent's tools may not function.")

trade_initiation_agent = LlmAgent(
    name="TradeInitiationAgent",
    model=MODEL_NAME,
    description="Captures initial trade details and creates a record in Firestore.",
    instruction=TRADE_INITIATION_INSTRUCTION,
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
            tool_filter=['create_trade']
        )
    ],
    output_key="trade_initiation_result"
)