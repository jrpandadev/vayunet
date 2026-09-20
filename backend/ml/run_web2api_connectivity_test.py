import time
import requests

def main():
    print("Starting Web2API Connectivity Test...")
    start_time = time.time()
    try:
        payload = {
            "model": "gemini-3.6-flash",
            "messages": [{"role": "user", "content": "Hello! What model are you and who created you?"}],
            "max_tokens": 100
        }
        headers = {"Content-Type": "application/json", "Authorization": "Bearer sk-gemini"}
        response = requests.post("http://127.0.0.1:8081/v1/chat/completions", json=payload, headers=headers)
        latency = time.time() - start_time

        print(f"Latency: {latency:.2f} seconds")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response successful.")
            print("Content:")
            print(response.json()["choices"][0]["message"]["content"])
        else:
            print("Response failed:")
            print(response.text)
    except Exception as e:
        print(f"Error during request: {e}")

if __name__ == "__main__":
    main()
