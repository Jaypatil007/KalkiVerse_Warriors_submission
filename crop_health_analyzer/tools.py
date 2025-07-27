import os
from google import genai
from google.genai.types import Part
from dotenv import load_dotenv

# Load environment variables. The ADK and the google-generativeai library
# will automatically use the GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION
# when GOOGLE_GENAI_USE_VERTEXAI is set.
load_dotenv()

GCS_BUCKET_PATH = os.getenv("GCS_BUCKET_PATH")
MODEL = os.getenv("MODEL", "gemini-2.0-flash")


def analyze_crop_image(image_name: str, farmer_prompt: str) -> str:
    """
    Analyzes a crop image from a GCS bucket using the Gemini model through Vertex AI.

    Args:
        image_name (str): The name of the image file in the GCS bucket.
        farmer_prompt (str): The prompt from the farmer.

    Returns:
        str: The analysis of the crop image.
    """
    try:
        # When using Vertex AI, we instantiate a client.
        # It authenticates automatically in the Google Cloud environment.
        client = genai.Client()
        
        image_uri = f"{GCS_BUCKET_PATH}/{image_name}"
        
        # Prepare the content for the model
        contents = [
            farmer_prompt,
            Part.from_uri(
                file_uri=image_uri,
                mime_type="image/jpeg",
            ),
        ]
        
        # Call the model using the client
        response = client.models.generate_content(
            model=f"publishers/google/models/{MODEL}",
            contents=contents
        )
        
        return response.text
    except Exception as e:
        return f"Error analyzing image: {e}"
