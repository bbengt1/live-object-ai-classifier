"""
OCR Service for extracting overlay text from video frames.

Story P9-3.2: Attempt Frame Overlay Text Extraction

This service attempts to read timestamp and camera name text embedded
in video frame overlays (commonly added by security cameras).
"""

import logging
import re
from typing import Optional
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Check if pytesseract is available
OCR_AVAILABLE = False
try:
    import pytesseract
    # Test if tesseract binary is actually available
    pytesseract.get_tesseract_version()
    OCR_AVAILABLE = True
    logger.info("OCR service initialized: pytesseract available")
except ImportError:
    logger.warning("pytesseract not installed - OCR features disabled")
except Exception as e:
    logger.warning(f"Tesseract not available - OCR features disabled: {e}")


@dataclass
class OCRResult:
    """Result from OCR extraction attempt."""
    region: str  # Which corner region was processed
    timestamp: Optional[str]  # Extracted timestamp if found
    camera_name: Optional[str]  # Extracted camera name if found
    raw_text: str  # Raw OCR output for debugging


# Timestamp patterns commonly found in security camera overlays
# Order matters - check more specific patterns first
TIMESTAMP_PATTERNS = [
    r'\d{4}[/-]\d{2}[/-]\d{2}',     # YYYY-MM-DD or YYYY/MM/DD (check first - 4-digit year)
    r'\d{2}[/-]\d{2}[/-]\d{4}',     # MM-DD-YYYY or DD/MM/YYYY (4-digit year)
    r'\d{1,2}[/:]\d{2}[/:]\d{2}',   # HH:MM:SS or H:MM:SS (time format)
    r'\d{2}[/-]\d{2}[/-]\d{2}',     # MM-DD-YY or DD/MM/YY (2-digit year - check last)
]

# Camera name patterns - look for common prefixes
# Use negative lookahead to avoid partial word matches
CAMERA_NAME_PATTERNS = [
    r'\b(CAM|CH)(?![a-zA-Z])\s*[-:.\s]?\s*(\w+)',  # CAM 1, CAM-01, CH-01, CH 1 (not Camera, Channel)
    r'\bCamera\s*[-:.\s]?\s*(\w+)',                 # Camera: Front, Camera 2
    r'\bChannel\s+(\w+)',                           # Channel 3
    r'\b(Front|Back|Rear|Side|Garage|Driveway|Porch|Door)\b',  # Common location keywords
]


def parse_timestamp(text: str) -> Optional[str]:
    """
    Extract timestamp from OCR text.

    Args:
        text: Raw OCR text to parse

    Returns:
        Extracted timestamp string if found, None otherwise
    """
    for pattern in TIMESTAMP_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group()
    return None


def parse_camera_name(text: str) -> Optional[str]:
    """
    Extract camera name from OCR text.

    Args:
        text: Raw OCR text to parse

    Returns:
        Extracted camera name if found, None otherwise
    """
    for pattern in CAMERA_NAME_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Return the last captured group (the actual name, not the prefix)
            # For patterns with multiple groups, get the last one
            return match.group(match.lastindex) if match.lastindex else match.group()
    return None


def preprocess_region(region: np.ndarray) -> np.ndarray:
    """
    Preprocess a frame region for better OCR accuracy.

    Args:
        region: BGR image region from frame

    Returns:
        Preprocessed grayscale image optimized for OCR
    """
    # Convert to grayscale
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)

    # Apply adaptive thresholding for better text contrast
    # This works better than simple threshold for varying backgrounds
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Optional: slight dilation to connect broken characters
    kernel = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    return dilated


def extract_overlay_text(frame: np.ndarray) -> Optional[OCRResult]:
    """
    Extract timestamp and camera name from frame overlay.

    Security cameras typically embed text overlays in corners of the frame
    showing timestamp, camera name, or both. This function attempts to
    extract that information using OCR.

    Args:
        frame: BGR image (numpy array) from video frame

    Returns:
        OCRResult with extracted data, or None if OCR unavailable or nothing found
    """
    if not OCR_AVAILABLE:
        logger.debug("OCR not available, skipping overlay extraction")
        return None

    if frame is None or frame.size == 0:
        logger.warning("Invalid frame provided for OCR")
        return None

    height, width = frame.shape[:2]

    # Define corner regions to check (typical overlay positions)
    # Using relative positions for different frame sizes
    region_height = min(60, height // 10)
    region_width = min(350, width // 3)

    regions = [
        ("top_left", frame[0:region_height, 0:region_width]),
        ("top_right", frame[0:region_height, width-region_width:width]),
        ("bottom_left", frame[height-region_height:height, 0:region_width]),
        ("bottom_right", frame[height-region_height:height, width-region_width:width]),
    ]

    for region_name, region in regions:
        try:
            # Preprocess for better OCR
            processed = preprocess_region(region)

            # Run OCR
            text = pytesseract.image_to_string(
                processed,
                config='--psm 7 --oem 3'  # Single line mode, best OCR engine
            ).strip()

            if not text:
                continue

            # Try to extract timestamp and camera name
            timestamp = parse_timestamp(text)
            camera_name = parse_camera_name(text)

            if timestamp or camera_name:
                logger.debug(
                    f"OCR extraction from {region_name}: timestamp={timestamp}, "
                    f"camera_name={camera_name}, raw='{text}'"
                )
                return OCRResult(
                    region=region_name,
                    timestamp=timestamp,
                    camera_name=camera_name,
                    raw_text=text
                )
        except Exception as e:
            logger.warning(f"OCR failed for {region_name}: {e}")
            continue

    logger.debug("No overlay text found in any region")
    return None


def is_ocr_available() -> bool:
    """
    Check if OCR functionality is available.

    Returns:
        True if pytesseract and tesseract are properly installed
    """
    return OCR_AVAILABLE
