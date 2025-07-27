import logging
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState, UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

# Import the single root_agent from our agent.py file
from .agent import root_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PricePredictionAgentExecutor(AgentExecutor):
    """
    This executor wraps the ADK's `root_agent` and its runner,
    bridging the A2A server framework with ADK execution logic.
    """
    def __init__(self):
        self.agent = root_agent
        self.runner = Runner(
            app_name=self.agent.name,
            agent=self.agent,
            session_service=InMemorySessionService(),
        )
        logger.info(f"PricePredictionAgentExecutor initialized with ADK Agent: {self.agent.name}")

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        logger.info(f"Executing task for query: {query[:100]}...")

        task = context.current_task or new_task(context.message)
        await event_queue.enqueue_event(task)
        logger.info(f"Started task with ID: {task.id}")

        updater = TaskUpdater(event_queue, task.id, task.contextId)
        
        # Ensure a session exists in the ADK Runner's session service.
        session_id = task.contextId
        user_id = "a2a_user" # A static user ID for the A2A session
        
        session = await self.runner.session_service.get_session(
            app_name=self.agent.name,
            user_id=user_id,
            session_id=session_id,
        )
        if session is None:
            session = await self.runner.session_service.create_session(
                app_name=self.agent.name,
                user_id=user_id,
                session_id=session_id,
            )
            logger.info(f"ADK Runner created new internal session: {session.id}")

        try:
            user_content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
            
            # The ADK runner handles the entire lifecycle, including sub-agent calls
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=user_content,
            ):
                if event.is_final_response():
                    response_text = ""
                    if event.content and event.content.parts and event.content.parts[-1].text:
                        response_text = event.content.parts[-1].text
                    
                    logger.info(f"Task {task.id} completed. Final content: {response_text[:100]}...")
                    message = new_agent_text_message(response_text, task.contextId, task.id)
                    await updater.update_status(TaskState.completed, message)
                    break 

        except Exception as e:
            logger.exception(f"Error during agent execution for task {task.id}: {e}")
            error_message = f"An error occurred: {str(e)}"
            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(error_message, task.contextId, task.id)
            )
            raise

    async def cancel(self, request: RequestContext, event_queue: EventQueue):
        logger.warning("Cancellation is not supported by this agent.")
        raise ServerError(error=UnsupportedOperationError())
