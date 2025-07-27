import os
import httpx
import logging
import json
from uuid import uuid4

from a2a.client import A2AClient
from a2a.types import SendMessageRequest, MessageSendParams, AgentCard, Message

from mcp import ClientSession
from mcp.client.sse import sse_client

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Use our new centralized settings
from common.settings import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def call_agent(task_description: str) -> str:
    """
    Finds the best specialist agent via MCP and calls it through the MCP proxy.

    Args:
        task_description: A natural language description of the task.

    Returns:
        The text response from the specialized agent.
    """
    logger.info(f"Orchestrator received task: '{task_description[:70]}...'")
    
    agent_card_json_str = ""
    mcp_sse_url = f"{settings.MCP_SERVER_URL}/sse"

    try:
        # Step 1: Connect to MCP server to find the right agent
        logger.info(f"Connecting to MCP server at {mcp_sse_url} to find an agent.")
        async with sse_client(mcp_sse_url, timeout=30) as (reader, writer):
            async with ClientSession(read_stream=reader, write_stream=writer) as session:
                await session.initialize()
                tool_result = await session.call_tool(
                    name='find_agent',
                    arguments={'query': task_description}
                )
                agent_card_json_str = tool_result.content[0].text

        if not agent_card_json_str:
            raise ValueError("MCP server did not return an agent card.")

        # Step 2: Parse the agent card. The URL will now be the MCP proxy URL.
        agent_card_data = json.loads(agent_card_json_str)
        if "error" in agent_card_data:
            raise ValueError(f"MCP Server Error: {agent_card_data['error']}")

        agent_card = AgentCard(**agent_card_data)
        logger.info(f"MCP server selected agent: '{agent_card.name}' at proxy URL: {agent_card.url}")
        
        # Step 3: Use the discovered agent card to make an A2A call.
        # The A2AClient will transparently call the proxy URL provided in the card.
        async with httpx.AsyncClient(timeout=300.0) as httpx_client:
            a2a_client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

            message_to_send = Message(
                role='user',
                parts=[{'kind': 'text', 'text': task_description}],
                messageId=str(uuid4()),
                contextId=str(uuid4()), # Create a unique context/session for this call
            )
            request = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(message=message_to_send)
            )
            
            logger.info(f"Sending A2A request to agent '{agent_card.name}' via its proxy URL.")
            response_record = await a2a_client.send_message(request)
            response_dict = response_record.model_dump(mode='json')

            if 'error' in response_dict:
                return f"Agent returned an error: {response_dict['error'].get('message')}"

            # Correctly parse the nested A2A response
            result_data = response_dict.get('result', {})
            status_data = result_data.get('status', {})
            message_data = status_data.get('message', {})
            parts_data = message_data.get('parts', [])
            
            if parts_data:
                response_text = parts_data[0].get('text', 'Agent returned an empty response.')
                logger.info(f"Received final text from '{agent_card.name}': '{response_text[:100]}...'")
                return response_text
            else:
                return "Agent completed the task but returned no text content."

    except httpx.ConnectError as e:
        error_msg = f"Connection Error: Could not connect to the MCP server at {mcp_sse_url}. Is it running? Details: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred during orchestration: {e}"
        logger.exception(error_msg)
        return error_msg

# --- Orchestrator Agent Definition ---
root_agent = LlmAgent(
    model=settings.GOOGLE_MODEL_NAME,
    name="agriconnect_orchestrator",
    description="Main AgriConnect agent that assists farmers by finding and delegating tasks to specialized sub-agents.",
    instruction="""
    You are AgriConnect, a friendly and helpful AI assistant for farmers.
    Your primary role is to understand the farmer's needs and delegate tasks to specialized agents using the 'call_agent' tool.
    You DO NOT perform tasks like price prediction or buyer matching yourself. You find and delegate to an expert.

    Workflow:
    1. Greet the farmer warmly and ask how you can assist them.
    2. Listen carefully to the farmer's request to identify their primary goal.
    3. Use the `call_agent` tool to delegate the task. The `task_description` should be the user's full, detailed request. The tool will automatically find the best specialist (e.g., price predictor, buyer matcher, or logistics coordinator).
       - Example: If the user says "I need to know the price for onions in Nashik", you call `call_agent(task_description='I need to know the price for onions in Nashik')`.
       - Example: If the user says "Help me sell my 5 tons of wheat", you call `call_agent(task_description='Help me sell my 5 tons of wheat')`.
    4. Before calling the tool, inform the user which kind of expert you are looking for. E.g., "Okay, let me find a Price Prediction expert for you."
    5. Relay the specialist agent's response back to the farmer clearly and conversationally.
    6. If the user's request is unclear, ask clarifying questions before calling an agent.
    """,
    tools=[
        FunctionTool(call_agent),
    ],
)