import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

def get_mistral_models():
    # Load environment securely
    backend_root = Path(__file__).resolve().parent.parent
    env_path = backend_root / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("Error: MISTRAL_API_KEY not found.")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    resp = requests.get("https://api.mistral.ai/v1/models", headers=headers)

    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        models = [m.get("id") for m in data.get("data", [])]
        print("Models Available:")
        for m in sorted(models):
            print(f" - {m}")
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    get_mistral_models()
