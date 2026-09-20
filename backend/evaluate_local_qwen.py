import os
import json
import time
import base64
import requests
import subprocess
from pathlib import Path

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5vl:3b"

IMAGE_DIR_TEST = Path("test_images")
IMAGE_DIR_TEMP = Path("temp")

IMAGES_TO_TEST = [
    IMAGE_DIR_TEST / "smoke_industrial.jpg",
    IMAGE_DIR_TEST / "biomass_stubble.jpg",
    IMAGE_DIR_TEST / "construction_dust.jpg",
    IMAGE_DIR_TEST / "unrelated_clean_room.jpg",
    IMAGE_DIR_TEMP / "2115e976-21fd-44c5-99ad-84355aab82f6.jpg"
]

PROMPT = """You are the visual observation component of VayuNet, an environmental intelligence platform.

Analyze ONLY what is visually observable in the supplied image.

Return exactly one JSON object with these fields:

{
  "image_relevant": true,
  "smoke_visible": false,
  "dust_visible": false,
  "open_burning_visible": false,
  "plume_like_structure_visible": false,
  "visible_objects": [],
  "limitations": []
}

Rules:

- Output ONLY valid JSON.
- Use double quotes around keys and strings.
- Use true/false, never True/False.
- No Markdown.
- No explanation.
- No reasoning.
- No headings.
- No text before or after the JSON.
- Do not add fields.
- Do not identify the pollution source.
- Do not infer causality.
- Do not claim the image proves a pollution event.
- Do not invent pollutant concentrations.
- Do not invent weather.
- Do not invent GPS coordinates.
- Do not invent timestamps.
- Do not invent satellite observations.
- Do not invent sensor observations.
- Do not use external environmental information.

Definitions:

smoke_visible:
True only if smoke itself is visually distinguishable.

dust_visible:
True only if dust is visually distinguishable.

open_burning_visible:
True only if active/open burning is visibly present.

plume_like_structure_visible:
True only if a plume-like visual structure is visibly observable. This does not identify its source or composition.

visible_objects:
Only clearly visible relevant objects or structures.

limitations:
Only genuine visual ambiguities or image limitations."""


# --- Helper Functions ---

def get_gpu_memory():
    """Queries nvidia-smi for VRAM usage. Returns a string like '2048 MiB / 4096 MiB' or 'N/A'"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE, text=True, check=True
        )
        mem = result.stdout.strip().split(',')
        if len(mem) == 2:
            return f"{mem[0].strip()} MiB / {mem[1].strip()} MiB"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return "N/A"


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def validate_schema(parsed_json):
    """Verifies that the required keys exist."""
    required_keys = {
        "image_relevant", "smoke_visible", "dust_visible",
        "open_burning_visible", "plume_like_structure_visible",
        "visible_objects", "limitations"
    }
    return required_keys.issubset(set(parsed_json.keys()))


# --- Main Execution ---

def main():
    print(f"==================================================")
    print(f"LOCAL VLM EVALUATION: {MODEL_NAME}")
    print(f"==================================================")

    # 1. Verify Ollama Connection
    try:
        requests.get("http://localhost:11434/")
    except requests.exceptions.ConnectionError:
        print("ERROR: Ollama is not running on localhost:11434.")
        return

    results = []

    # 2. Iterate and evaluate images
    for img_path in IMAGES_TO_TEST:
        print(f"\nEvaluating: {img_path.name}")

        if not img_path.exists():
            print(f"  -> File not found at {img_path}")
            continue

        base64_image = encode_image(img_path)

        vram_before = get_gpu_memory()

        payload = {
            "model": MODEL_NAME,
            "prompt": PROMPT,
            "images": [base64_image],
            "stream": False,
            "options": {
                "temperature": 0.0 # Strictly greedy for consistent evaluation
            }
        }

        start_time = time.time()
        try:
            response = requests.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            raw_output = data.get("response", "")
        except Exception as e:
            print(f"  -> API Error: {e}")
            continue

        duration = time.time() - start_time
        vram_after = get_gpu_memory()

        # Strict JSON Parsing Attempt
        parsed_data = None
        json_valid = False
        schema_valid = False

        try:
            parsed_data = json.loads(raw_output)
            json_valid = True
            schema_valid = validate_schema(parsed_data)
        except json.JSONDecodeError:
            pass # We do not repair or regex, per strict instructions

        # Print per-image results
        print(f"  -> VRAM Before: {vram_before}")
        print(f"  -> VRAM After : {vram_after}")
        print(f"  -> Inference Time: {duration:.2f} seconds")
        print(f"  -> JSON Valid: {json_valid} | Schema Valid: {schema_valid}")
        print(f"  -> RAW OUTPUT:\n{raw_output.strip()}\n")

        results.append({
            "file": img_path.name,
            "duration": duration,
            "vram_before": vram_before,
            "vram_after": vram_after,
            "json_valid": json_valid,
            "schema_valid": schema_valid,
            "raw_output": raw_output
        })

    # 3. Overall Aggregation
    successful_calls = len(results)
    valid_json_count = sum(1 for r in results if r["json_valid"])
    valid_schema_count = sum(1 for r in results if r["schema_valid"])
    avg_duration = sum(r["duration"] for r in results) / successful_calls if successful_calls > 0 else 0

    print(f"\n==================================================")
    print(f"SUMMARY METRICS")
    print(f"==================================================")
    print(f"Successful image calls: {successful_calls}/{len(IMAGES_TO_TEST)}")
    print(f"Average inference time: {avg_duration:.2f} seconds")
    print(f"Valid strict JSON responses: {valid_json_count}/{successful_calls}")
    print(f"Schema-valid responses: {valid_schema_count}/{successful_calls}")

if __name__ == "__main__":
    main()
