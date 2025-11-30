# Story P2-1.3: Build Controller Configuration UI in Settings Page

Status: done

## Story

As a **user**,
I want **a form in Settings to add and configure my UniFi Protect controller**,
so that **I can connect my Protect system through the dashboard**.

## Acceptance Criteria

| # | Criteria | Verification |
|---|----------|--------------|
| AC1 | Settings page has a "UniFi Protect" section/tab that displays the Protect configuration area | Manual UI test |
| AC2 | Empty state shows "Connect your UniFi Protect controller to auto-discover cameras" message with "Add Controller" button when no controller is configured | Manual UI test |
| AC3 | Controller form includes: Name (text, required), Host/IP (text, required), Username (text, required), Password (password, required), Verify SSL (checkbox, default unchecked) | Manual UI test |
| AC4 | "Test Connection" button calls `POST /api/v1/protect/controllers/test` and shows success (green checkmark + firmware version) or error (red X + error message) | API integration test |
| AC5 | "Save" button calls `POST /api/v1/protect/controllers` to create controller, shows success toast, and displays saved controller info | API integration test |
| AC6 | Connection status indicator shows: Green dot + "Connected" (when connected), Yellow dot + "Connecting..." with spinner (during connection), Red dot + "Connection Error" with tooltip (on error), Gray dot + "Not configured" (when no controller) | Manual UI test |
| AC7 | Form validation: Host required with valid format, Username required (min 1 char), Password required (min 1 char), real-time validation on blur | Manual UI test |
| AC8 | Responsive layout: Full width on mobile (<640px), two-column layout on desktop (form left, status right) | Manual UI test |
| AC9 | Toast notifications display for success ("Controller saved successfully") and errors ("Failed to save controller: {message}") | Manual UI test |
| AC10 | TanStack Query mutation handles loading states and error states correctly | Code review |

## Tasks / Subtasks

- [x] **Task 1: Create UniFi Protect Settings Section** (AC: 1, 2)
  - [x] 1.1 Add "UniFi Protect" tab/section to existing Settings page
  - [x] 1.2 Create empty state component with message and "Add Controller" button
  - [x] 1.3 Implement section header "UniFi Protect Integration"

- [x] **Task 2: Build ControllerForm Component** (AC: 3, 7)
  - [x] 2.1 Create `frontend/components/protect/ControllerForm.tsx`
  - [x] 2.2 Add Name field (text input, placeholder: "Home UDM Pro", required)
  - [x] 2.3 Add Host/IP field (text input, placeholder: "192.168.1.1 or unifi.local", required)
  - [x] 2.4 Add Username field (text input, required)
  - [x] 2.5 Add Password field (password input, required)
  - [x] 2.6 Add Verify SSL checkbox (default: unchecked, helper text about SSL certificates)
  - [x] 2.7 Implement form validation with Zod schema (on blur validation)
  - [x] 2.8 Use React Hook Form for form state management

- [x] **Task 3: Implement Test Connection Feature** (AC: 4)
  - [x] 3.1 Add "Test Connection" button (accent cyan color)
  - [x] 3.2 Create TanStack Query mutation for `POST /api/v1/protect/controllers/test`
  - [x] 3.3 Show loading spinner on button during test
  - [x] 3.4 Display success state: green checkmark + "Connected successfully" + firmware version
  - [x] 3.5 Display error state: red X + specific error message (auth failed, unreachable, SSL error, timeout)
  - [x] 3.6 Disable Save button until test passes

- [x] **Task 4: Implement Save Controller Feature** (AC: 5, 9)
  - [x] 4.1 Add "Save" button (primary slate color)
  - [x] 4.2 Create TanStack Query mutation for `POST /api/v1/protect/controllers`
  - [x] 4.3 Show loading state on Save button during API call
  - [x] 4.4 Display success toast notification on successful save
  - [x] 4.5 Display error toast notification with API error message on failure
  - [x] 4.6 After successful save, transition to "controller configured" view

- [x] **Task 5: Build ConnectionStatus Component** (AC: 6)
  - [x] 5.1 Create `frontend/components/protect/ConnectionStatus.tsx`
  - [x] 5.2 Implement "Not configured" state (gray dot)
  - [x] 5.3 Implement "Connecting..." state (yellow dot + spinner)
  - [x] 5.4 Implement "Connected" state (green dot + text)
  - [x] 5.5 Implement "Connection Error" state (red dot + tooltip with error details)
  - [x] 5.6 Add ARIA live region for status change announcements (accessibility)

- [x] **Task 6: Implement Responsive Layout** (AC: 8)
  - [x] 6.1 Full-width form layout for mobile (<640px)
  - [x] 6.2 Two-column layout for desktop: form (left), status (right)
  - [x] 6.3 Use Tailwind responsive classes (sm:, md:, lg:)
  - [x] 6.4 Test on various screen sizes

- [x] **Task 7: Add API Client Functions** (AC: 4, 5, 10)
  - [x] 7.1 Add `testProtectController(data)` function to `frontend/lib/api-client.ts`
  - [x] 7.2 Add `createProtectController(data)` function to `frontend/lib/api-client.ts`
  - [x] 7.3 Add `getProtectControllers()` function to `frontend/lib/api-client.ts`
  - [x] 7.4 Define TypeScript types for Protect controller in `frontend/types/protect.ts`

- [x] **Task 8: Integration and Testing** (AC: all)
  - [x] 8.1 Integrate all components in Settings page
  - [x] 8.2 Test form validation scenarios
  - [x] 8.3 Test connection test flow (success and failure cases)
  - [x] 8.4 Test save controller flow
  - [x] 8.5 Test responsive behavior
  - [x] 8.6 Verify accessibility (keyboard navigation, screen reader)

## Dev Notes

### Architecture Patterns

**Frontend Component Pattern** (from CLAUDE.md):
- Components in `frontend/components/` organized by feature
- Hooks in `frontend/hooks/`
- Use shadcn/ui components for forms (Input, Button, Switch, Card)
- TanStack Query for server state management
- Zod validation with React Hook Form

**API Response Format** (from architecture.md):
```typescript
{
  data: {...},  // Single object or list
  meta: {
    request_id: "uuid",
    timestamp: "ISO8601"
  }
}
```

### UX Specifications (from ux-design-specification.md Section 10.2)

**Form Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ UniFi Protect Integration                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Controller Connection                    [Status Indicator] │
│ ─────────────────────────────────────────────────────────── │
│                                                             │
│ Name:        [________________________]                     │
│ Host/IP:     [________________________]                     │
│ Username:    [________________________]                     │
│ Password:    [________________________]                     │
│ ☐ Verify SSL certificates                                  │
│                                                             │
│ [Test Connection]              [Save]                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Button Hierarchy** (from UX spec 7.1):
- Primary (Save): Slate background (#475569), white text
- Accent (Test Connection): Cyan background (#0ea5e9), white text
- Secondary (Cancel): White background, slate border/text

**Form Patterns** (from UX spec 7.1):
- Label position: Above input field
- Required indicator: Asterisk (*) next to label
- Validation timing: onBlur for fields
- Error display: Inline below field (red text + red border)

**Connection Status States:**
- Connected: Green dot (#22c55e) + "Connected" text
- Connecting: Yellow dot (#f97316) + "Connecting..." + spinner
- Error: Red dot (#ef4444) + "Connection Error" + tooltip
- Not configured: Gray dot (#94a3b8) + "Not configured"

### API Endpoints (from P2-1.2)

**Test Connection:**
- `POST /api/v1/protect/controllers/test`
- Request: `{ host, port, username, password, verify_ssl }`
- Success: `{ data: { success: true, message: "...", firmware_version: "X.X.X", camera_count: N } }`
- Errors: 401 (auth), 502 (SSL), 503 (unreachable), 504 (timeout)

**Create Controller:**
- `POST /api/v1/protect/controllers`
- Request: `{ name, host, port, username, password, verify_ssl }`
- Response: `{ data: ProtectController, meta: {...} }`

**Get Controllers:**
- `GET /api/v1/protect/controllers`
- Response: `{ data: ProtectController[], meta: { count: N, ... } }`

### Project Structure Notes

**Files to create:**
- `frontend/components/protect/ControllerForm.tsx`
- `frontend/components/protect/ConnectionStatus.tsx`
- `frontend/components/protect/index.ts` (exports)
- `frontend/types/protect.ts`

**Files to modify:**
- `frontend/app/settings/page.tsx` - Add UniFi Protect section
- `frontend/lib/api-client.ts` - Add Protect API functions

### References

- [Source: docs/ux-design-specification.md#Section-10.2] - UniFi Protect UI wireframes
- [Source: docs/architecture.md#Phase-2-API-Contracts] - API specifications
- [Source: docs/epics-phase2.md#Story-1.3] - Acceptance criteria
- [Source: docs/PRD-phase2.md] - FR1, FR6, FR7 requirements

### Learnings from Previous Stories

**From Story P2-1.1 (Status: done)**
- ProtectController model at `backend/app/models/protect_controller.py`
- CRUD API endpoints at `backend/app/api/v1/protect.py`
- Response schemas use `{ data, meta }` format
- Password is write-only (not returned in API responses)

**From Story P2-1.2 (Status: done)**
- Test endpoint at `POST /api/v1/protect/controllers/test`
- Test for existing controller at `POST /api/v1/protect/controllers/{id}/test`
- Returns `{ success, message, firmware_version, camera_count }` on success
- Error types: auth_error (401), ssl_error (502), connection_error (503), timeout (504)
- Connection test has 10-second timeout
- Credentials not logged for security

[Source: docs/sprint-artifacts/p2-1-1-create-protect-controller-database-model-and-api-endpoints.md#Dev-Agent-Record]
[Source: docs/sprint-artifacts/p2-1-2-implement-controller-connection-validation-and-test-endpoint.md#Dev-Agent-Record]

## Dev Agent Record

### Context Reference

- [p2-1-3-build-controller-configuration-ui-in-settings-page.context.xml](./p2-1-3-build-controller-configuration-ui-in-settings-page.context.xml)

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Build completed successfully with `npm run build`
- Lint passed with 0 errors (pre-existing warnings in other files)
- All 8 tasks completed with 38 subtasks

### Completion Notes List

- Created new Protect tab in Settings page with Shield icon
- Implemented ControllerForm component with all form fields (Name, Host, Username, Password, Port, Verify SSL)
- Implemented ConnectionStatus component with 4 states (not_configured, connecting, connected, error)
- Added full protect namespace to API client with testConnection, createController, listControllers, getController, testExistingController, deleteController
- Created TypeScript types for all Protect-related interfaces
- Implemented responsive layout with two-column on desktop (>640px) and single column on mobile
- Added Zod validation with onBlur mode
- TanStack Query mutations handle loading states, success toasts, and error messages
- Form resets connection test status when fields change (security/UX pattern)
- Added ARIA live region for accessibility
- Fixed pre-existing TypeScript issue in RuleFormDialog.tsx (zodResolver type compatibility)

### File List

**Created:**
- frontend/components/protect/ControllerForm.tsx
- frontend/components/protect/ConnectionStatus.tsx
- frontend/components/protect/index.ts
- frontend/types/protect.ts

**Modified:**
- frontend/app/settings/page.tsx (added Protect tab)
- frontend/lib/api-client.ts (added protect namespace)
- frontend/components/rules/RuleFormDialog.tsx (fixed pre-existing TS error)

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-11-30 | Story drafted from epics-phase2.md | SM Agent |
| 2025-11-30 | Story context generated, status → ready-for-dev | SM Agent |
| 2025-11-30 | Implementation complete - all 8 tasks done, build and lint pass | Dev Agent |
| 2025-11-30 | Code review approved, status → done | Code Review Agent |

## Code Review Record

### Review Date
2025-11-30

### Reviewer
Code Review Agent (Claude Opus 4.5)

### Review Outcome
**APPROVED** ✅

### Acceptance Criteria Validation

| # | Criteria | Evidence | Status |
|---|----------|----------|--------|
| AC1 | Settings page has "UniFi Protect" section/tab | `settings/page.tsx:320-323` - Tab with Shield icon | ✅ PASS |
| AC2 | Empty state with "Add Controller" button | `settings/page.tsx:946-958` - Empty state UI | ✅ PASS |
| AC3 | Form fields (Name, Host, Username, Password, Verify SSL) | `ControllerForm.tsx:234-337` - All fields present | ✅ PASS |
| AC4 | "Test Connection" calls POST /api/v1/protect/controllers/test | `ControllerForm.tsx:97-153` - testConnectionMutation | ✅ PASS |
| AC5 | "Save" calls POST /api/v1/protect/controllers + toast | `ControllerForm.tsx:156-184` - saveControllerMutation | ✅ PASS |
| AC6 | Connection status indicator (4 states) | `ConnectionStatus.tsx:30-51` - green/yellow/red/gray | ✅ PASS |
| AC7 | Form validation with onBlur | `ControllerForm.tsx:72-83` - Zod + mode: 'onBlur' | ✅ PASS |
| AC8 | Responsive layout | `settings/page.tsx:910` - sm:grid sm:grid-cols-2 | ✅ PASS |
| AC9 | Toast notifications | `ControllerForm.tsx:119,123,151,168,182` | ✅ PASS |
| AC10 | TanStack Query mutation states | `ControllerForm.tsx:209-211` - isPending, canSave | ✅ PASS |

### Build Verification
- **Build**: ✅ PASS (0 errors)
- **Lint**: ✅ PASS (0 errors, 5 pre-existing warnings)

### Code Quality Assessment

**Strengths:**
- Clean component separation (ControllerForm, ConnectionStatus)
- Comprehensive TypeScript types in `frontend/types/protect.ts`
- Proper ApiError handling with user-friendly messages
- ARIA live region for accessibility
- Form state properly resets test status on field changes
- Follows existing patterns from CameraForm and Settings page

**Minor Observations:**
- React Compiler warning on form.watch() is expected (React Hook Form limitation)
- No new lint errors introduced

### Security Review
- ✅ Password field uses type="password"
- ✅ Credentials not logged
- ✅ Backend encrypts stored passwords (existing pattern)

### Risk Assessment
- **LOW RISK** - Additive frontend changes only, no breaking changes
