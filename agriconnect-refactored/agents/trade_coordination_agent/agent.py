import logging
from collections.abc import AsyncIterable

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Use our new centralized settings
from common.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradeCoordinationAgent:
    """
    An ADK-powered agent that specializes in post-sale logistics and tracking.
    This class wraps the core agent logic to be invokable by the A2A framework.
    """
    def __init__(self):
        self._agent = self._build_agent()
        self._user_id = "trade_coordination_user"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def _build_agent(self) -> LlmAgent:
        logger.info(f"Building TradeCoordinationAgent with model: {settings.GOOGLE_MODEL_NAME}")
        return LlmAgent(
            model=settings.GOOGLE_MODEL_NAME,
            name="trade_coordination_agent",
            description="Manages logistics, sends alerts, and tracks transactions once a trade agreement is in place.",
            instruction="""
            Your role is to act as an agricultural TradeCoordination Agent.
            You are an expert in managing the operational aspects of a trade after an agreement has been made.

            When activated, you should assume a deal has been agreed upon by the farmer and a buyer.
            1. Confirm the details of the agreed trade: crop, quantity, price, buyer, and terms.
            2. (Simulate) Assisting with logistics planning like transport and pickup/delivery dates.
            3. (Simulate) Tracking the transaction by sending alerts for payment, dispatch, and delivery.
            4. Provide clear status updates to the farmer at each key stage.
            5. Answer any questions the farmer has about the ongoing trade process.
            Focus ONLY on post-agreement coordination, logistics, alerts, and tracking. Do not get involved in price prediction or finding new buyers.
            """
        )

    async def invoke(self, query: str, session_id: str) -> AsyncIterable[dict]:
        """
        Receives a user query and processes it using the agent, streaming the response.
        """
        logger.info(f"TradeCoordinationAgent received query for session {session_id}: {query[:100]}...")
        
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
            logger.info(f"Created new session {session.id} for TradeCoordinationAgent.")

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
                yield {'is_task_complete': False, 'updates': 'Coordinating trade logistics...'}