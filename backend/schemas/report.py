from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class LocationCoords(BaseModel):
    """Geographic coordinates of the environmental incident."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate between -90 and 90 degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate between -180 and 180 degrees")


class PhotoMetadata(BaseModel):
    """Metadata extracted safely from validated image upload."""
    filename: Optional[str] = None
    content_type: str
    size_bytes: int
    format: str
    width: int
    height: int


class ReportResponse(BaseModel):
    """
    Structured API response returned to the client upon successful ingestion.
    Does NOT return any environmental verdict, AI score, or fabricated evidence.
    """
    report_id: str = Field(..., description="Unique tracking identifier for the report")
    status: Literal["received"] = Field("received", description="Ingestion status of the report")
    location: LocationCoords
    timestamp: str = Field(..., description="ISO 8601 timestamp provided with the report")
    photo_received: bool = Field(True, description="Whether photographic evidence was received and validated")
    text_received: bool = Field(..., description="Whether a non-empty text description was provided")


class InternalReport(BaseModel):
    """
    Internal representation of an ingested environmental report record.
    Preserves raw inputs and extracted safe metadata without AI classification or synthesis.
    """
    report_id: str
    location: LocationCoords
    timestamp: str
    text: Optional[str] = None
    photo_metadata: PhotoMetadata
    status: str = "received"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
