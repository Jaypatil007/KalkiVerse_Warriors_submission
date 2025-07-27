# trade_orchestrator/sub_agents/trade_query_agent/agent.py

import os
import json
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

from dotenv import load_dotenv # Ensure load_dotenv is imported
from trade_orchestrator.sub_agents.trade_query_agent.prompt import TRADE_QUERY_INSTRUCTION # NEW import

orchestrator_root = Path(__file__).parent.parent.parent.resolve() # three levels up
load_dotenv(os.path.join(orchestrator_root, '.env'))

MODEL_NAME = os.getenv("MODEL", "gemini-2.0-flash-001")


PATH_TO_FIRESTORE_MCP_SERVER = str(orchestrator_root / "firestore_mcp" / "server.py")

if not Path(PATH_TO_FIRESTORE_MCP_SERVER).exists():
    print(f"WARNING: MCP Server script NOT FOUND at {PATH_TO_FIRESTORE_MCP_SERVER}. "
          "This agent's tools may not function.")


trade_query_agent = LlmAgent(
    name="TradeQueryAgent",
    model=MODEL_NAME,
    description="Answers farmer queries about their agricultural trades, including pending payments, completed trades, or specific trade details, by querying Firestore via an MCP server.",
    instruction=TRADE_QUERY_INSTRUCTION, # Instruction from prompt.py
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
            tool_filter=['get_trade_by_id', 'query_trades'] # Only provide relevant tools
        )
    ],
    output_key="trade_query_result" # Name for this agent's output in state
)