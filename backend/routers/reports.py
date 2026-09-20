import uuid
from typing import Optional, Dict
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from schemas.report import (
    LocationCoords,
    ReportResponse,
    InternalReport,
)
from schemas.evidence import EvidencePackage
from services.report_validator import (
    validate_and_extract_photo,
    validate_timestamp,
    validate_text,
)
from services.evidence_retriever import build_evidence_package

router = APIRouter(prefix="/api/v1", tags=["Reports"])

# In-memory storage for ingested citizen reports
REPORT_STORE: Dict[str, InternalReport] = {}


@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=200,
    summary="Ingest Live User Environmental Report",
    description=(
        "Ingests and validates citizen environmental reports containing photographic evidence, "
        "incident location, report timestamp, and optional incident description.\n\n"
        "Note: This stage strictly ingests and validates the inputs. "
        "It does not perform AI verification or fabricate environmental evidence."
    ),
)
async def submit_environmental_report(
    photo: UploadFile = File(
        ...,
        description="Photographic evidence file (supported formats: JPEG, PNG, WEBP; max size: 10MB)"
    ),
    latitude: float = Form(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude coordinate of the environmental incident (-90 to 90 degrees)"
    ),
    longitude: float = Form(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude coordinate of the environmental incident (-180 to 180 degrees)"
    ),
    timestamp: str = Form(
        ...,
        description="Incident timestamp in ISO 8601 format (e.g. 2026-09-17T12:00:00Z)"
    ),
    text: Optional[str] = Form(
        None,
        max_length=2000,
        description="Optional text description of the environmental event (max 2000 characters)"
    ),
):
    """
    Ingestion endpoint for citizen environmental reports.
    Executes strict validation on photo, geographic bounds, and timestamp format.
    """
    # 1. Validate and inspect uploaded photo
    photo_bytes, photo_metadata = validate_and_extract_photo(photo)

    # 2. Validate timestamp format
    validated_dt = validate_timestamp(timestamp)

    # 3. Validate text description (optional)
    cleaned_text = validate_text(text)

    # 4. Generate unique report identifier
    report_id = f"rep_{uuid.uuid4().hex}"

    # 5. Build validated location
    location = LocationCoords(latitude=latitude, longitude=longitude)

    # 6. Build internal report representation
    internal_report = InternalReport(
        report_id=report_id,
        location=location,
        timestamp=timestamp,
        text=cleaned_text,
        photo_metadata=photo_metadata,
        status="received"
    )

    # 7. Persist in report store
    REPORT_STORE[report_id] = internal_report

    # 8. Construct and return structured API response
    return ReportResponse(
        report_id=internal_report.report_id,
        status="received",
        location=location,
        timestamp=internal_report.timestamp,
        photo_received=True,
        text_received=cleaned_text is not None,
    )


@router.post(
    "/reports/{report_id}/evidence",
    response_model=EvidencePackage,
    status_code=200,
    summary="Retrieve Environmental Evidence for Ingested Report",
    description=(
        "Retrieves deterministic multi-source environmental evidence (CPCB ground sensors, "
        "weather/meteorology, Sentinel-5P satellite, NASA FIRMS active fires, and OWBEII static emissions) "
        "spatially and temporally aligned with the ingested report.\n\n"
        "Strict causal boundaries are enforced (no future observations). "
        "Does NOT call Gemini or generate AI verdicts."
    ),
)
@router.get(
    "/reports/{report_id}/evidence",
    response_model=EvidencePackage,
    status_code=200,
    include_in_schema=False,
)
async def get_report_evidence(report_id: str):
    """
    Retrieves environmental evidence package for a given report_id.
    """
    if report_id not in REPORT_STORE:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")

    report = REPORT_STORE[report_id]
    evidence_pkg = build_evidence_package(report)
    return evidence_pkg
