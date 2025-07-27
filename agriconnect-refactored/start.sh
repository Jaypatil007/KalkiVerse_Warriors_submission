#!/bin/bash

# start.sh

# This script launches all the necessary servers for the AgriConnect application.
# Each server is started as a background process.

echo "--- Starting AgriConnect Multi-Agent System ---"

# --- CRITICAL CHANGE ---
# MCP Server MUST listen on the PORT provided by Cloud Run.
# If PORT is not set (e.g., local run), default to 10000.
MCP_PORT=${PORT:-10000}
echo "Starting MCP Server on 0.0.0.0:${MCP_PORT}..."
python -m mcp_server --host 0.0.0.0 --port ${MCP_PORT} &

# Gateway Server will listen on a fixed internal port.
GATEWAY_PORT=9000
echo "Starting Gateway Server on 0.0.0.0:${GATEWAY_PORT}..."
python -m gateway_server --host 0.0.0.0 --port ${GATEWAY_PORT} &

# Agent Servers will listen on their fixed internal ports.
echo "Starting Price Prediction Agent on 0.0.0.0:10001..."
python -m agents.price_prediction_agent --host 0.0.0.0 --port 10001 &

echo "Starting Buyer Matching Agent on 0.0.0.0:10002..."
python -m agents.buyer_matching_agent --host 0.0.0.0 --port 10002 &

echo "Starting Trade Coordination Agent on 0.0.0.0:10003..."
python -m agents.trade_coordination_agent --host 0.0.0.0 --port 10003 &

echo "--- All services started. ---"

# Wait for any background process to exit.
wait -n

exit $?