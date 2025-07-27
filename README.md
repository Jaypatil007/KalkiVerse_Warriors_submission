# KalkiVerse_Warriors_submission
# AgriConnect: AI-Powered Agricultural Trade Platform

AgriConnect is an intelligent system designed to streamline agricultural trade processes by leveraging advanced AI agents and Google Cloud services. It connects farmers with buyers, provides market insights, and manages trade logistics.

## Core Features:

*   **Intelligent Agent Network**: Utilizes specialized AI agents (e.g., Price Predictors, Buyer Matchers, Trade Coordinators) powered by Google's Gemini models and Vertex AI.
*   **End-to-End Trade Management**: Facilitates the entire trade lifecycle, from initial setup and logistics to payment and notifications.
*   **Real-time Market Insights**: Provides accurate price predictions based on current web data and historical trends.
*   **Buyer Discovery**: Connects farmers with potential buyers through intelligent matching and datastore searches.
*   **Logistics & Payment Handling**: Manages post-sale activities including transport, delivery, and payment tracking.
*   **Cloud-Native Architecture**: Built for scalability and reliability using Google Cloud Run, Firestore, Pub/Sub, and Vertex AI.

## Deployment Process:

This project is designed to be deployed using Docker and Google Cloud services. The primary deployment involves building a Docker image and running it, while specific agents and services interact with Google Cloud for AI capabilities and data management.

### 1. Build the Docker Image:

Navigate to the project root directory and build the Docker image. Replace `"apikey"` with your actual Google API key.

```bash
cd ~/SuperDemo/agriconnect-refactored
docker build --build-arg GOOGLE_API_KEY_ARG="YOUR_GOOGLE_API_KEY" -t agriconnect-server .
2. Run the Docker Container:
Run the built Docker container, mapping the necessary ports for the MCP and Gateway servers.

docker run --rm -it -p 10000:10000 -p 9000:9000 agriconnect-server
3. Agent Interaction and Testing:
After the server is running, you can interact with the system and test individual agents. Ensure you have your virtual environment activated (avenv) and the ADK CLI installed.

Activate virtual environment:

cd ~/SuperDemo/agriconnect-refactored && avenv
Run the Orchestrator Agent (for high-level interaction):

cd agents && adk web
Then, use prompts like:

Hello
I want to find buyers for my Basmati rice of premium quality, I have 1000 kg and looking for buyer in Maharashtra nashik region
find current market price for onion in Nashik region
I just made a new sale. I sold 500 kg of fresh bell peppers to Sunshine Grocers for $1200. They want to pick it up tomorrow morning from the main barn. Payment terms are net 15 days.
Test Crop Health Analyzer (Requires GCS setup and GOOGLE_GENAI_USE_VERTEXAI=true in .env):

Activate virtual environment:
cd ~/SuperDemo && avenv
Run ADK web interface:
adk web
Then, use prompts like:
Crop Diesease . (Note: This prompt is very vague and might not yield good results.)
I've uploaded a picture of my plant named 'mangoissue.jpeg'. Based on this image, please tell me what disease is affecting it and what steps I should take to cure it.”
I've uploaded a picture of my plant named 'tomato_crop.jpeg'. Based on this image, please tell me what disease is affecting it and what steps I should take to cure it.”
