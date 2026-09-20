import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend root is in sys.path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from google import genai
from google.genai import types

def main():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key_1 = os.getenv("GEMINI_API_KEY")
    api_key_2 = os.getenv("GEMINI_API_KEY_2")

    print(f"Loaded GEMINI_API_KEY: {'Yes' if api_key_1 else 'No'} (len {len(api_key_1) if api_key_1 else 0})")
    print(f"Loaded GEMINI_API_KEY_2: {'Yes' if api_key_2 else 'No'} (len {len(api_key_2) if api_key_2 else 0})")

    if not api_key_2:
        print("Error: GEMINI_API_KEY_2 not found.")
        return

    client = genai.Client(api_key=api_key_2)
    model_name = "gemini-3.6-flash"

    print(f"\n--- Checking Model {model_name} with GEMINI_API_KEY_2 ---")

    try:
        model_info = client.models.get(model=model_name)
        print("\nModel Info:")
        print(f"Name: {model_info.name}")
        print(f"Display Name: {model_info.display_name}")
        print(f"Version: {model_info.version}")
        print(f"Description: {model_info.description}")
        print(f"Input Token Limit: {model_info.input_token_limit}")
        print(f"Output Token Limit: {model_info.output_token_limit}")
        print(f"Supported Generation Methods: {model_info.supported_generation_methods}")
    except Exception as e:
        print(f"Failed to fetch model info: {e}")

    try:
        print("\n--- Checking Quotas & Limits ---")
        # In newer SDKs or API endpoints, quota information isn't always directly exposed via SDK.
        # But let's try calling a small request to see if we hit a 429 immediately, or check headers.
        # Since we just want to know if batch is supported:
        pass
    except Exception as e:
        print(f"Quota check failed: {e}")

if __name__ == "__main__":
    main()
