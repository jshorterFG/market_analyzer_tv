import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = "sp500trading"
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION)

try:
    model = GenerativeModel("gemini-1.0-pro")
    print("gemini-1.0-pro is available")
except Exception as e:
    print(f"gemini-1.0-pro error: {e}")

try:
    model = GenerativeModel("gemini-pro")
    print("gemini-pro is available")
except Exception as e:
    print(f"gemini-pro error: {e}")
