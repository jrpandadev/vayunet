import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend root is in sys.path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from models import CitizenGeminiOutput, CitizenEvidence
from google import genai
from google.genai import types


# Load environment
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

EVIDENCE_PROMPT = """
You are an environmental evidence analyst for a pollution detection system (VayuNet).
Analyze the provided photo and citizen description to extract structured evidence.

Citizen's text/voice description: "{description}"

Respond ONLY with valid JSON matching this exact structure, no other text or explanation:
{{
  "event_type": "smoke" | "dust" | "industrial" | "burning" | "other" | "unclear",
  "severity": "low" | "medium" | "high",
  "confidence": <float between 0.0 and 1.0>,
  "description": "<a clear one-sentence summary of what the evidence shows>",
  "needs_human_review": <true if the image is ambiguous, unrelated, or description conflicts with image, else false>
}}

Rules:
- If no photo is provided or the photo is unclear or completely unrelated (e.g. cat, indoor room, clean sky), lower your confidence significantly and set event_type to "unclear" or "other".
- Do not guess the pollution source with absolute certainty — classify only what is visibly/descriptively evident.
- Confidence should reflect how clearly this evidence indicates a real pollution incident.
"""

def extract_evidence(description: str, image_path: str = None) -> dict:
    """
    Multimodal evidence extraction using Google GenAI SDK (gemini-2.5-flash / gemini-3.6-flash).
    Validates output directly against VayuNet locked schema.
    """
    global client
    if not client:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
        else:
            return {
                "gemini_output": {
                    "event_type": "unclear",
                    "severity": "low",
                    "confidence": 0.0,
                    "description": "GEMINI_API_KEY not configured.",
                    "needs_human_review": True
                },
                "photo_url": image_path,
                "source": "citizen",
                "freshness": "stale"
            }

    prompt = EVIDENCE_PROMPT.format(description=description)
    contents = [prompt]

    if image_path and os.path.exists(image_path):
        try:
            # Upload image or pass file bytes using genai SDK
            with open(image_path, "rb") as f:
                img_bytes = f.read()
            mime_type = "image/jpeg"
            if image_path.lower().endswith(".png"):
                mime_type = "image/png"
            elif image_path.lower().endswith(".webp"):
                mime_type = "image/webp"

            contents.append(
                types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
            )
        except Exception as e:
            print(f"[WARN] Failed to load image {image_path}: {e}")

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        raw_json = json.loads(text)
        validated_output = CitizenGeminiOutput(**raw_json)
        
        citizen_evidence = CitizenEvidence(
            gemini_output=validated_output,
            photo_url=image_path,
            source="citizen",
            freshness="fresh"
        )
        return citizen_evidence.model_dump()

    except Exception as e:
        print(f"[ERROR] Evidence extraction or validation failed: {e}")
        fallback_output = CitizenGeminiOutput(
            event_type="unclear",
            severity="low",
            confidence=0.0,
            description="Could not process evidence reliably.",
            needs_human_review=True
        )
        return CitizenEvidence(
            gemini_output=fallback_output,
            photo_url=image_path,
            source="citizen",
            freshness="stale"
        ).model_dump()


if __name__ == "__main__":
    print("Testing text-only evidence extraction...")
    res = extract_evidence(description="Heavy smoke near the industrial area, very thick black clouds")
    print(json.dumps(res, indent=2))
