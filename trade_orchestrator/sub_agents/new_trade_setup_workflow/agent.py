# trade_orchestrator/sub_agents/new_trade_setup_workflow/agent.py
from google.adk.agents import SequentialAgent

# Import the sub-agents that are part of this sequential workflow.
# These imports rely on the __init__.py files in their respective directories.
from trade_orchestrator.sub_agents.new_trade_setup_workflow.seq_sub_agents.trade_initiation_agent import trade_initiation_agent
from trade_orchestrator.sub_agents.new_trade_setup_workflow.seq_sub_agents.logistics_details_agent import logistics_details_agent
from trade_orchestrator.sub_agents.new_trade_setup_workflow.seq_sub_agents.payment_management_agent import payment_management_agent
from trade_orchestrator.sub_agents.new_trade_setup_workflow.seq_sub_agents.alert_and_notification_agent import alert_and_notification_agent
# Import instruction from prompt.py
from trade_orchestrator.sub_agents.new_trade_setup_workflow.prompt import NEW_TRADE_WORKFLOW_DESCRIPTION
new_trade_setup_workflow = SequentialAgent(
    name="NewTradeSetupWorkflow",
    sub_agents=[
        trade_initiation_agent,     # Input: farmer_message, extracted_entities. Output: state.trade_initiation_result containing trade_id
        logistics_details_agent,    # Input: uses state.trade_initiation_result.trade_id and initial farmer_message for details. Output: state.logistics_details_result
        payment_management_agent,   # Input: uses state.trade_initiation_result.trade_id and farmer_message for terms. Output: state.payment_management_result
        alert_and_notification_agent  # Input: uses state.trade_id, state.logistics_details_result, state.payment_management_result to send confirmation. Output: state.alert_notification_result
    ],
    description=NEW_TRADE_WORKFLOW_DESCRIPTION,
)