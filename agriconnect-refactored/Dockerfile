# Dockerfile

# Stage 1: Use a slim, modern Python base image
FROM python:3.11-slim AS base

# --- SECURE KEY INJECTION ---
# 1. Declare a build-time argument. This will be passed via the 'docker build' command.
ARG GOOGLE_API_KEY_ARG

# 2. Set the environment variable for the container using the value from the build-time argument.
# This makes the key available to your Python application at runtime.
# If the build-time arg is not provided, this will be an empty string.
ENV GOOGLE_API_KEY=$GOOGLE_API_KEY_ARG
# --- END SECURE KEY INJECTION ---

# Set environment variables to prevent Python from writing .pyc files and to buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project source code into the working directory
# Note: We no longer need to copy the .env file for the API key, but it's
# still useful for the other variables.
COPY . .

# Make the startup script executable
RUN chmod +x ./start.sh

# Expose the main entry point port (MCP server)
EXPOSE 10000
# --- CHANGE: Expose Gateway server port as well ---
EXPOSE 9000
# --- END CHANGE ---

# The command to run when the container starts.
CMD ["./start.sh"]