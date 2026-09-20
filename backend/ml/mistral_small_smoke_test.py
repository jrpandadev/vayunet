import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

def run_smoke_test():
    backend_root = Path(__file__).resolve().parent.parent
    env_path = backend_root / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print(json.dumps({"error": "MISTRAL_API_KEY not found in environment"}))
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string"
            }
        },
        "required": ["status"],
        "additionalProperties": False
    }

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "user", "content": "Return status TEST_OK."}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "status_response",
                "schema": schema,
                "strict": True
            }
        }
    }

    start_time = time.time()
    try:
        resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        latency = time.time() - start_time

        result = {
            "status_code": resp.status_code,
            "latency": round(latency, 3),
            "headers": dict(resp.headers)
        }

        if resp.status_code == 200:
            data = resp.json()
            result["success"] = True
            result["model"] = data.get("model")
            result["request_id"] = data.get("id") or resp.headers.get("x-request-id")
            content = data["choices"][0]["message"]["content"]
            result["response_text"] = content
            try:
                result["response_json"] = json.loads(content)
            except Exception as e:
                result["response_json_error"] = str(e)
            usage = data.get("usage", {})
            result["prompt_tokens"] = usage.get("prompt_tokens")
            result["completion_tokens"] = usage.get("completion_tokens")
            result["total_tokens"] = usage.get("total_tokens")
        else:
            result["success"] = False
            result["error_body"] = resp.text
            try:
                result["error_json"] = resp.json()
            except Exception:
                pass

        print(json.dumps(result, indent=2))

    except Exception as e:
        latency = time.time() - start_time
        print(json.dumps({
            "success": False,
            "exception": str(e),
            "latency": round(latency, 3)
        }, indent=2))

if __name__ == "__main__":
    run_smoke_test()
