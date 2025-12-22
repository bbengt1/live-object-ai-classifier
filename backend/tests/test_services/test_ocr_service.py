"""
Unit tests for OCR Service (Story P9-3.2).

Tests OCR extraction from video frame overlays, timestamp parsing,
camera name parsing, and graceful degradation.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from app.services.ocr_service import (
    OCRResult,
    parse_timestamp,
    parse_camera_name,
    preprocess_region,
    extract_overlay_text,
    is_ocr_available,
    TIMESTAMP_PATTERNS,
    CAMERA_NAME_PATTERNS,
)


class TestTimestampParsing:
    """Test timestamp extraction from OCR text (AC-3.2.1)."""

    def test_parse_timestamp_hh_mm_ss_colon(self):
        """Parse HH:MM:SS format."""
        assert parse_timestamp("10:30:45") == "10:30:45"
        assert parse_timestamp("Camera 1 10:30:45 Front Door") == "10:30:45"

    def test_parse_timestamp_hh_mm_ss_slash(self):
        """Parse HH/MM/SS format."""
        assert parse_timestamp("10/30/45") == "10/30/45"

    def test_parse_timestamp_yyyy_mm_dd(self):
        """Parse YYYY-MM-DD format."""
        assert parse_timestamp("2025-12-22") == "2025-12-22"
        assert parse_timestamp("Recording: 2025-12-22") == "2025-12-22"

    def test_parse_timestamp_yyyy_mm_dd_slash(self):
        """Parse YYYY/MM/DD format."""
        assert parse_timestamp("2025/12/22") == "2025/12/22"

    def test_parse_timestamp_mm_dd_yyyy(self):
        """Parse MM-DD-YYYY format."""
        assert parse_timestamp("12-22-2025") == "12-22-2025"

    def test_parse_timestamp_mm_dd_yy(self):
        """Parse MM-DD-YY short format."""
        assert parse_timestamp("12-22-25") == "12-22-25"

    def test_parse_timestamp_none_when_not_found(self):
        """Return None when no timestamp pattern found."""
        assert parse_timestamp("Front Door Camera") is None
        assert parse_timestamp("") is None
        assert parse_timestamp("No timestamp here") is None

    def test_parse_timestamp_single_digit_hour(self):
        """Handle single digit hour format."""
        assert parse_timestamp("7:15:00 AM") == "7:15:00"


class TestCameraNameParsing:
    """Test camera name extraction from OCR text (AC-3.2.2)."""

    def test_parse_camera_name_cam_prefix(self):
        """Parse CAM prefix pattern."""
        assert parse_camera_name("CAM 1") == "1"
        assert parse_camera_name("CAM-01") == "01"
        assert parse_camera_name("CAM: Front") == "Front"

    def test_parse_camera_name_camera_prefix(self):
        """Parse Camera prefix pattern."""
        assert parse_camera_name("Camera: Driveway") == "Driveway"
        assert parse_camera_name("Camera 2") == "2"

    def test_parse_camera_name_channel_prefix(self):
        """Parse Channel/CH prefix pattern."""
        assert parse_camera_name("CH-01") == "01"
        assert parse_camera_name("Channel 3") == "3"

    def test_parse_camera_name_location_keywords(self):
        """Parse common location keywords."""
        assert parse_camera_name("Front Door") == "Front"
        assert parse_camera_name("Back Yard") == "Back"
        assert parse_camera_name("Garage Camera") == "Garage"
        assert parse_camera_name("Driveway View") == "Driveway"
        assert parse_camera_name("Porch") == "Porch"
        assert parse_camera_name("Side Entrance") == "Side"

    def test_parse_camera_name_none_when_not_found(self):
        """Return None when no camera name pattern found."""
        assert parse_camera_name("12:30:45") is None
        assert parse_camera_name("2025-12-22") is None
        assert parse_camera_name("") is None


class TestPreprocessRegion:
    """Test image preprocessing for OCR."""

    def test_preprocess_region_converts_to_grayscale(self):
        """Verify region is converted to grayscale."""
        # Create a simple BGR image (blue channel filled)
        bgr_image = np.zeros((50, 300, 3), dtype=np.uint8)
        bgr_image[:, :, 0] = 128  # Blue channel

        result = preprocess_region(bgr_image)

        # Result should be 2D (grayscale after thresholding)
        assert len(result.shape) == 2
        assert result.shape == (50, 300)

    def test_preprocess_region_handles_white_text_on_black(self):
        """Verify preprocessing handles typical overlay contrast."""
        # Create black background with white region
        bgr_image = np.zeros((50, 300, 3), dtype=np.uint8)
        bgr_image[10:40, 50:250] = 255  # White rectangle

        result = preprocess_region(bgr_image)

        # Should have white (255) and black (0) values
        assert result.max() == 255
        assert result.min() == 0


class TestOCRResultDataclass:
    """Test OCRResult dataclass."""

    def test_ocr_result_creation(self):
        """Test OCRResult creation with all fields."""
        result = OCRResult(
            region="top_left",
            timestamp="10:30:45",
            camera_name="Front Door",
            raw_text="CAM: Front Door 10:30:45"
        )

        assert result.region == "top_left"
        assert result.timestamp == "10:30:45"
        assert result.camera_name == "Front Door"
        assert result.raw_text == "CAM: Front Door 10:30:45"

    def test_ocr_result_with_none_values(self):
        """Test OCRResult with None for optional fields."""
        result = OCRResult(
            region="bottom_right",
            timestamp=None,
            camera_name="Driveway",
            raw_text="Driveway"
        )

        assert result.timestamp is None
        assert result.camera_name == "Driveway"


class TestExtractOverlayText:
    """Test full OCR extraction workflow."""

    def test_extract_overlay_text_returns_none_when_ocr_unavailable(self):
        """AC-3.2.6: Gracefully handle missing tesseract."""
        # Since OCR_AVAILABLE is set at import time, we need to reload the module
        # For now, just verify the function handles the global flag
        from app.services import ocr_service
        original_value = ocr_service.OCR_AVAILABLE

        try:
            ocr_service.OCR_AVAILABLE = False
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            result = ocr_service.extract_overlay_text(frame)
            assert result is None
        finally:
            ocr_service.OCR_AVAILABLE = original_value

    def test_extract_overlay_text_returns_none_for_invalid_frame(self):
        """Handle invalid frame input."""
        assert extract_overlay_text(None) is None
        assert extract_overlay_text(np.array([])) is None

    def test_extract_overlay_text_processes_corners_when_ocr_available(self):
        """Test that all four corners would be checked with OCR available."""
        from app.services import ocr_service

        # If OCR is not available, skip this test
        if not ocr_service.OCR_AVAILABLE:
            pytest.skip("pytesseract not installed")

        # This test would require a real tesseract installation
        # For CI, just verify the function doesn't crash with empty frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = ocr_service.extract_overlay_text(frame)
        # Result may be None if no text found, which is fine
        assert result is None or isinstance(result, OCRResult)

    def test_extract_overlay_text_handles_small_frame(self):
        """Handle very small frames gracefully."""
        from app.services import ocr_service

        # Small frame shouldn't crash
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        result = ocr_service.extract_overlay_text(frame)
        # Should not raise, may return None
        assert result is None or isinstance(result, OCRResult)


class TestIsOcrAvailable:
    """Test OCR availability check."""

    def test_is_ocr_available_returns_bool(self):
        """Function should return boolean."""
        result = is_ocr_available()
        assert isinstance(result, bool)


class TestBuildContextPromptWithOCR:
    """Test build_context_prompt integration with OCR results (AC-3.2.3, AC-3.2.4)."""

    def test_context_prompt_uses_ocr_camera_name_for_generic_db_name(self):
        """AC-3.2.3: OCR data supplements DB data for generic names."""
        from app.services.ai_service import build_context_prompt

        ocr_result = OCRResult(
            region="top_left",
            timestamp="10:30:45",
            camera_name="Front Door",
            raw_text="CAM: Front Door 10:30:45"
        )

        # Generic database name should be replaced by OCR name
        prompt = build_context_prompt(
            camera_name="Camera 1",
            timestamp="2025-12-22T10:30:45+00:00",
            ocr_result=ocr_result
        )

        assert '"Front Door" camera' in prompt

    def test_context_prompt_keeps_db_name_when_specific(self):
        """AC-3.2.3: Keep specific DB name even when OCR differs."""
        from app.services.ai_service import build_context_prompt

        ocr_result = OCRResult(
            region="top_left",
            timestamp="10:30:45",
            camera_name="CAM1",
            raw_text="CAM1 10:30:45"
        )

        # Specific database name should be kept
        prompt = build_context_prompt(
            camera_name="Driveway",
            timestamp="2025-12-22T10:30:45+00:00",
            ocr_result=ocr_result
        )

        assert '"Driveway" camera' in prompt

    def test_context_prompt_fallback_without_ocr(self):
        """AC-3.2.4: Fall back to DB metadata when no OCR."""
        from app.services.ai_service import build_context_prompt

        prompt = build_context_prompt(
            camera_name="Backyard",
            timestamp="2025-12-22T15:00:00+00:00",
            ocr_result=None
        )

        assert '"Backyard" camera' in prompt
        assert "3:00 PM" in prompt
        assert "afternoon" in prompt

    def test_context_prompt_handles_none_ocr_camera_name(self):
        """AC-3.2.4: Handle OCR result with no camera name."""
        from app.services.ai_service import build_context_prompt

        ocr_result = OCRResult(
            region="top_left",
            timestamp="10:30:45",
            camera_name=None,
            raw_text="10:30:45"
        )

        prompt = build_context_prompt(
            camera_name="Front Porch",
            timestamp="2025-12-22T10:30:45+00:00",
            ocr_result=ocr_result
        )

        # Should use DB name
        assert '"Front Porch" camera' in prompt
