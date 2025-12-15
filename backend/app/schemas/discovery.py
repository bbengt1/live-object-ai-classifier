"""
ONVIF Camera Discovery Schemas (Story P5-2.1)

Pydantic models for ONVIF WS-Discovery endpoints.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DiscoveredDevice(BaseModel):
    """
    Represents a device discovered via WS-Discovery.

    Contains the minimal information extracted from ProbeMatch responses.
    Full device details (manufacturer, model, RTSP URLs) are retrieved
    in Story P5-2.2 via GetDeviceInformation.
    """
    endpoint_url: str = Field(
        ...,
        description="XAddrs service URL from ProbeMatch response"
    )
    scopes: List[str] = Field(
        default_factory=list,
        description="Device scopes (e.g., onvif://www.onvif.org/type/NetworkVideoTransmitter)"
    )
    types: List[str] = Field(
        default_factory=list,
        description="Device types from ProbeMatch (e.g., tdn:NetworkVideoTransmitter)"
    )
    metadata_version: Optional[str] = Field(
        None,
        description="Metadata version from ProbeMatch if available"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "endpoint_url": "http://192.168.1.100:80/onvif/device_service",
                "scopes": [
                    "onvif://www.onvif.org/type/NetworkVideoTransmitter",
                    "onvif://www.onvif.org/Profile/Streaming"
                ],
                "types": ["tdn:NetworkVideoTransmitter"],
                "metadata_version": "1"
            }
        }
    )


class DiscoveryRequest(BaseModel):
    """Request body for camera discovery endpoint."""
    timeout: int = Field(
        10,
        ge=1,
        le=60,
        description="Discovery timeout in seconds (default: 10, max: 60)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timeout": 10
            }
        }
    )


class DiscoveryResponse(BaseModel):
    """Response from camera discovery endpoint."""
    status: str = Field(
        ...,
        description="Discovery status: 'complete', 'timeout', or 'error'"
    )
    duration_ms: int = Field(
        ...,
        description="Time taken for discovery scan in milliseconds"
    )
    devices: List[DiscoveredDevice] = Field(
        default_factory=list,
        description="List of discovered ONVIF devices"
    )
    device_count: int = Field(
        ...,
        description="Number of devices discovered"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if status is 'error'"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "complete",
                "duration_ms": 8234,
                "devices": [
                    {
                        "endpoint_url": "http://192.168.1.100:80/onvif/device_service",
                        "scopes": ["onvif://www.onvif.org/type/NetworkVideoTransmitter"],
                        "types": ["tdn:NetworkVideoTransmitter"],
                        "metadata_version": "1"
                    }
                ],
                "device_count": 1,
                "error_message": None
            }
        }
    )
