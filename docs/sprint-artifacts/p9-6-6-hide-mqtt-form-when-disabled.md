# Story P9-6.6: Hide MQTT Form When Disabled

Status: done

## Story

As a **user managing integrations**,
I want **the MQTT configuration form to be hidden when the integration is disabled**,
So that **I see a clean interface with only relevant options visible**.

## Acceptance Criteria

1. **AC-6.6.1:** Given MQTT integration is disabled, when I view Settings > Integrations, then only the enable toggle is visible

2. **AC-6.6.2:** Given MQTT is disabled, when I view Settings > Integrations, then configuration fields are hidden

3. **AC-6.6.3:** Given I enable MQTT integration, when the toggle turns on, then the configuration form appears with animation

4. **AC-6.6.4:** Given I toggle MQTT off, when form hides, then form values are preserved (not reset)

## Tasks / Subtasks

- [x] Task 1: Audit current MQTT form visibility behavior (AC: 1-4)
  - [x] Found: Info Alert was always visible outside collapsible section
  - [x] Found: Save Button was always visible outside collapsible section
  - [x] Existing: Form values already preserved with current implementation

- [x] Task 2: Hide Info Alert when MQTT is disabled (AC: 1, 2)
  - [x] Moved Info Alert inside the collapsible `overflow-hidden` div
  - [x] Alert now animates with other form elements using grid-rows transition

- [x] Task 3: Hide Save Button when MQTT is disabled (AC: 1, 2)
  - [x] Added conditional rendering: show when `enabled || isDirty`
  - [x] Button visible when MQTT enabled OR when user has made changes

- [x] Task 4: Verify animation and value preservation (AC: 3, 4)
  - [x] Toggle animation uses existing CSS transition (duration-300 ease-in-out)
  - [x] Form values persist via react-hook-form state management

- [x] Task 5: Build and verify (AC: 1-4)
  - [x] Frontend build successful
  - [x] Updated test to reflect new behavior
  - [x] All 46 MQTT tests pass

## Dev Notes

### Architecture Alignment

From tech-spec-epic-P9-6.md:
- Component: `frontend/components/settings/MQTTSettings.tsx`
- Conditional visibility of form fields based on enabled state

### Current Implementation

The MQTTSettings component already has:
- Collapsible form sections using CSS grid transition (lines 324-331)
- `grid-rows-[0fr] opacity-0` when disabled, `grid-rows-[1fr] opacity-100` when enabled
- Smooth transition with `duration-300 ease-in-out`

### Issues to Fix

1. **Info Alert** (lines 683-692) is always visible - should be hidden when disabled
2. **Save Button** (lines 694-710) is always visible - should only show when enabled

### Implementation Approach

Move the Info Alert and Save Button inside the collapsible section, or wrap them in their own conditional visibility wrapper.

### References

- [Source: docs/sprint-artifacts/tech-spec-epic-P9-6.md#P9-6.6] - Acceptance criteria
- [Source: frontend/components/settings/MQTTSettings.tsx] - Component to modify

## Dev Agent Record

### Context Reference

- Inline context (simple change)

### Agent Model Used

Claude Opus 4.5

### Debug Log References

- Frontend build: compiled successfully in ~5s
- TypeScript check: passed
- Tests: 46 passed in MQTTSettings.test.tsx

### Completion Notes List

- Moved Info Alert inside the collapsible section so it hides with animation
- Added conditional visibility to Save Button: `(form.watch('enabled') || isDirty)`
- Updated test from "always shows Save button" to "hides Save button when disabled"
- All acceptance criteria verified:
  - AC-6.6.1: Only enable toggle visible when disabled (Info Alert and Save hidden)
  - AC-6.6.2: Configuration fields hidden using existing CSS grid transition
  - AC-6.6.3: Form appears with animation (grid-rows-[1fr] opacity-100 transition)
  - AC-6.6.4: Form values preserved via react-hook-form state management

### File List

MODIFIED:
- frontend/components/settings/MQTTSettings.tsx
- frontend/__tests__/components/settings/MQTTSettings.test.tsx

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-23 | Story drafted from Epic P9-6 and tech spec |
| 2025-12-23 | Story implementation complete - hide Info Alert and Save Button when MQTT disabled |
