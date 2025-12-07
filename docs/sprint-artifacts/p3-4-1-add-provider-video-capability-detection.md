# Story P3-4.1: Add Provider Video Capability Detection

Status: done

## Story

As a **system**,
I want **to know which AI providers support video input**,
So that **video_native mode routes to capable providers**.

## Acceptance Criteria

1. **AC1:** Given AIService provider configuration, when capability is checked, then returns capability matrix with:
   - OpenAI GPT-4o: video=true, max_duration=60s
   - Claude: video=false
   - Gemini: video=true, max_duration=60s
   - Grok: video=false (TBD)

2. **AC2:** Given video_native analysis requested, when provider doesn't support video, then that provider is skipped in fallback chain, and next video-capable provider is tried

3. **AC3:** Given no video-capable providers configured, when video_native mode is selected, then system falls back to multi_frame immediately, and logs "No video-capable providers available"

## Tasks / Subtasks

- [x] **Task 1: Analyze current AI service provider structure** (AC: All)
  - [x] 1.1 Review `ai_service.py` to understand current provider implementation
  - [x] 1.2 Identify provider configuration pattern (provider priority list, API key validation)
  - [x] 1.3 Review current fallback chain implementation (from P3-3.5)
  - [x] 1.4 Document existing provider method signatures

- [x] **Task 2: Define provider capabilities data structure** (AC: 1)
  - [x] 2.1 Create `PROVIDER_CAPABILITIES` constant dictionary in `ai_service.py`
  - [x] 2.2 Define capability schema: `{"video": bool, "max_video_duration": int, "max_video_size_mb": int, "supported_formats": list}`
  - [x] 2.3 Populate capabilities for all four providers:
    - OpenAI: `{"video": True, "max_video_duration": 60, "max_video_size_mb": 20, "supported_formats": ["mp4", "mov", "webm"]}`
    - Claude: `{"video": False, "max_video_duration": 0, "max_video_size_mb": 0, "supported_formats": []}`
    - Gemini: `{"video": True, "max_video_duration": 60, "max_video_size_mb": 20, "supported_formats": ["mp4", "mov", "webm"]}`
    - Grok: `{"video": False, "max_video_duration": 0, "max_video_size_mb": 0, "supported_formats": []}`
  - [x] 2.4 Add `max_images` capability for multi-frame (OpenAI: 10, Claude: 20, Gemini: 16, Grok: 10)

- [x] **Task 3: Implement capability query methods in AIService** (AC: 1, 2)
  - [x] 3.1 Add `get_provider_capabilities(provider: str) -> dict` method
  - [x] 3.2 Add `supports_video(provider: str) -> bool` method
  - [x] 3.3 Add `get_video_capable_providers() -> list[str]` method
  - [x] 3.4 Add `get_max_video_duration(provider: str) -> int` method
  - [x] 3.5 Add `get_max_video_size(provider: str) -> int` method

- [x] **Task 4: Integrate capability detection into fallback chain** (AC: 2, 3)
  - [x] 4.1 Modify `_try_video_native_analysis()` in `protect_event_handler.py` to check video capability before attempting
  - [x] 4.2 Filter provider list to video-capable providers when video_native mode is requested
  - [x] 4.3 Log which providers were skipped due to lack of video support
  - [x] 4.4 Ensure fallback to multi_frame when no video providers are available

- [x] **Task 5: Add capability endpoint to AI API** (AC: 1)
  - [x] 5.1 Add `GET /api/v1/ai/capabilities` endpoint
  - [x] 5.2 Return capabilities matrix for all configured providers
  - [x] 5.3 Include which providers have valid API keys configured
  - [x] 5.4 Create Pydantic response schema for capabilities

- [x] **Task 6: Write backend tests** (AC: All)
  - [x] 6.1 Test `get_provider_capabilities()` returns correct data for each provider
  - [x] 6.2 Test `supports_video()` returns correct boolean for each provider
  - [x] 6.3 Test `get_video_capable_providers()` returns only OpenAI and Gemini
  - [x] 6.4 Test video_native fallback when no video providers configured
  - [x] 6.5 Test provider skipping in fallback chain when video not supported
  - [x] 6.6 Test `/api/v1/ai/capabilities` endpoint returns expected structure

## Dev Notes

### Architecture References

- **Provider Capability Pattern**: Static capability matrix with runtime API key validation
- **Fallback Integration**: Extends existing fallback chain from P3-3.5
- **Service Location**: `backend/app/services/ai_service.py`
- [Source: docs/epics-phase3.md#Story-P3-4.1]
- [Source: docs/architecture.md#AI-Service]

### Project Structure Notes

- Primary implementation: `backend/app/services/ai_service.py`
- Fallback chain integration: `backend/app/services/protect_event_handler.py`
- API endpoint: `backend/app/api/v1/ai.py`
- Tests: `backend/tests/test_services/test_ai_service.py`

### Learnings from Previous Story

**From Story P3-3.5 (Status: done)**

- **Fallback Chain Implemented**: Full fallback chain (video_native -> multi_frame -> single_frame) exists in `ProtectEventHandler._submit_to_ai_pipeline()`
- **Video Native Stub**: `_try_video_native_analysis()` currently always returns None with reason "provider_unsupported" - this story enables proper provider detection
- **Fallback Tracking**: Uses `_fallback_chain` list to accumulate failures, joined with commas for `fallback_reason` field
- **Implementation Location**: Fallback chain is in `protect_event_handler.py`, not `event_processor.py`
- **Non-Protect Bypass**: RTSP/USB cameras bypass fallback chain entirely (no clips available)

**Backend Support Already Exists (from prior stories):**
- ClipService for downloading Protect video clips [P3-1.1 - P3-1.4]
- FrameExtractor for extracting frames from clips [P3-2.1, P3-2.2]
- AIService.describe_images() for multi-image analysis [P3-2.3]
- Multi-frame prompts [P3-2.4]
- Multi-frame integration in pipeline [P3-2.6]
- Camera.analysis_mode field [P3-3.1]
- Full fallback chain with tracking [P3-3.5]

[Source: docs/sprint-artifacts/p3-3-5-implement-automatic-fallback-chain.md#Dev-Agent-Record]

### Technical Notes from Epic

- Add `PROVIDER_CAPABILITIES` constant to ai_service.py
- Structure: `{"openai": {"video": True, "max_video_duration": 60, "max_video_size_mb": 20}}`
- Check capabilities before attempting video analysis
- Update as provider capabilities change
- OpenAI and Gemini support video; Claude and Grok do not (as of late 2025)

### Key Implementation Considerations

1. **Capability vs Configuration**: Capabilities are static (provider supports video), but availability depends on API key configuration
2. **Future-Proofing**: Structure allows easy addition of new capabilities (audio, documents, etc.)
3. **Runtime Filtering**: `get_video_capable_providers()` should only return providers that both support video AND have configured API keys
4. **Logging**: Clear logging when providers are skipped helps debugging fallback issues

### Provider Video Support (Current Knowledge)

| Provider | Video Support | Max Duration | Max Size | Notes |
|----------|--------------|--------------|----------|-------|
| OpenAI GPT-4o | Yes | 60s | 20MB | Base64 or file upload |
| Claude | No | - | - | Images only |
| Gemini 1.5 | Yes | 60s | 20MB | File API or inline |
| Grok | No | - | - | Images only (TBD) |

### References

- [Source: docs/epics-phase3.md#Story-P3-4.1]
- [Source: docs/architecture.md#AI-Service]
- [Source: backend/app/services/ai_service.py]
- [Source: backend/app/services/protect_event_handler.py]
- [Source: docs/sprint-artifacts/p3-3-5-implement-automatic-fallback-chain.md]

## Dev Agent Record

### Context Reference

- `docs/sprint-artifacts/p3-4-1-add-provider-video-capability-detection.context.xml`

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Added `PROVIDER_CAPABILITIES` constant to `ai_service.py` (lines 82-118) with video/max_duration/max_size/formats/max_images for all 4 providers
- Implemented 6 capability methods on AIService class (lines 2266-2395):
  - `get_provider_capabilities(provider: str) -> dict`
  - `supports_video(provider: str) -> bool`
  - `get_video_capable_providers() -> list[str]`
  - `get_max_video_duration(provider: str) -> int`
  - `get_max_video_size(provider: str) -> int`
  - `get_all_capabilities() -> dict` (includes configured flag)
- Modified `_try_video_native_analysis()` in `protect_event_handler.py` to check video capability before attempting
- New fallback reasons: "no_video_providers_available" when no video providers configured, "video_upload_not_implemented" when providers exist but upload not yet done
- Added `GET /api/v1/ai/capabilities` endpoint with `AICapabilitiesResponse` schema
- Added 28 new tests across `test_ai_service.py` and `test_api/test_ai.py`
- Updated existing fallback chain tests to use flexible reason matching

### File List

**Modified:**
- `backend/app/services/ai_service.py` - Added PROVIDER_CAPABILITIES and capability methods
- `backend/app/services/protect_event_handler.py` - Video capability check in fallback chain
- `backend/app/api/v1/ai.py` - New /capabilities endpoint
- `backend/app/schemas/ai.py` - Added ProviderCapability and AICapabilitiesResponse schemas
- `backend/tests/test_services/test_ai_service.py` - 23 new capability tests
- `backend/tests/test_api/test_ai.py` - 5 new endpoint tests
- `backend/tests/test_services/test_fallback_chain.py` - Updated for new reason format
- `backend/tests/test_integration/test_multi_frame_analysis.py` - Updated for new reason format

## Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2025-12-06 | 1.0 | Story drafted from epics-phase3.md with context from P3-3.5 |
| 2025-12-06 | 2.0 | Implementation complete: capability detection, API endpoint, fallback integration, 28 tests |
