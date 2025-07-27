import logging
from collections.abc import AsyncIterable

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.tools import VertexAiSearchTool
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Use our new centralized settings
from common.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BuyerMatchingAgent:
    """
    A "smart" agent that uses Vertex AI Search to find real buyers from a datastore.
    This class wraps the core agent logic to be invokable by the A2A framework.
    """
    def __init__(self):
        if not settings.GOOGLE_GENAI_USE_VERTEXAI:
            raise ValueError(
                "This agent requires Vertex AI. Please set GOOGLE_GENAI_USE_VERTEXAI=true in your .env file."
            )
            
        self._agent = self._build_agent()
        self._user_id = "smart_buyer_matching_user"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def _build_agent(self) -> LlmAgent:
        # Construct the datastore path using the centralized settings
        buyer_datastore_path = (
            f"projects/{settings.GOOGLE_CLOUD_PROJECT}/locations/{settings.BUYER_DATASTORE_REGION}"
            f"/collections/default_collection/dataStores/{settings.BUYER_DATASTORE_ID}"
        )
        logger.info(f"Initializing VertexAiSearchTool with datastore: {buyer_datastore_path}")
        
        vertex_search_tool = VertexAiSearchTool(data_store_id=buyer_datastore_path)

        logger.info(f"Building SmartBuyerMatchingAgent with model: {settings.GOOGLE_MODEL_NAME}")
        
        return LlmAgent(
            name="smart_buyer_matching_agent",
            model=settings.GOOGLE_MODEL_NAME,
            description="Identifies potential buyers for the farmer's produce from a real-time datastore, and helps negotiate terms.",
            instruction="""
            Your role is to act as an Agricultural Buyer Matching Agent.
            You are an expert in connecting farmers with suitable buyers and facilitating fair negotiations.
            You have access to a real-time datastore of buyer profiles using your Vertex AI Search tool.
            
            ✅ When activated, follow this process:
            1. Ask the farmer for any missing information needed for a search, such as:
               - The **produce type** (e.g., "wheat", "tomatoes", "basmati rice")
               - **Quantity available** (in kilograms)
               - **Quality level** (e.g., "standard", "premium", "organic")
               - Their **location or region**
            
            2. Use the Vertex AI Search Tool to retrieve buyer entries that match the farmer's criteria. Formulate your search query based on the information gathered.
            3. For each matching buyer found, present the relevant details to the farmer, including:
               - Buyer's name
               - Price offer range
               - Payment and delivery terms
               - Any special conditions
            4. Provide advice on choosing a buyer by helping the farmer compare the offers.
            5. If no matching buyers are found, politely inform the farmer and suggest they revise their criteria for a better match.
            6. Always use the Vertex AI Search Tool to fetch buyer data before responding. Do not fabricate buyer information. Your primary function is to query the datastore and present the results.
            """,
            tools=[vertex_search_tool],
        )

    async def invoke(self, query: str, session_id: str) -> AsyncIterable[dict]:
        """
        Receives a user query and processes it using the agent, streaming the response.
        """
        logger.info(f"SmartBuyerMatchingAgent received query for session {session_id}: {query[:100]}...")
        
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=session_id,
                state={},
            )
            logger.info(f"Created new session {session.id} for SmartBuyerMatchingAgent.")

        user_content = types.Content(role="user", parts=[types.Part.from_text(text=query)])

        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session.id,
            new_message=user_content
        ):
            if event.is_final_response():
                response_text = ""
                if event.content and event.content.parts and event.content.parts[-1].text:
                    response_text = event.content.parts[-1].text
                logger.info(f"Final response for session {session.id}.")
                yield {'is_task_complete': True, 'content': response_text}
                break
            else:
                yield {'is_task_complete': False, 'updates': 'Searching for potential buyers in the datastore...'}