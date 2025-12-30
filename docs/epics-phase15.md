# ArgusAI Phase 15 - Epic Breakdown

**Author:** Brent
**Date:** 2025-12-30
**Project Level:** Brownfield (existing production system)
**Target Scale:** Multi-user home security platform

---

## Overview

This document provides the complete epic and story breakdown for ArgusAI Phase 15, decomposing the requirements from the [PRD](./PRD-phase15.md) into implementable stories.

**Living Document Notice:** This is the initial version. It will be updated after UX Design and Architecture workflows add interaction and technical details to stories.

### Epic Summary

| Epic | Title | Stories | Priority | FRs Covered |
|------|-------|---------|----------|-------------|
| P15-1 | Entity UX Improvements | 5 | P2 | FR23-FR27 |
| P15-2 | Authentication & User Management | 10 | P2 | FR1-FR22 |
| P15-3 | Settings UX Consolidation | 5 | P3 | FR28-FR32 |
| P15-4 | Multi-Entity Event Support | 5 | P3 | FR33-FR37 |
| P15-5 | AI Visual Annotations | 5 | P3 | FR38-FR44 |

**Total:** 30 stories

---

## Functional Requirements Inventory

### User Account & Authentication (FR1-FR9)
- FR1: Administrators can create new user accounts with email and role assignment
- FR2: Users can be invited via email with secure temporary password
- FR3: Users must change password on first login when flagged
- FR4: Users can reset forgotten password via secure email token
- FR5: Users can change their own password from settings
- FR6: System enforces password complexity requirements
- FR7: Administrators can enable/disable user accounts
- FR8: Administrators can delete user accounts
- FR9: System logs all authentication and user management events

### Session Management (FR10-FR16)
- FR10: System tracks all active sessions with metadata (device, IP, user agent)
- FR11: Users can view their active sessions in settings
- FR12: Users can revoke individual sessions
- FR13: Users can revoke all sessions except current
- FR14: System enforces maximum concurrent sessions per user (configurable)
- FR15: Sessions automatically expire after inactivity period
- FR16: Current session is clearly identified in session list

### Role-Based Access Control (FR17-FR22)
- FR17: System supports three roles: Admin, Operator, Viewer
- FR18: Admin role has full system access including user management
- FR19: Operator role can manage events, entities, cameras but not users
- FR20: Viewer role has read-only access to dashboard and events
- FR21: Role permissions are enforced on both frontend and backend
- FR22: Administrators can change user roles

### Entity UX Improvements (FR23-FR27)
- FR23: Entity detail modal supports scrolling for long event lists
- FR24: Entity modal displays events with virtual scrolling for performance
- FR25: Clicking an event in entity modal opens that event's detail view
- FR26: Navigation from event detail back to entity modal preserves state
- FR27: Entity modal shows event count and scroll position indicator

### Settings UX (FR28-FR32)
- FR28: All settings sections use consistent save pattern (explicit Save button)
- FR29: Settings pages show indicator when changes are unsaved
- FR30: System warns before navigating away with unsaved changes
- FR31: Settings save shows confirmation toast on success
- FR32: Settings have Cancel/Reset button to discard changes

### Multi-Entity Events (FR33-FR37)
- FR33: Events can be associated with multiple entities
- FR34: Event cards display badges for all matched entities
- FR35: Entity detail shows events where entity appears (including multi-entity)
- FR36: Event assignment UI supports selecting multiple entities
- FR37: Alert rules can trigger on any matched entity in event

### AI Visual Annotations (FR38-FR44)
- FR38: AI can return bounding box coordinates with descriptions
- FR39: System draws bounding boxes on reference frames
- FR40: Annotations include entity type labels
- FR41: Annotations show confidence scores
- FR42: Bounding boxes are color-coded by entity type
- FR43: Users can toggle annotation visibility on/off
- FR44: Both original and annotated frame versions are stored

---

## FR Coverage Map

| FR Range | Epic | Description |
|----------|------|-------------|
| FR1-FR9 | P15-2 | User Account & Authentication |
| FR10-FR16 | P15-2 | Session Management |
| FR17-FR22 | P15-2 | Role-Based Access Control |
| FR23-FR27 | P15-1 | Entity UX Improvements |
| FR28-FR32 | P15-3 | Settings UX Consolidation |
| FR33-FR37 | P15-4 | Multi-Entity Event Support |
| FR38-FR44 | P15-5 | AI Visual Annotations |

---

## Epic P15-1: Entity UX Improvements

**Goal:** Eliminate UX friction in entity management by fixing modal scrolling, enabling seamless event navigation, and improving performance for entities with many events.

**Backlog References:** IMP-066, IMP-067

**FRs Covered:** FR23, FR24, FR25, FR26, FR27

### Story P15-1.1: Entity Modal Scrolling Fix

As an **operator**,
I want the entity detail modal to scroll properly when viewing many assigned events,
So that I can review all events associated with an entity without UI overflow.

**Acceptance Criteria:**

**Given** an entity with 50+ assigned events
**When** I open the entity detail modal
**Then** the events list container has max-height with overflow-y-auto
**And** I can scroll through all events smoothly
**And** the modal header/footer remain sticky (visible)
**And** scroll position is preserved if modal is temporarily obscured

**Prerequisites:** None

**Technical Notes:**
- File: `frontend/components/entities/EntityDetailModal.tsx`
- Add `max-h-[60vh] overflow-y-auto` to events list container
- Ensure modal itself has proper max-height constraint
- Test with 100+ events for performance baseline

---

### Story P15-1.2: Virtual Scrolling for Large Event Lists

As an **operator**,
I want entity modals with 1000+ events to load quickly,
So that I can work with entities that have extensive history without performance degradation.

**Acceptance Criteria:**

**Given** an entity with 1000+ assigned events
**When** I open the entity detail modal
**Then** the modal loads within 500ms (NFR7)
**And** only visible events are rendered (virtualization)
**And** scrolling remains smooth at 60fps
**And** event count badge shows total count accurately

**Prerequisites:** P15-1.1

**Technical Notes:**
- Implement using `@tanstack/react-virtual` (already in project dependencies)
- Virtualize when event count > 50
- Maintain row height consistency for scroll position accuracy
- File: `frontend/components/entities/EntityDetailModal.tsx`

---

### Story P15-1.3: Event Click Opens Event Detail Modal

As an **operator**,
I want to click an event in the entity modal to see its full details,
So that I can investigate specific events without losing context.

**Acceptance Criteria:**

**Given** I am viewing an entity detail modal with events
**When** I click on an event item
**Then** the EventDetailModal opens with that event's data
**And** the entity modal remains in the background (not closed)
**And** clicking outside event detail or pressing Escape returns to entity modal
**And** entity modal scroll position is preserved

**Prerequisites:** P15-1.1

**Technical Notes:**
- Use React state to manage nested modal visibility
- Store entity modal state (scroll position, selected entity) before opening event detail
- Consider using portal for nested modal to avoid z-index issues
- Files: `frontend/components/entities/EntityDetailModal.tsx`, `frontend/components/events/EventDetailModal.tsx`

---

### Story P15-1.4: Back Navigation from Event Detail

As an **operator**,
I want to navigate back from event detail to the entity modal,
So that I can continue reviewing other events for the same entity.

**Acceptance Criteria:**

**Given** I opened event detail from entity modal
**When** I close the event detail modal (X button, Escape, or backdrop click)
**Then** I return to the entity modal
**And** the entity modal is in the same state (scroll position, selected tab)
**And** the event I just viewed is still visible in the list

**Prerequisites:** P15-1.3

**Technical Notes:**
- Implement breadcrumb-style navigation state
- Use React context or state lifting to preserve entity modal state
- Test with keyboard navigation (Tab, Escape)
- File: `frontend/components/entities/EntityDetailModal.tsx`

---

### Story P15-1.5: Event Count and Scroll Indicator

As an **operator**,
I want to see how many events an entity has and my scroll position,
So that I know the scope of the entity's history.

**Acceptance Criteria:**

**Given** an entity with assigned events
**When** I view the entity detail modal
**Then** I see "X events" badge in the events section header
**And** when scrolling, I see a scroll position indicator (e.g., "Showing 25-50 of 150")
**And** the count updates when events are added/removed

**Prerequisites:** P15-1.2

**Technical Notes:**
- Add event count to EntityDetailModal header
- Use virtualization observer to track visible range
- Format: "Showing {first}-{last} of {total}"
- Update count via React Query cache invalidation when events change

---

## Epic P15-2: Authentication & User Management

**Goal:** Transform ArgusAI from single-user to multi-user with proper authentication, session management, and role-based access control.

**Backlog References:** FF-036, FF-037

**FRs Covered:** FR1-FR22

### Story P15-2.1: User Model and Database Schema

As a **developer**,
I want a User model with all necessary fields for multi-user support,
So that the backend can store and manage user accounts.

**Acceptance Criteria:**

**Given** the database needs user storage
**When** the migration is applied
**Then** User table exists with fields:
  - id (UUID, primary key)
  - email (unique, indexed)
  - password_hash (bcrypt)
  - role (enum: admin, operator, viewer)
  - is_active (boolean, default true)
  - must_change_password (boolean, default false)
  - created_at, updated_at (timestamps)
  - last_login_at (nullable timestamp)
**And** appropriate indexes exist for email lookup
**And** role enum is enforced at database level

**Prerequisites:** None

**Technical Notes:**
- Create Alembic migration
- Use SQLAlchemy Enum for role
- Add unique constraint on email
- File: `backend/app/models/user.py`

---

### Story P15-2.2: Session Model and Tracking

As a **developer**,
I want a Session model to track active user sessions,
So that users can view and manage their login sessions.

**Acceptance Criteria:**

**Given** the database needs session storage
**When** the migration is applied
**Then** Session table exists with fields:
  - id (UUID, primary key)
  - user_id (FK to users)
  - token_hash (for session validation)
  - device_info (string, extracted from User-Agent)
  - ip_address (string)
  - user_agent (full string)
  - created_at (timestamp)
  - last_active_at (timestamp)
  - expires_at (timestamp)
  - is_current (boolean, for UI indicator)
**And** sessions are indexed by user_id and token_hash
**And** cascade delete when user is deleted

**Prerequisites:** P15-2.1

**Technical Notes:**
- Create Alembic migration
- Add relationship to User model
- File: `backend/app/models/session.py`

---

### Story P15-2.3: User CRUD API Endpoints

As an **administrator**,
I want API endpoints to create, read, update, and delete users,
So that I can manage user accounts programmatically.

**Acceptance Criteria:**

**Given** I am authenticated as admin
**When** I call user management endpoints
**Then** the following work correctly:
  - POST `/api/v1/users` creates user with email, role
  - GET `/api/v1/users` lists all users (admin only)
  - GET `/api/v1/users/{id}` returns user details
  - PUT `/api/v1/users/{id}` updates user (email, role, is_active)
  - DELETE `/api/v1/users/{id}` soft-deletes or removes user
  - POST `/api/v1/users/{id}/reset` triggers password reset
**And** non-admin users receive 403 Forbidden
**And** all operations are logged (FR9)

**Prerequisites:** P15-2.1, P15-2.2

**Technical Notes:**
- Create `backend/app/api/v1/users.py` router
- Add admin-only dependency for permission check
- Log to audit trail (use existing logging infrastructure)
- Schemas in `backend/app/schemas/user.py`

---

### Story P15-2.4: Password Hashing and Validation

As a **user**,
I want my password securely hashed and validated against complexity rules,
So that my account is protected from unauthorized access.

**Acceptance Criteria:**

**Given** a user creates or changes password
**When** the password is submitted
**Then** it is validated for:
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 number
  - At least 1 special character (!@#$%^&*)
**And** passwords are hashed with bcrypt cost factor 12 (NFR1)
**And** validation errors return specific feedback (which rule failed)

**Prerequisites:** P15-2.1

**Technical Notes:**
- Add `password_service.py` with hash/verify/validate functions
- Use passlib with bcrypt backend
- Return structured validation errors
- File: `backend/app/services/password_service.py`

---

### Story P15-2.5: User Invitation Flow

As an **administrator**,
I want to invite users via email with temporary password,
So that new team members can access the system.

**Acceptance Criteria:**

**Given** I am an admin creating a new user
**When** I provide email and role
**Then** a secure random password is generated (16 chars)
**And** user is created with must_change_password=true
**And** I can choose to:
  - Display credentials on screen (for manual sharing)
  - Send email invitation (if email service configured)
**And** the temporary password expires after 72 hours if unused

**Prerequisites:** P15-2.3, P15-2.4

**Technical Notes:**
- Generate password using secrets.token_urlsafe()
- Email sending is optional (check system settings)
- Store password_expires_at for temporary passwords
- File: `backend/app/services/user_service.py`

---

### Story P15-2.6: Force Password Change on First Login

As a **new user**,
I want to be prompted to change my temporary password on first login,
So that I can set my own secure password.

**Acceptance Criteria:**

**Given** I have must_change_password=true
**When** I successfully authenticate
**Then** I am redirected to password change screen
**And** I cannot access other pages until password is changed
**And** after changing, must_change_password is set to false
**And** I am redirected to dashboard

**Prerequisites:** P15-2.4, P15-2.5

**Technical Notes:**
- Add middleware to check must_change_password flag
- Frontend: Add ChangePasswordRequired route/modal
- Backend: Add `/api/v1/auth/change-password` endpoint
- File: `frontend/app/change-password/page.tsx`

---

### Story P15-2.7: Session Management API

As a **user**,
I want API endpoints to view and manage my active sessions,
So that I can monitor and secure my account access.

**Acceptance Criteria:**

**Given** I am authenticated
**When** I call session endpoints
**Then** the following work correctly:
  - GET `/api/v1/auth/sessions` lists my active sessions
  - DELETE `/api/v1/auth/sessions/{id}` revokes specific session
  - DELETE `/api/v1/auth/sessions` revokes all except current
**And** session list includes device info, IP, last active time
**And** current session is marked with is_current=true
**And** revoked sessions are immediately invalidated

**Prerequisites:** P15-2.2

**Technical Notes:**
- Create `backend/app/api/v1/auth.py` router (extend existing)
- Use device-detector library for User-Agent parsing
- Invalidate by removing session from DB
- File: `backend/app/api/v1/auth.py`

---

### Story P15-2.8: Session Expiration and Limits

As a **system administrator**,
I want sessions to expire and enforce concurrent limits,
So that abandoned sessions don't pose security risks.

**Acceptance Criteria:**

**Given** system session settings
**When** sessions are created/used
**Then** sessions expire after 24 hours of inactivity (configurable)
**And** maximum 5 concurrent sessions per user (configurable)
**And** when limit reached, oldest session is revoked
**And** expired sessions are cleaned up by background task

**Prerequisites:** P15-2.7

**Technical Notes:**
- Add settings: SESSION_EXPIRY_HOURS, MAX_SESSIONS_PER_USER
- Create background task for cleanup (run hourly)
- Update last_active_at on each authenticated request
- File: `backend/app/services/session_service.py`

---

### Story P15-2.9: Role-Based Access Control Backend

As a **developer**,
I want role-based permissions enforced on all API endpoints,
So that users only access resources appropriate to their role.

**Acceptance Criteria:**

**Given** three roles: admin, operator, viewer
**When** API requests are made
**Then** permissions are enforced:
  - Admin: Full access to all endpoints
  - Operator: CRUD on events, entities, cameras; no user management
  - Viewer: GET only on events, dashboard, entities
**And** unauthorized access returns 403 Forbidden
**And** permission checks use FastAPI dependencies

**Prerequisites:** P15-2.1, P15-2.3

**Technical Notes:**
- Create `require_role(roles: List[Role])` dependency
- Add role checks to existing routers
- Document permission matrix in code comments
- File: `backend/app/core/permissions.py`

---

### Story P15-2.10: User Management UI

As an **administrator**,
I want a UI to manage users in Settings,
So that I can create, edit, and manage user accounts visually.

**Acceptance Criteria:**

**Given** I am logged in as admin
**When** I navigate to Settings > Users
**Then** I see a list of all users with:
  - Email, role, status (active/disabled), last login
  - Actions: Edit, Disable/Enable, Delete, Reset Password
**And** I can click "Invite User" to open invite modal
**And** invite modal shows generated credentials or sends email
**And** non-admins don't see the Users settings tab

**Prerequisites:** P15-2.3, P15-2.5, P15-2.9

**Technical Notes:**
- Create `frontend/components/settings/UserManagement.tsx`
- Add Users tab to Settings page (admin only)
- Use existing table component patterns
- Confirmation dialogs for destructive actions

---

## Epic P15-3: Settings UX Consolidation

**Goal:** Standardize settings save patterns across all settings pages for consistent, predictable user experience.

**Backlog References:** IMP-068

**FRs Covered:** FR28-FR32

### Story P15-3.1: Audit Settings Save Patterns

As a **developer**,
I want to audit all settings sections for current save behavior,
So that I understand what needs to be standardized.

**Acceptance Criteria:**

**Given** all settings pages in the application
**When** I document current behavior
**Then** I have a list showing for each section:
  - Current save mechanism (auto-save, button, mixed)
  - Any existing unsaved change detection
  - Navigation warning behavior
**And** this audit informs Stories P15-3.2 through P15-3.5

**Prerequisites:** None

**Technical Notes:**
- Review files in `frontend/components/settings/`
- Document in PR or story notes
- Settings sections: General, AI, Cameras, Alerts, Notifications, Security, etc.

---

### Story P15-3.2: Settings Form State Management Hook

As a **developer**,
I want a reusable hook for settings form state management,
So that all settings sections can use consistent save patterns.

**Acceptance Criteria:**

**Given** a settings section needs form state management
**When** using the `useSettingsForm` hook
**Then** it provides:
  - Form state tracking (original vs current values)
  - `isDirty` boolean for unsaved changes
  - `save()` function that calls API and resets dirty state
  - `reset()` function to discard changes
  - `isLoading` state during save
**And** the hook is type-safe with generics

**Prerequisites:** P15-3.1

**Technical Notes:**
- Create `frontend/hooks/useSettingsForm.ts`
- Use React Hook Form or custom implementation
- Integrate with existing React Query patterns
- Support both sync and async save functions

---

### Story P15-3.3: Unsaved Changes Indicator

As a **user**,
I want to see when I have unsaved changes in settings,
So that I know I need to save before leaving.

**Acceptance Criteria:**

**Given** I have modified a settings field
**When** the form becomes dirty
**Then** I see a visual indicator (e.g., orange dot on Save button, "Unsaved changes" text)
**And** the Save button becomes enabled/highlighted
**And** the indicator clears after successful save
**And** the indicator clears after reset/cancel

**Prerequisites:** P15-3.2

**Technical Notes:**
- Add `UnsavedIndicator` component
- Style: Orange dot or asterisk near section title
- Integrate with `useSettingsForm` hook
- File: `frontend/components/settings/UnsavedIndicator.tsx`

---

### Story P15-3.4: Navigation Warning for Unsaved Changes

As a **user**,
I want to be warned when navigating away with unsaved changes,
So that I don't accidentally lose my settings modifications.

**Acceptance Criteria:**

**Given** I have unsaved changes in settings
**When** I try to navigate to another page
**Then** I see a confirmation dialog:
  - "You have unsaved changes. Discard changes?"
  - Options: "Stay", "Discard"
**And** clicking "Stay" keeps me on the settings page
**And** clicking "Discard" navigates away without saving
**And** browser beforeunload event also warns on page close

**Prerequisites:** P15-3.2, P15-3.3

**Technical Notes:**
- Use Next.js router events for SPA navigation
- Add beforeunload listener for browser close/refresh
- Use existing Dialog component for confirmation
- File: `frontend/hooks/useUnsavedChangesWarning.ts`

---

### Story P15-3.5: Standardize All Settings Sections

As a **user**,
I want all settings sections to use the same save pattern,
So that my experience is consistent throughout settings.

**Acceptance Criteria:**

**Given** any settings section (General, AI, Cameras, Alerts, etc.)
**When** I make changes
**Then** I see explicit Save and Cancel buttons at section bottom
**And** Save is disabled when no changes exist
**And** Save shows loading spinner during save
**And** Success toast appears after save completes
**And** Cancel button resets form to original values

**Prerequisites:** P15-3.2, P15-3.3, P15-3.4

**Technical Notes:**
- Apply `useSettingsForm` hook to all settings sections
- Add consistent button placement (bottom-right of each section)
- Use existing toast system for success feedback
- Files: All components in `frontend/components/settings/`

---

## Epic P15-4: Multi-Entity Event Support

**Goal:** Enable events to be associated with multiple entities, supporting real-world scenarios like two people walking together.

**Backlog References:** IMP-069

**FRs Covered:** FR33-FR37

### Story P15-4.1: Backend Multi-Entity Support

As a **developer**,
I want the backend to support multiple entities per event,
So that events can accurately represent multi-person/vehicle scenarios.

**Acceptance Criteria:**

**Given** an event with multiple detected entities
**When** entity matching runs
**Then** `matched_entity_ids` JSON field stores array of entity IDs
**And** EntityEvent junction table has multiple records per event
**And** event API returns all matched entities in response
**And** backward compatibility: single-entity events still work

**Prerequisites:** None

**Technical Notes:**
- Review existing `matched_entity_ids` field (may already be JSON array)
- Ensure EntityEvent many-to-many is properly configured
- Update entity_service.py matching logic
- File: `backend/app/services/entity_service.py`

---

### Story P15-4.2: Multi-Entity Display on Event Cards

As an **operator**,
I want event cards to show all matched entities,
So that I can see everyone/everything detected in an event.

**Acceptance Criteria:**

**Given** an event matched to multiple entities
**When** I view the event card
**Then** I see badges/avatars for all matched entities
**And** badges are clickable to open entity detail
**And** if more than 3 entities, show "+N more" overflow indicator
**And** tooltip on hover shows all entity names

**Prerequisites:** P15-4.1

**Technical Notes:**
- Update EventCard component
- Use Avatar stack component for multiple entities
- Limit visible badges to 3, show overflow count
- File: `frontend/components/events/EventCard.tsx`

---

### Story P15-4.3: Entity Detail Multi-Event Query

As an **operator**,
I want entity detail to show all events where an entity appears,
So that I can see complete history including multi-entity events.

**Acceptance Criteria:**

**Given** an entity that appears in multi-entity events
**When** I view the entity detail modal
**Then** the events list includes all events where this entity appears
**And** multi-entity events show "with [other entity names]" indicator
**And** event count reflects total appearances

**Prerequisites:** P15-4.1, P15-1.1

**Technical Notes:**
- Update entity events API query to use EntityEvent junction table
- Include co-appearing entities in response
- File: `backend/app/api/v1/entities.py`

---

### Story P15-4.4: Multi-Select Entity Assignment UI

As an **operator**,
I want to assign multiple entities to an event manually,
So that I can correct AI detection when it missed entities.

**Acceptance Criteria:**

**Given** I am editing entity assignment for an event
**When** I open the assignment UI
**Then** I can select multiple entities via checkboxes
**And** I see currently assigned entities pre-selected
**And** I can search/filter the entity list
**And** saving updates all EntityEvent relationships

**Prerequisites:** P15-4.1

**Technical Notes:**
- Update EntityAssignmentModal to support multi-select
- Use Combobox with multi-select pattern
- API: PUT `/api/v1/events/{id}/entities` accepts array
- File: `frontend/components/events/EntityAssignmentModal.tsx`

---

### Story P15-4.5: Alert Rules Multi-Entity Trigger

As an **operator**,
I want alert rules to trigger when any matched entity meets criteria,
So that I get notifications for VIP appearances in group events.

**Acceptance Criteria:**

**Given** an alert rule configured for specific entity (e.g., VIP person)
**When** an event matches multiple entities including the VIP
**Then** the alert rule triggers
**And** the notification indicates which entity triggered it
**And** alert doesn't trigger multiple times for same event

**Prerequisites:** P15-4.1

**Technical Notes:**
- Update alert_engine.py entity matching logic
- Check all matched_entity_ids against rule criteria
- Include triggering entity ID in webhook payload
- File: `backend/app/services/alert_engine.py`

---

## Epic P15-5: AI Visual Annotations

**Goal:** Add visual annotations (bounding boxes, labels) to AI-analyzed frames to show what the AI detected.

**Backlog References:** FF-035

**FRs Covered:** FR38-FR44

### Story P15-5.1: AI Bounding Box Response Schema

As a **developer**,
I want the AI service to return bounding box coordinates,
So that we can draw annotations on frames.

**Acceptance Criteria:**

**Given** AI analyzes a frame with detected objects
**When** the description is generated
**Then** response includes optional bounding_boxes array:
  - Each box has: x, y, width, height (normalized 0-1)
  - entity_type (person, vehicle, package, animal, other)
  - confidence (0.0-1.0)
  - label (description text)
**And** providers that support native bounding boxes use them (GPT-4o, Gemini)
**And** providers without native support return null bounding_boxes

**Prerequisites:** None

**Technical Notes:**
- Update AI response schema
- GPT-4o and Gemini have native bounding box support
- Claude needs prompt engineering or returns null
- File: `backend/app/schemas/ai.py`, `backend/app/services/ai_service.py`

---

### Story P15-5.2: Frame Annotation Service

As a **developer**,
I want a service that draws bounding boxes on frames,
So that annotated versions can be stored alongside originals.

**Acceptance Criteria:**

**Given** an original frame and bounding box data
**When** annotation service processes them
**Then** it produces an annotated frame with:
  - Bounding boxes drawn with 2px stroke
  - Color-coded by entity type (person=blue, vehicle=green, package=orange, other=gray)
  - Label text above each box
  - Confidence percentage in label
**And** original frame is preserved (not modified)
**And** annotated frame is saved with `_annotated` suffix

**Prerequisites:** P15-5.1

**Technical Notes:**
- Use Pillow or OpenCV for drawing
- Store both original and annotated in thumbnails directory
- File: `backend/app/services/frame_annotation_service.py`

---

### Story P15-5.3: Store Annotated Frames

As a **developer**,
I want annotated frames stored alongside originals,
So that users can view either version.

**Acceptance Criteria:**

**Given** an event with AI analysis and bounding boxes
**When** frames are processed
**Then** original frame stored at `{event_id}/frame_{n}.jpg`
**And** annotated frame stored at `{event_id}/frame_{n}_annotated.jpg`
**And** event record includes `has_annotations` boolean flag
**And** API returns both URLs when annotations exist

**Prerequisites:** P15-5.2

**Technical Notes:**
- Update event processing pipeline
- Add has_annotations field to Event model
- Update frame URLs in event API response
- File: `backend/app/services/event_processor.py`

---

### Story P15-5.4: Annotation Toggle in Event Detail

As an **operator**,
I want to toggle annotations on/off when viewing event frames,
So that I can see what AI detected or view clean original.

**Acceptance Criteria:**

**Given** I am viewing event detail with frames that have annotations
**When** I click the annotation toggle
**Then** frame display switches between original and annotated versions
**And** toggle shows current state (e.g., "Show Annotations" / "Hide Annotations")
**And** preference persists during session
**And** toggle is disabled/hidden for events without annotations

**Prerequisites:** P15-5.3

**Technical Notes:**
- Add toggle button to EventDetailModal frame viewer
- Use React state for toggle
- Check `has_annotations` to show/hide toggle
- File: `frontend/components/events/EventDetailModal.tsx`

---

### Story P15-5.5: Annotation Legend and Styling

As an **operator**,
I want consistent annotation styling with a legend,
So that I understand what the colors and labels mean.

**Acceptance Criteria:**

**Given** I am viewing annotated frames
**When** annotations are visible
**Then** I see a color legend showing entity type colors
**And** annotations are visually consistent across all events
**And** boxes don't obscure critical frame areas (thin lines, semi-transparent fill)
**And** labels are readable on both light and dark backgrounds (outline/shadow)

**Prerequisites:** P15-5.4

**Technical Notes:**
- Add AnnotationLegend component
- Use consistent color palette across backend and frontend
- Apply text shadow for label readability
- File: `frontend/components/events/AnnotationLegend.tsx`

---

## FR Coverage Matrix

| FR | Description | Epic | Story |
|----|-------------|------|-------|
| FR1 | Create user accounts with email and role | P15-2 | P15-2.3 |
| FR2 | Invite users via email with temporary password | P15-2 | P15-2.5 |
| FR3 | Force password change on first login | P15-2 | P15-2.6 |
| FR4 | Reset password via email token | P15-2 | P15-2.5 |
| FR5 | Change own password from settings | P15-2 | P15-2.6 |
| FR6 | Enforce password complexity | P15-2 | P15-2.4 |
| FR7 | Enable/disable user accounts | P15-2 | P15-2.3 |
| FR8 | Delete user accounts | P15-2 | P15-2.3 |
| FR9 | Log authentication events | P15-2 | P15-2.3 |
| FR10 | Track sessions with metadata | P15-2 | P15-2.2 |
| FR11 | View active sessions | P15-2 | P15-2.7, P15-2.10 |
| FR12 | Revoke individual sessions | P15-2 | P15-2.7 |
| FR13 | Revoke all sessions except current | P15-2 | P15-2.7 |
| FR14 | Enforce max concurrent sessions | P15-2 | P15-2.8 |
| FR15 | Session auto-expiry | P15-2 | P15-2.8 |
| FR16 | Identify current session | P15-2 | P15-2.7 |
| FR17 | Support three roles | P15-2 | P15-2.1 |
| FR18 | Admin full access | P15-2 | P15-2.9 |
| FR19 | Operator manage events/entities | P15-2 | P15-2.9 |
| FR20 | Viewer read-only access | P15-2 | P15-2.9 |
| FR21 | Enforce permissions frontend+backend | P15-2 | P15-2.9, P15-2.10 |
| FR22 | Admin change user roles | P15-2 | P15-2.3 |
| FR23 | Entity modal scrolling | P15-1 | P15-1.1 |
| FR24 | Virtual scrolling for performance | P15-1 | P15-1.2 |
| FR25 | Click event opens detail | P15-1 | P15-1.3 |
| FR26 | Back navigation preserves state | P15-1 | P15-1.4 |
| FR27 | Event count and scroll indicator | P15-1 | P15-1.5 |
| FR28 | Consistent save pattern | P15-3 | P15-3.5 |
| FR29 | Unsaved changes indicator | P15-3 | P15-3.3 |
| FR30 | Navigation warning | P15-3 | P15-3.4 |
| FR31 | Save confirmation toast | P15-3 | P15-3.5 |
| FR32 | Cancel/Reset button | P15-3 | P15-3.5 |
| FR33 | Multi-entity association | P15-4 | P15-4.1 |
| FR34 | Multi-entity badges on cards | P15-4 | P15-4.2 |
| FR35 | Entity detail shows multi-entity events | P15-4 | P15-4.3 |
| FR36 | Multi-select entity assignment | P15-4 | P15-4.4 |
| FR37 | Alert rules on any matched entity | P15-4 | P15-4.5 |
| FR38 | AI returns bounding boxes | P15-5 | P15-5.1 |
| FR39 | Draw bounding boxes on frames | P15-5 | P15-5.2 |
| FR40 | Entity type labels | P15-5 | P15-5.2 |
| FR41 | Confidence scores | P15-5 | P15-5.2 |
| FR42 | Color-coded by type | P15-5 | P15-5.2 |
| FR43 | Toggle annotation visibility | P15-5 | P15-5.4 |
| FR44 | Store both frame versions | P15-5 | P15-5.3 |

---

## Summary

### Epic Breakdown Complete

| Epic | Stories | Priority | Recommended Sequence |
|------|---------|----------|---------------------|
| P15-1: Entity UX | 5 | P2 | Week 1 |
| P15-2: Auth & Users | 10 | P2 | Week 1-2 |
| P15-3: Settings UX | 5 | P3 | Week 2 |
| P15-4: Multi-Entity | 5 | P3 | Week 3 |
| P15-5: AI Annotations | 5 | P3 | Week 3-4 |

**Total Stories:** 30

### Implementation Notes

1. **P15-1 and P15-2 can run in parallel** - No dependencies between them
2. **P15-3 depends on completing P15-2.10** - User management needs settings save pattern
3. **P15-4 depends on P15-1.1** - Multi-entity events use same modal scrolling
4. **P15-5 is independent** - Can start anytime after foundation

### Non-Functional Requirements Coverage

| NFR | Description | Covered By |
|-----|-------------|------------|
| NFR1 | bcrypt cost 12 | P15-2.4 |
| NFR2 | Token expiry 24h | P15-2.5 |
| NFR3 | 256-bit tokens | P15-2.2 |
| NFR4 | Rate limiting | P15-2.9 (existing) |
| NFR5 | Audit logging | P15-2.3, P15-2.7 |
| NFR6 | Session encryption | P15-2.2 |
| NFR7 | 500ms load time | P15-1.2 |
| NFR8 | 100ms API | P15-2.7 |
| NFR9 | 1s save time | P15-3.5 |
| NFR10-12 | Accessibility | All UI stories |

---

_For implementation: Use the `create-story` workflow to generate individual story implementation plans from this epic breakdown._

_This document will be updated after UX Design and Architecture workflows to incorporate interaction details and technical decisions._
