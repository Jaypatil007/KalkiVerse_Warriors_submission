import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai.types import Part

# Load environment variables.
load_dotenv()

GCS_BUCKET_PATH = os.getenv("GCS_BUCKET_PATH")
MODEL = os.getenv("MODEL", "gemini-2.0-flash") 

async def test_analyze_crop_image():
    """
    Tests the image analysis function by running the synchronous SDK call
    in a separate thread to avoid blocking the asyncio event loop.
    """
    try:
        # This client uses the synchronous API, which is what's available
        client = genai.Client()

        image_name = "tomato_crop.jpeg"
        farmer_prompt = "Based on this image, what disease is affecting my plant and what steps should I take?"
        image_uri = f"{GCS_BUCKET_PATH}/{image_name}"

        content_parts = [
            farmer_prompt,
            Part.from_uri(
                file_uri=image_uri,
                mime_type="image/jpeg",
            ),
        ]

        # This is the synchronous function we need to call
        def generate():
            return client.models.generate_content(
                model=f"publishers/google/models/{MODEL}",
                contents=content_parts
            )

        # Use asyncio.to_thread to run the blocking synchronous call in a separate thread
        response = await asyncio.to_thread(generate)

        print("--- Analysis Complete ---")
        print(response.text)
        return response.text
    except Exception as e:
        print(f"--- Error During Analysis ---")
        print(f"An error occurred: {e}")
        return f"Error analyzing image: {e}"

if __name__ == "__main__":
    if not os.getenv("GOOGLE_GENAI_USE_VERTEXAI"):
        print("Error: GOOGLE_GENAI_USE_VERTEXAI environment variable is not set.")
    else:
        asyncio.run(test_analyze_crop_image())
