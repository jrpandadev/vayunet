import os
import httpx
from typing import Optional

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET_NAME = "vayunet-evidence"

async def upload_evidence(file_bytes: bytes, file_name: str, content_type: str = "image/jpeg") -> Optional[str]:
    """Uploads file to Supabase Storage and returns the public URL or path."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("Supabase credentials missing")
        return None

    # Construct the Supabase Storage REST URL
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{file_name}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": content_type
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, content=file_bytes)

        if response.status_code in (200, 201):
            return file_name
        else:
            print(f"Supabase upload failed: {response.text}")
            return None

def get_public_url(file_name: str) -> str:
    """Gets the public URL for a file in Supabase Storage."""
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_name}"

async def get_signed_url(file_name: str, expires_in: int = 3600) -> Optional[str]:
    """Generates a signed URL for a private file in Supabase Storage."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None

    url = f"{SUPABASE_URL}/storage/v1/object/sign/{BUCKET_NAME}/{file_name}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"expiresIn": expires_in}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            return f"{SUPABASE_URL}{response.json().get('signedURL')}"
        else:
            print(f"Supabase signed URL failed: {response.text}")
            return None
