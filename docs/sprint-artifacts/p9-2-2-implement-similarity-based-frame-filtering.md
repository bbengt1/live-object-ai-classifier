# Story 9.2.2: Implement Similarity-Based Frame Filtering

Status: done

## Story

As a **system**,
I want **to skip redundant frames that look nearly identical**,
So that **AI analyzes diverse frames without wasting tokens on duplicates**.

## Acceptance Criteria

1. **AC-2.2.1:** Given 100 raw frames extracted, when similarity filtering runs, then frames with >95% SSIM are removed
2. **AC-2.2.2:** Given consecutive identical frames, when filtering runs, then only first is kept
3. **AC-2.2.3:** Given visually distinct frames, when filtering runs, then all are retained
4. **AC-2.2.4:** Given filtering completes, when viewing logs, then filter ratio is logged (e.g., "Filtered 100→45 frames")

## Tasks / Subtasks

- [x] Task 1: Implement SSIM-based similarity comparison (AC: 2.2.1)
  - [x] Add SSIM function using OpenCV
  - [x] Create `is_similar()` function with 0.95 threshold
  - [x] Resize frames to 256x256 for faster comparison
- [x] Task 2: Create similarity filter function (AC: 2.2.2, 2.2.3)
  - [x] Implement `filter_similar_frames()` in frame_extractor.py
  - [x] Process frames sequentially, compare to last kept frame
  - [x] Return filtered frames with original indices
- [x] Task 3: Integrate with frame extraction pipeline (AC: 2.2.1)
  - [x] Add similarity filtering functions to FrameExtractor class
  - [x] Make similarity threshold configurable via parameter
  - [x] Add SIMILARITY_THRESHOLD constant (0.95)
- [x] Task 4: Add logging for filter ratio (AC: 2.2.4)
  - [x] Log input frame count and output frame count
  - [x] Log similarity threshold used
  - [x] Log time taken for filtering
- [x] Task 5: Write unit tests (12 tests)
- [x] Task 6: Run all tests to verify

## Dev Notes

### Technical Approach

Use SSIM (Structural Similarity Index) from scikit-image to compare consecutive frames. Frames with >95% similarity to the previously kept frame are skipped. This ensures AI receives diverse visual content without wasting tokens on near-identical frames.

### Architecture Pattern

```
Raw Frames (100+) → Resize (256x256) → SSIM Compare → Filter → Unique Frames (20-50)
                                            ↓
                              Compare each to last kept frame
                                            ↓
                              If similarity > 0.95: skip
                              If similarity <= 0.95: keep
```

### Source Components

- `backend/app/services/frame_extractor.py` - Add `filter_similar_frames()` and `is_similar()`
- `backend/tests/test_services/test_frame_extractor.py` - Add similarity filter tests

### Testing Standards

- Unit tests for SSIM calculation
- Unit tests with identical frames (should filter all but first)
- Unit tests with diverse frames (should keep all)
- Performance test: 100 frames in <500ms

### References

- [Source: docs/sprint-artifacts/tech-spec-epic-P9-2.md#P9-2.2]
- [Source: docs/epics-phase9.md#Story P9-2.2]
- [Backlog: FF-020]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5

### Debug Log References

### Completion Notes List

### File List

- `backend/app/services/frame_extractor.py` - Added `_calculate_ssim()`, `is_similar()`, `filter_similar_frames()`
- `backend/tests/test_services/test_frame_extractor.py` - Added 12 tests in `TestSimilarityFiltering` class

