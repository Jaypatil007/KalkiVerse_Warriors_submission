import os
from google.adk import Agent
from .tools import analyze_crop_image
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL", "gemini-2.0-flash")

crop_health_analyzer = Agent(
    name="crop_health_analyzer",
    model=MODEL,
    description="Analyzes crop images from a GCS bucket to identify diseases and recommend treatments.",
    instruction="""
        You are the Crop Health Analyzer.
        You will receive a file name for a crop image and a prompt from the user.
        Use the 'analyze_crop_image' tool to analyze the image and provide a comprehensive analysis
        that includes the crop name, visible symptoms, disease name (if any), severity level,
        and a suggested treatment plan.
    """,
    tools=[analyze_crop_image],
)
root_agent = crop_health_analyzer