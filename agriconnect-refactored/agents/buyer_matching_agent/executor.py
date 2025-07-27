import logging
import asyncio
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState, UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from .agent import BuyerMatchingAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BuyerMatchingAgentExecutor(AgentExecutor):
    """
    Bridges the A2A server framework with the BuyerMatchingAgent logic.
    """
    def __init__(self):
        self.agent = BuyerMatchingAgent()
        logger.info("BuyerMatchingAgentExecutor initialized with BuyerMatchingAgent.")

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        logger.info(f"Executing task for query: {query[:100]}...")

        task = context.current_task or new_task(context.message)
        await event_queue.enqueue_event(task)
        logger.info(f"Started task with ID: {task.id}")

        updater = TaskUpdater(event_queue, task.id, task.contextId)
        
        try:
            async for item in self.agent.invoke(query, task.contextId):
                if item.get('is_task_complete'):
                    final_content = item.get('content', 'No content received.')
                    logger.info(f"Task {task.id} completed. Final content length: {len(final_content)} chars.")
                    message = new_agent_text_message(final_content, task.contextId, task.id)
                    await updater.update_status(TaskState.completed, message)
                    await asyncio.sleep(0.1)
                    break
                else:
                    update_message = item.get('updates', 'Agent is processing...')
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(update_message, task.contextId, task.id)
                    )
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