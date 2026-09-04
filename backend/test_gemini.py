import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load .env from backend or root directory
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("[ERROR] GEMINI_API_KEY is not set in your .env file.")
    exit(1)

print("[INFO] GEMINI_API_KEY found. Connecting to Gemini API...")

try:
    client = genai.Client(api_key=api_key)
    
    # Using recommended gemini-3.6-flash model
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Confirm connectivity for VayuNet environmental intelligence system. Return a short 1-sentence confirmation."
    )
    
    print("\n[SUCCESS] Connectivity Confirmed!")
    print("Model Response:")
    print("-" * 50)
    print(response.text.strip())
    print("-" * 50)
except Exception as e:
    print(f"\n[ERROR] Failed to connect to Gemini API: {e}")
    exit(1)
