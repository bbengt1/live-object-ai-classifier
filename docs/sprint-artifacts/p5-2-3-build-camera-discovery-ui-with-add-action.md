# Story P5-2.3: Build Camera Discovery UI with Add Action

**Epic:** P5-2 ONVIF Camera Discovery
**Status:** done
**Created:** 2025-12-14
**Story Key:** p5-2-3-build-camera-discovery-ui-with-add-action

---

## User Story

**As a** homeowner setting up ArgusAI,
**I want** a "Discover Cameras" button that scans my network and shows found cameras,
**So that** I can add ONVIF cameras with one click instead of manually entering RTSP URLs.

---

## Background & Context

This story creates the frontend UI for ONVIF camera discovery, building on the backend services implemented in P5-2.1 (WS-Discovery) and P5-2.2 (device details). The discovery UI provides a seamless experience for non-technical users who don't know their camera's RTSP URL.

**What this story delivers:**
1. CameraDiscovery.tsx component with "Discover Cameras" button
2. Loading state during network scan (up to 10 seconds)
3. List of discovered cameras with name, IP, manufacturer
4. "Add" button that opens CameraForm with pre-populated RTSP URL
5. API client functions for ONVIF discovery endpoints
6. Integration into the Cameras page
7. Empty state when no cameras found

**Dependencies:**
- P5-2.1 completed: WS-Discovery endpoints available
- P5-2.2 completed: Device details endpoints available

**PRD Reference:** docs/PRD-phase5.md (FR16, FR19)
**Architecture Reference:** docs/architecture/phase-5-additions.md (ONVIF Discovery Architecture)
**Tech Spec Reference:** docs/sprint-artifacts/tech-spec-epic-p5-2.md (Story P5-2.3)

---

## Acceptance Criteria

### AC1: "Discover Cameras" Button Visible on Cameras Page
- [ ] Button visible in the cameras page header area
- [ ] Button styled consistently with other action buttons
- [ ] Button includes a scan/search icon (e.g., Radar or Search icon)
- [ ] Button disabled during active scan with loading indicator

### AC2: Loading Spinner/State Shown During Discovery
- [ ] Clicking "Discover Cameras" shows loading spinner on button
- [ ] Loading text changes to "Scanning..." or similar
- [ ] Discovery can take up to 10 seconds (timeout)
- [ ] Progress indication (optional: elapsed time)
- [ ] User can continue viewing existing cameras during scan

### AC3: Discovered Cameras Listed with Name, IP, Manufacturer
- [ ] Results displayed in a card/list format
- [ ] Each discovered camera shows: device name, IP address, manufacturer
- [ ] Model number displayed if available
- [ ] Stream profiles listed with resolution/FPS
- [ ] Cameras already in ArgusAI marked as "Already Added"

### AC4: "Add" Button Opens Camera Form with Pre-populated RTSP URL
- [ ] Each discovered camera card has "Add" button
- [ ] Clicking "Add" navigates to /cameras/new with pre-filled data
- [ ] RTSP URL pre-populated from discovery (primary stream)
- [ ] Camera name pre-populated from device name
- [ ] Username/password fields empty (user must enter)
- [ ] Option to select different stream profile before adding

### AC5: Manual RTSP Entry Still Available
- [ ] Existing "Add Camera" button/dropdown still functional
- [ ] Users can bypass discovery and enter RTSP URL manually
- [ ] Discovery is optional, not required for adding cameras

### AC6: Empty State Message if No Cameras Found
- [ ] Empty state displayed if discovery returns 0 devices
- [ ] Message explains possible reasons (no ONVIF cameras, network issues)
- [ ] Provides guidance on manual entry alternative
- [ ] Option to retry scan

---

## Tasks / Subtasks

### Task 1: Add API Client Functions for Discovery (AC: 1, 2, 3)
**File:** `frontend/lib/api-client.ts`
- [x] Add `discovery.getStatus()` to check if ONVIF discovery is available
- [x] Add `discovery.startScan(timeout?: number)` to trigger discovery
- [x] Add `discovery.getDeviceDetails(endpointUrl, credentials?)` for device info
- [x] Add `discovery.clearCache()` to force fresh scan
- [x] Add TypeScript interfaces for discovery schemas
- [x] Handle 503 errors (library not installed)

### Task 2: Create DiscoveredCameraCard Component (AC: 3, 4)
**File:** `frontend/components/cameras/DiscoveredCameraCard.tsx`
- [x] Display device info (name, manufacturer, model, IP)
- [x] Show stream profiles with resolution/FPS badges
- [x] "Add" button with primary styling
- [x] "Already Added" badge if camera exists in ArgusAI
- [x] Profile selector dropdown if multiple profiles available
- [x] Loading state while fetching device details

### Task 3: Create CameraDiscovery Component (AC: 1, 2, 3, 6)
**File:** `frontend/components/cameras/CameraDiscovery.tsx`
- [x] "Discover Cameras" button with Radar/Search icon
- [x] Loading state with spinner during scan
- [x] Results list using DiscoveredCameraCard
- [x] Empty state with helpful message
- [x] Error state with retry option
- [x] Collapsible/expandable results panel
- [x] Auto-fetch device details for discovered devices

### Task 4: Integrate Discovery into Cameras Page (AC: 1, 5)
**File:** `frontend/app/cameras/page.tsx`
- [x] Add CameraDiscovery component below page header
- [x] Position alongside existing AddCameraDropdown
- [x] Ensure discovery doesn't interfere with existing functionality
- [x] Pass camera list to discovery for "Already Added" detection

### Task 5: Add URL Query Params for Pre-populated Form (AC: 4)
**File:** `frontend/app/cameras/new/page.tsx`
- [x] Read query params: rtsp_url, name, username (optional)
- [x] Pre-populate CameraForm with values from URL
- [x] Clear query params after form loads
- [x] Handle URL encoding for special characters

### Task 6: Add Discovery Types to Camera Types (AC: 3)
**File:** `frontend/types/camera.ts` or `frontend/types/discovery.ts`
- [x] Add `DiscoveredDevice` interface
- [x] Add `StreamProfile` interface
- [x] Add `DeviceInfo` interface
- [x] Add `DiscoveredCameraDetails` interface
- [x] Add `DiscoveryResponse` interface
- [x] Add `DeviceDetailsResponse` interface

### Task 7: Write Component Tests (AC: 1, 2, 3, 6)
**File:** `frontend/__tests__/components/cameras/CameraDiscovery.test.tsx`
- [x] Test "Discover Cameras" button renders
- [x] Test loading state during scan
- [x] Test discovered cameras list renders
- [x] Test empty state renders when no cameras found
- [x] Test error state and retry functionality
- [x] Mock API responses for all test cases

---

## Dev Notes

### API Integration Pattern

Use TanStack Query for data fetching with the existing patterns:

```typescript
// Example usage in CameraDiscovery component
import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

// Check if discovery is available
const { data: status } = useQuery({
  queryKey: ['discovery', 'status'],
  queryFn: () => apiClient.discovery.getStatus(),
});

// Trigger discovery scan
const discoverMutation = useMutation({
  mutationFn: (timeout?: number) => apiClient.discovery.startScan(timeout),
  onSuccess: (data) => {
    // Handle discovered devices
  },
});
```

### Pre-populating CameraForm via URL

Navigate to camera form with query params:

```typescript
// In DiscoveredCameraCard
const handleAddCamera = () => {
  const params = new URLSearchParams({
    rtsp_url: camera.primary_rtsp_url,
    name: camera.device_info.name,
  });
  router.push(`/cameras/new?${params.toString()}`);
};
```

### "Already Added" Detection

Compare discovered camera IP with existing cameras:

```typescript
const isAlreadyAdded = (discoveredIp: string, cameras: ICamera[]) => {
  return cameras.some((cam) => {
    if (cam.rtsp_url) {
      const url = new URL(cam.rtsp_url);
      return url.hostname === discoveredIp;
    }
    return false;
  });
};
```

### Learnings from Previous Story

**From Story P5-2.2 (Status: done)**

- **Device details endpoint** - Use `POST /api/v1/cameras/discover/device` with endpoint URL
- **Two-step discovery** - First get basic devices (fast), then fetch details per device
- **Error handling** - Service returns `status: 'auth_required'` if credentials needed
- **IP extraction** - Backend extracts IP from endpoint URL, available in response

[Source: docs/sprint-artifacts/p5-2-2-parse-onvif-device-info-and-capabilities.md#Dev-Agent-Record]

### Project Structure Notes

**Files to create:**
- `frontend/components/cameras/CameraDiscovery.tsx` - Main discovery component
- `frontend/components/cameras/DiscoveredCameraCard.tsx` - Individual camera card
- `frontend/types/discovery.ts` - TypeScript interfaces
- `frontend/__tests__/components/cameras/CameraDiscovery.test.tsx` - Tests

**Files to modify:**
- `frontend/lib/api-client.ts` - Add discovery API functions
- `frontend/app/cameras/page.tsx` - Integrate discovery component
- `frontend/app/cameras/new/page.tsx` - Handle URL query params

### UI Design Guidelines

Follow existing component patterns:
- Use shadcn/ui components (Button, Card, Badge, Skeleton)
- Use Lucide icons (Radar, Search, RefreshCw, Plus)
- Match existing card styling from CameraPreview
- Use consistent spacing and typography

### Error Handling

| Error Type | User Message | Action |
|------------|--------------|--------|
| Discovery unavailable (503) | "Camera discovery unavailable. Install WSDiscovery package on server." | Show info, suggest manual entry |
| Network error | "Discovery failed. Check your network connection." | Retry button |
| No devices found | "No ONVIF cameras found on your network." | Guidance + manual entry link |
| Timeout | "Discovery timed out. Some devices may not have responded." | Show partial results + retry |

### References

- [Source: docs/PRD-phase5.md#Functional-Requirements] - FR16, FR19
- [Source: docs/architecture/phase-5-additions.md#Phase-5-ONVIF-Discovery-Architecture] - UI components
- [Source: docs/sprint-artifacts/tech-spec-epic-p5-2.md#Acceptance-Criteria] - P5-2.3 criteria
- [Source: docs/epics-phase5.md#Epic-P5-2] - Story P5-2.3 acceptance criteria
- [Source: docs/sprint-artifacts/p5-2-2-parse-onvif-device-info-and-capabilities.md] - Previous story

---

## Dev Agent Record

### Context Reference

- [docs/sprint-artifacts/p5-2-3-build-camera-discovery-ui-with-add-action.context.xml](p5-2-3-build-camera-discovery-ui-with-add-action.context.xml)

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

**Implementation Summary:**
- Created full ONVIF camera discovery UI with "Discover Cameras" button
- CameraDiscovery component handles scan lifecycle (idle → scanning → results/error/empty)
- DiscoveredCameraCard displays device info, stream profiles, and "Add" action
- API client extended with 4 discovery functions matching backend endpoints
- Pre-population flow: clicking "Add" navigates to /cameras/new with ?rtsp_url=...&name=... query params
- New camera page reads query params and pre-populates CameraForm
- 17 test cases covering all component states and interactions

**Technical Decisions:**
- Used TanStack Query (useQuery/useMutation) for API calls
- Two-step discovery: first quick scan, then fetch details per device
- "Already Added" detection compares IP addresses from RTSP URLs
- Collapsible results panel with count badge for better UX
- Suspense boundary on /cameras/new page for useSearchParams

### File List

**New Files:**
- `frontend/types/discovery.ts` - TypeScript interfaces for ONVIF discovery API
- `frontend/components/cameras/CameraDiscovery.tsx` - Main discovery component with scan button and results
- `frontend/components/cameras/DiscoveredCameraCard.tsx` - Individual camera card with "Add" action
- `frontend/__tests__/components/cameras/CameraDiscovery.test.tsx` - 17 test cases for discovery component

**Modified Files:**
- `frontend/lib/api-client.ts` - Added discovery API functions (getStatus, startScan, getDeviceDetails, clearCache)
- `frontend/app/cameras/page.tsx` - Integrated CameraDiscovery component
- `frontend/app/cameras/new/page.tsx` - Added URL query param handling for pre-population from discovery

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-14 | SM Agent (Claude Opus 4.5) | Initial story creation via create-story workflow |
| 2025-12-14 | Dev Agent (Claude Opus 4.5) | Implementation complete - all 7 tasks done, 17 tests passing |
| 2025-12-14 | Reviewer (Claude Opus 4.5) | Senior Developer Review - APPROVED |

---

## Senior Developer Review (AI)

### Reviewer
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Date
2025-12-14

### Outcome: APPROVE

All acceptance criteria have been fully implemented with comprehensive test coverage. The implementation follows existing patterns in the codebase and provides a polished user experience for ONVIF camera discovery.

### Summary

The implementation delivers a complete ONVIF camera discovery UI with:
- "Discover Cameras" button with proper loading states
- Two-step discovery flow (scan → fetch details per device)
- Comprehensive error handling and empty states
- Pre-population of camera form via URL query parameters
- 17 passing component tests
- Clean, well-documented code following project conventions

### Key Findings

**No HIGH or MEDIUM severity issues found.**

**LOW Severity:**
- Note: Consider adding debounce to prevent rapid-fire discovery scans if button is clicked multiple times quickly (enhancement, not required)

### Acceptance Criteria Coverage

| AC# | Description | Status | Evidence |
|-----|-------------|--------|----------|
| AC1 | "Discover Cameras" button visible with icon, disabled during scan | IMPLEMENTED | CameraDiscovery.tsx:208-229, :210 disabled prop |
| AC2 | Loading spinner shown during discovery (up to 10s) | IMPLEMENTED | CameraDiscovery.tsx:251-264, :154 timeout=10 |
| AC3 | Discovered cameras show name/IP/manufacturer, profiles with res/FPS, "Already Added" | IMPLEMENTED | DiscoveredCameraCard.tsx:118-188, :128-133 badge |
| AC4 | "Add" button opens form with pre-populated RTSP URL and name | IMPLEMENTED | DiscoveredCameraCard.tsx:101-106, cameras/new/page.tsx:32-79 |
| AC5 | Manual RTSP entry still available | IMPLEMENTED | cameras/page.tsx:118 AddCameraDropdown unchanged |
| AC6 | Empty state with guidance and retry | IMPLEMENTED | CameraDiscovery.tsx:292-319 |

**Summary: 6 of 6 acceptance criteria fully implemented**

### Task Completion Validation

| Task | Marked As | Verified As | Evidence |
|------|-----------|-------------|----------|
| Task 1: API Client Functions | Complete | ✅ VERIFIED | api-client.ts:2020-2068, 4 functions added |
| Task 2: DiscoveredCameraCard | Complete | ✅ VERIFIED | DiscoveredCameraCard.tsx:1-253, all subtasks done |
| Task 3: CameraDiscovery Component | Complete | ✅ VERIFIED | CameraDiscovery.tsx:1-428, all subtasks done |
| Task 4: Integration into Cameras Page | Complete | ✅ VERIFIED | cameras/page.tsx:17 import, :121-134 component |
| Task 5: URL Query Params | Complete | ✅ VERIFIED | cameras/new/page.tsx:32-79, Suspense wrapper |
| Task 6: Discovery Types | Complete | ✅ VERIFIED | types/discovery.ts:1-165, 7 interfaces |
| Task 7: Component Tests | Complete | ✅ VERIFIED | CameraDiscovery.test.tsx, 17 test cases pass |

**Summary: 7 of 7 completed tasks verified, 0 questionable, 0 false completions**

### Test Coverage and Gaps

**Covered:**
- Initial render tests (button, title, description)
- Discovery unavailable state (disabled button, warning message)
- Scanning state (loading spinner, progress message)
- Discovery results (camera list, device details)
- "Already Added" badge detection
- Empty state (no cameras found, guidance, retry/manual links)
- Error state (failed discovery, retry functionality)
- Rescan functionality

**Gaps:**
- No tests for profile selector interaction (LOW priority)
- No tests for pre-population in new camera page (could add integration test)

### Architectural Alignment

✅ Uses TanStack Query for data fetching (consistent with project patterns)
✅ Uses shadcn/ui components (Button, Badge, Select)
✅ Uses Lucide icons (Radar, RefreshCw, AlertCircle, etc.)
✅ Follows existing component file structure
✅ TypeScript interfaces mirror backend Pydantic schemas
✅ Proper error handling for 503 responses

### Security Notes

- No security concerns identified
- URL query params are properly encoded/decoded
- No sensitive data exposed in URL (username/password not included)

### Best-Practices and References

- [TanStack Query v5 docs](https://tanstack.com/query/latest)
- [Next.js App Router useSearchParams](https://nextjs.org/docs/app/api-reference/functions/use-search-params)
- [Vitest Testing Library](https://vitest.dev/)

### Action Items

**Advisory Notes:**
- Note: Consider adding rate limiting/debounce on discovery button for UX polish (not required)
- Note: Profile selector tests could be added in future iteration
