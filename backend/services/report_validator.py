import io
from datetime import datetime
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
from PIL import Image, UnidentifiedImageError

from schemas.report import PhotoMetadata

MAX_PHOTO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Supported magic bytes signatures
# JPEG: FF D8 FF
# PNG: 89 50 4E 47 0D 0A 1A 0A
# WEBP: RIFF....WEBP
ALLOWED_MIME_TYPES = {
    "image/jpeg": "JPEG",
    "image/jpg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


def validate_and_extract_photo(photo: UploadFile) -> Tuple[bytes, PhotoMetadata]:
    """
    Safely inspects and validates an uploaded photo file without executing code
    or persisting files to disk prematurely.

    Validates:
    - File exists and has non-zero size
    - Size does not exceed MAX_PHOTO_SIZE_BYTES (HTTP 413)
    - Magic bytes match supported image formats (JPEG, PNG, WEBP) (HTTP 415)
    - Image is not corrupted or truncated using PIL verify() (HTTP 400)

    Returns:
        Tuple of (raw_bytes, PhotoMetadata)
    """
    if not photo or not photo.filename:
        raise HTTPException(status_code=422, detail="Photo file must be provided")

    # Read bytes safely
    try:
        contents = photo.file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded photo: {str(e)}")

    if not contents or len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded photo is empty (0 bytes)")

    if len(contents) > MAX_PHOTO_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded photo exceeds maximum allowed size of {MAX_PHOTO_SIZE_BYTES // (1024 * 1024)}MB"
        )

    # Magic byte inspection (do not blindly trust client Content-Type)
    detected_format: Optional[str] = None
    if contents.startswith(b"\xff\xd8\xff"):
        detected_format = "JPEG"
    elif contents.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_format = "PNG"
    elif len(contents) >= 12 and contents.startswith(b"RIFF") and contents[8:12] == b"WEBP":
        detected_format = "WEBP"
    else:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format. Supported formats are JPEG, PNG, and WEBP."
        )

    # PIL verification for corruption / truncations
    try:
        bio = io.BytesIO(contents)
        with Image.open(bio) as img:
            img.verify()

        # Re-open after verify() to inspect actual dimensions safely
        bio.seek(0)
        with Image.open(bio) as img:
            width, height = img.size
            if width <= 0 or height <= 0:
                raise HTTPException(status_code=400, detail="Invalid image dimensions")
            actual_format = img.format or detected_format

    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="File is not a valid or readable image")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Corrupted or malformed image: {str(e)}")

    mime_type = photo.content_type or f"image/{detected_format.lower()}"

    metadata = PhotoMetadata(
        filename=photo.filename,
        content_type=mime_type,
        size_bytes=len(contents),
        format=actual_format or detected_format,
        width=width,
        height=height,
    )

    return contents, metadata


def validate_timestamp(timestamp_str: str) -> datetime:
    """
    Validates that the timestamp string is a well-formed ISO 8601 timestamp.
    Rejects malformed strings with HTTP 422.
    """
    if not timestamp_str or not timestamp_str.strip():
        raise HTTPException(status_code=422, detail="Timestamp string cannot be empty")

    clean_str = timestamp_str.strip()
    # Normalize Z to +00:00 for standard isoformat parsing
    normalized = clean_str.replace("Z", "+00:00") if clean_str.endswith("Z") else clean_str

    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid timestamp format: '{timestamp_str}'. Must be a valid ISO 8601 string."
        )

    if dt.year < 1970 or dt.year > 2100:
        raise HTTPException(
            status_code=422,
            detail=f"Timestamp year {dt.year} is out of realistic operating bounds."
        )

    return dt


def validate_text(text: Optional[str]) -> Optional[str]:
    """
    Validates optional text input. Basic sanitization only; does not run LLM classification.
    """
    if text is None:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    if len(cleaned) > 2000:
        raise HTTPException(
            status_code=422,
            detail="Text description exceeds maximum allowed length of 2000 characters."
        )
    return cleaned
