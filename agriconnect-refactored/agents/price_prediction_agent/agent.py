from google.adk.agents import Agent, LlmAgent
from google.adk.tools import google_search, VertexAiSearchTool
from google.adk.tools.agent_tool import AgentTool

# Use our new centralized settings
from common.settings import settings

# Construct the full datastore path from settings
PRICE_DATASTORE_PATH = (
    f"projects/{settings.GOOGLE_CLOUD_PROJECT}/locations/{settings.PRICE_DATASTORE_REGION}"
    f"/collections/default_collection/dataStores/{settings.PRICE_DATASTORE_ID}"
)

# --- Sub-agent for fetching current prices via Google Search ---
google_search_price_agent = Agent(
    name="google_search_price_agent",
    model=settings.GOOGLE_MODEL_NAME,
    description="Fetches current market prices and news for agricultural produce.",
    instruction="""
    Use the Google Search tool to find the most recent market prices and news for the given crop and region.
    Extract: crop, region, current price range, trend observation, data currency, and URLs checked.
    Return findings as a structured JSON string. Do not add any conversational text.
    If data is not found, indicate "current_price_range": "Not found".
    """,
    tools=[google_search],
)

# --- Sub-agent for fetching historical prices from Vertex AI Search ---
vertex_search_tool_historical = VertexAiSearchTool(data_store_id=PRICE_DATASTORE_PATH)
vertex_ai_search_price_agent = Agent(
    name="vertex_ai_search_price_agent",
    model=settings.GOOGLE_MODEL_NAME,
    description="Retrieves historical agricultural price data from a Vertex AI Search datastore.",
    instruction="""
    Use the Vertex AI Search tool to query the datastore for historical price entries for the specified crop and location.
    Extract: crop, query location, historical period, average modal price, typical price range, trend observation, and data points summary.
    Return findings as a structured JSON string. Do not add any conversational text.
    If data is not found, indicate "typical_price_range": "Not found".
    """,
    tools=[vertex_search_tool_historical],
)

# --- Main Hierarchical Agent (The one we expose) ---
smart_price_prediction_agent = LlmAgent(
    name="smart_price_prediction_agent_v2",
    model=settings.GOOGLE_MODEL_NAME,
    description="Predicts agricultural produce prices by consulting two specialist sub-agents for current and historical data.",
    instruction="""
    You are an expert Agricultural Price Prediction Advisor. Your task is to provide a data-driven price prediction and selling advice.

    **WORKFLOW:**
    1.  **Identify Inputs:** From the user's query, identify the `crop_name` and `location`.
    2.  **Delegate Data Gathering:** You MUST call two sub-agents to gather data:
        *   First, call `google_search_price_agent` to get CURRENT market data. The query should be `[crop_name] price in [location]`.
        *   Second, call `vertex_ai_search_price_agent` to get HISTORICAL price trends. The query should be `historical price for [crop_name] in [location]`.
    3.  **Synthesize Results:** Once both sub-agents have responded, analyze their JSON outputs. Compare the current data with historical trends.
    4.  **Formulate Prediction:** Based on your synthesis, create a final report that includes:
        - A predicted price range for the near future.
        - The optimal time to sell (e.g., "now", "in 2 weeks").
        - The reasoning behind your advice, referencing both current and historical data.
    5.  **Output:** Provide a single, comprehensive text report. Do not output raw JSON.

    You are an orchestrator. Your primary job is to call your tools and then think about their outputs to generate a final, human-readable answer.
    """,
    tools=[
        AgentTool(agent=google_search_price_agent),
        AgentTool(agent=vertex_ai_search_price_agent),
    ],
)

# This is the single entry point for both `adk web` and our A2A server.
root_agent = smart_price_prediction_agent