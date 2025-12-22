# Story 9.3.2: Attempt Frame Overlay Text Extraction

Status: done

## Story

As a **system**,
I want **to read timestamp/camera name embedded in video frames**,
So that **I can use the camera's own metadata when available**.

## Acceptance Criteria

1. **AC-3.2.1:** Given OCR enabled in settings, when frame has visible timestamp, then timestamp extracted
2. **AC-3.2.2:** Given OCR enabled, when frame has camera name overlay, then name extracted
3. **AC-3.2.3:** Given OCR extraction succeeds, when building context, then OCR data supplements DB data
4. **AC-3.2.4:** Given OCR extraction fails, when building context, then fallback to DB metadata only
5. **AC-3.2.5:** Given OCR disabled in settings, when processing event, then OCR not attempted
6. **AC-3.2.6:** Given tesseract not installed, when OCR attempted, then graceful error with warning

## Tasks / Subtasks

- [x] Task 1: Add OCR setting to system settings (AC: 3.2.5)
  - [x] Add `attempt_ocr_extraction` boolean to settings model
  - [x] Default to `false` (opt-in due to CPU cost)
  - [x] Expose in GET/PUT `/api/v1/system/settings`
- [x] Task 2: Create OCR service module (AC: 3.2.1, 3.2.2)
  - [x] Create `backend/app/services/ocr_service.py`
  - [x] Implement `extract_overlay_text(frame: np.ndarray)` function
  - [x] Target corner regions: top-left, top-right, bottom-left, bottom-right
  - [x] Preprocess regions (grayscale, threshold) for OCR
  - [x] Run pytesseract on preprocessed regions
- [x] Task 3: Implement timestamp parsing (AC: 3.2.1)
  - [x] Create `parse_timestamp(text: str)` function
  - [x] Support patterns: HH:MM:SS, YYYY-MM-DD, MM-DD-YYYY
  - [x] Return parsed timestamp or None
- [x] Task 4: Implement camera name parsing (AC: 3.2.2)
  - [x] Create `parse_camera_name(text: str)` function
  - [x] Identify camera-like text patterns
  - [x] Return extracted camera name or None
- [x] Task 5: Handle missing tesseract gracefully (AC: 3.2.6)
  - [x] Try importing pytesseract at module load
  - [x] Set `OCR_AVAILABLE` flag based on import success
  - [x] Log warning if tesseract not installed
  - [x] Return None without error when OCR unavailable
- [x] Task 6: Integrate OCR into context building (AC: 3.2.3, 3.2.4)
  - [x] Modify `build_context_prompt()` to accept optional OCR data
  - [x] If OCR succeeds, use OCR timestamp/camera name when available
  - [x] Always fallback to DB metadata when OCR fails
  - [x] Log OCR extraction results for debugging
- [x] Task 7: Add OCR setting toggle to Settings UI
  - [x] Add checkbox in General Settings for "Attempt OCR extraction"
  - [x] Add helper text explaining CPU cost and requirement for tesseract
- [x] Task 8: Write unit tests
  - [x] Test OCR extraction with sample images
  - [x] Test timestamp parsing patterns
  - [x] Test camera name parsing
  - [x] Test graceful degradation when tesseract missing
  - [x] Test setting toggle behavior
- [x] Task 9: Run all tests to verify

## Dev Notes

### Technical Approach

Implement optional OCR extraction to read timestamps and camera names from video frame overlays (commonly embedded by security cameras). This data supplements database metadata, improving AI context accuracy.

Key design decisions:
- **Opt-in by default**: OCR is CPU-intensive, disabled by default
- **Graceful degradation**: System works without tesseract installed
- **Corner targeting**: Security camera overlays are typically in corners
- **Fallback strategy**: Always fall back to DB metadata if OCR fails

### OCR Extraction Algorithm

```python
def extract_overlay_text(frame: np.ndarray) -> Optional[dict]:
    """Extract timestamp/camera from frame overlay."""
    regions = [
        ("top_left", frame[0:50, 0:300]),
        ("top_right", frame[0:50, -300:]),
        ("bottom_left", frame[-50:, 0:300]),
        ("bottom_right", frame[-50:, -300:]),
    ]

    for region_name, region in regions:
        # Preprocess for OCR
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # Run OCR
        text = pytesseract.image_to_string(thresh)

        # Parse for patterns
        timestamp = parse_timestamp(text)
        camera_name = parse_camera_name(text)

        if timestamp or camera_name:
            return {
                "region": region_name,
                "timestamp": timestamp,
                "camera_name": camera_name,
                "raw_text": text
            }

    return None
```

### Timestamp Patterns

```python
patterns = [
    r'\d{2}[/:]\d{2}[/:]\d{2}',  # HH:MM:SS or HH/MM/SS
    r'\d{4}[/-]\d{2}[/-]\d{2}',  # YYYY-MM-DD
    r'\d{2}[/-]\d{2}[/-]\d{4}',  # MM-DD-YYYY
]
```

### Dependencies

```
# NEW dependency for OCR
pytesseract>=0.3.10  # Python wrapper for Tesseract OCR

# System dependency (must be installed separately)
# tesseract-ocr  # apt-get install tesseract-ocr
```

### Source Components

- `backend/app/services/ocr_service.py` - New OCR service module
- `backend/app/services/ai_service.py` - Integrate OCR with context building
- `backend/app/api/v1/system.py` - Add OCR setting
- `frontend/app/settings/page.tsx` - Add OCR toggle

### Learnings from Previous Story

**From Story p9-3-1-add-camera-and-time-context-to-ai-prompt (Status: done)**

- **New Functions Created**: `get_time_of_day_category()` and `build_context_prompt()` in `backend/app/services/ai_service.py` (lines 163-227)
- **Context Format Established**: `Context: This footage is from the "Camera Name" camera at 7:15 AM on Sunday, December 22, 2025 (morning).`
- **Testing Pattern**: Added `TestContextPromptBuilding` and `TestPromptBuildingWithContext` test classes in test_ai_service.py
- **Integration Points**: `_build_user_prompt()` and `_build_multi_image_prompt()` both use context building

[Source: docs/sprint-artifacts/p9-3-1-add-camera-and-time-context-to-ai-prompt.md#Dev-Agent-Record]

### Testing Standards

- Unit tests for OCR extraction with sample images
- Unit tests for timestamp/camera name parsing
- Unit tests for graceful tesseract missing handling
- Integration tests with context building
- Frontend component tests for settings toggle

### References

- [Source: docs/sprint-artifacts/tech-spec-epic-P9-3.md#P9-3.2]
- [Source: docs/epics-phase9.md#Story P9-3.2]
- [Backlog: IMP-012]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5

### Debug Log References

### Completion Notes List

- Created `ocr_service.py` with OCR extraction, timestamp parsing, and camera name parsing
- Added `attempt_ocr_extraction` setting to `SystemSettings` and `SystemSettingsUpdate` schemas
- Updated `build_context_prompt()` in `ai_service.py` to accept optional OCR data (supplements DB metadata)
- Added OCR toggle switch to Settings UI with informational note about CPU cost and tesseract requirement
- Added TypeScript types and validation for new setting
- Created 25 unit tests for OCR functionality in `test_ocr_service.py`
- All 172 backend tests pass (1 skipped for missing tesseract)

### File List

- `backend/app/services/ocr_service.py` - New OCR service module with extraction functions
- `backend/app/services/ai_service.py` - Updated `build_context_prompt()` to accept OCR data (lines 189-250)
- `backend/app/schemas/system.py` - Added `attempt_ocr_extraction` to settings schemas (lines 201-205, 350-352)
- `backend/tests/test_services/test_ocr_service.py` - New test file with 25 tests
- `frontend/app/settings/page.tsx` - Added OCR toggle in General Settings (lines 562-596)
- `frontend/types/settings.ts` - Added `attempt_ocr_extraction` type (lines 60-61)
- `frontend/lib/settings-validation.ts` - Added OCR setting validation (lines 23-24)

