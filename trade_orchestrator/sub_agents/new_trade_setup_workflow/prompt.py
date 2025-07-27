# trade_orchestrator/sub_agents/new_trade_setup_workflow/prompt.py

NEW_TRADE_WORKFLOW_DESCRIPTION = """
This agent orchestrates the sequential setup of a new agricultural trade.
It calls sub-agents to:
1. Initiate the trade and get a trade ID, extracting initial details.
2. Add logistics details (pickup, delivery, dates).
3. Manage payment terms and status.
4. Send final alerts and notifications, and provide a comprehensive summary.
"""