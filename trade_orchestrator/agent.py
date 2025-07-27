# trade_orchestrator/agent.py

import os
import json
from pathlib import Path
#from google.adk.agents import LlmAgent
from dotenv import load_dotenv

from google.adk import Agent

# Import Top-Level Sub-Agents (their instances)
from trade_orchestrator.sub_agents.logistics_status_update_agent import logistics_status_update_agent
from trade_orchestrator.sub_agents.new_trade_setup_workflow import new_trade_setup_workflow
from trade_orchestrator.sub_agents.trade_query_agent import trade_query_agent

# Import instruction from prompt.py
from trade_orchestrator.prompt import ROUTING_INSTRUCTION

# Load environment variables for this agent and its sub-agents
orchestrator_base_path = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(orchestrator_base_path, '.env'))

MODEL_NAME = os.getenv("MODEL", "gemini-2.0-flash-001")

trade_orchestration_root_agent = Agent(
    name="TradeOrchestratorAgent",
    model=MODEL_NAME,
    description="The main orchestration agent for agricultural trade management, routing requests to specialized sub-agents and processing their outcomes.",
    instruction=ROUTING_INSTRUCTION, # ROUTING_INSTRUCTION now comes from prompt.py
    sub_agents=[
        logistics_status_update_agent,
        new_trade_setup_workflow,
        trade_query_agent,
    ],
    output_key="Finalstate",
)

root_agent = trade_orchestration_root_agent