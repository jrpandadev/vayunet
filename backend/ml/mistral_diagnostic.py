import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

def run_diagnostic():
    # Step 1: Load environment safely
    backend_root = Path(__file__).resolve().parent.parent
    env_path = backend_root / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("DIAGNOSTIC: MISTRAL_API_KEY is not found in environment.")
        return

    print("DIAGNOSTIC: MISTRAL_API_KEY is present.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Step 3: Test Models Endpoint
    print("\n--- Testing /v1/models ---")
    try:
        resp = requests.get("https://api.mistral.ai/v1/models", headers=headers)
        print(f"Status Code: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("id") for m in data.get("data", [])]
            has_large = "mistral-large-latest" in models
            print(f"Request Succeeded: True")
            print(f"mistral-large-latest Available: {has_large}")

            # Step 4: Test Completion if models succeeded
            print("\n--- Testing /v1/chat/completions ---")
            payload = {
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": "Return exactly: TEST_OK"}]
            }
            start_time = time.time()
            comp_resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload)
            latency = time.time() - start_time
            print(f"Completion Status Code: {comp_resp.status_code}")

            if comp_resp.status_code == 200:
                comp_data = comp_resp.json()
                print(f"Model Returned: {comp_data.get('model')}")
                print(f"Response Text: {comp_data['choices'][0]['message']['content']}")
                print(f"Request ID: {comp_data.get('id')}")
                print(f"Latency: {latency:.2f} seconds")
                usage = comp_data.get('usage', {})
                print(f"Token Usage: Input={usage.get('prompt_tokens')}, Output={usage.get('completion_tokens')}, Total={usage.get('total_tokens')}")
            else:
                print(f"Completion Request Failed. Error Body: {comp_resp.text}")

        else:
            print(f"Request Succeeded: False")
            print(f"Error Body: {resp.text}")
    except Exception as e:
        print(f"Exception during diagnostic: {e}")

if __name__ == "__main__":
    run_diagnostic()
