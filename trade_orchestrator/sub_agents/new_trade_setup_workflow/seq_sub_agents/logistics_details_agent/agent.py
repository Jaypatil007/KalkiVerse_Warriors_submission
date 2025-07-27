# trade_orchestrator/sub_agents/new_trade_setup_workflow/seq_sub_agents/logistics_details_agent/agent.py

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

from dotenv import load_dotenv
from trade_orchestrator.sub_agents.new_trade_setup_workflow.seq_sub_agents.logistics_details_agent.prompt import LOGISTICS_DETAILS_INSTRUCTION # NEW import

orchestrator_root = Path(__file__).parent.parent.parent.parent.parent.resolve() # five levels up
load_dotenv(os.path.join(orchestrator_root, '.env'))

MODEL_NAME = os.getenv("MODEL", "gemini-2.0-flash-001")

PATH_TO_FIRESTORE_MCP_SERVER = str(orchestrator_root / "firestore_mcp" / "server.py")

if not Path(PATH_TO_FIRESTORE_MCP_SERVER).exists():
    print(f"WARNING: MCP Server script NOT FOUND at {PATH_TO_FIRESTORE_MCP_SERVER}. "
          "This agent's tools may not function.")


logistics_details_agent = LlmAgent(
    name="LogisticsDetailsAgent",
    model=MODEL_NAME,
    description="Gathers logistics details, parses dates, updates the trade record in Firestore, and adds status tags.",
    instruction=LOGISTICS_DETAILS_INSTRUCTION, # Instruction from prompt.py
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
            tool_filter=[
                'update_trade',
                'simulated_datetime_parser_function'
            ]
        )
    ],
    output_key="logistics_summary" # Changed output_key
)