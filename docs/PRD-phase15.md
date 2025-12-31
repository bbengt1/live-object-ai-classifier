# ArgusAI Phase 15 - Product Requirements Document

**Author:** Brent
**Date:** 2025-12-30
**Version:** 1.0
**Status:** ✅ **COMPLETE** (2025-12-31)

---

## Executive Summary

Phase 15 focuses on **User Experience Polish & Authentication Foundation** - addressing UX friction points identified during Phase 14 while establishing proper user authentication and session management. This phase transforms ArgusAI from a single-user system to a multi-user platform with proper security controls.

### What Makes This Special

Phase 15 delivers two key value propositions:
1. **Smoother User Experience** - Entity modals work intuitively, settings save consistently, and multi-entity events are properly handled
2. **Production-Ready Authentication** - Real user management, session control, and security visibility that enterprise deployments require

---

## Project Classification

**Technical Type:** Web Application (FastAPI + Next.js)
**Domain:** Home Security / AI Vision
**Complexity:** Medium

This is an existing production system (Phase 14 complete) requiring incremental improvements rather than greenfield development. The authentication work builds on the existing stub auth system.

---

## Success Criteria

### Primary Success Metrics

1. **UX Friction Eliminated** - Zero user-reported issues with entity modal overflow, event navigation, or settings save confusion
2. **Multi-User Ready** - Support 3+ concurrent users with distinct sessions and role-based access
3. **Security Visibility** - Users can see and revoke active sessions within 2 clicks from settings

### Business Metrics

- Reduce support tickets related to UX confusion by 80%
- Enable team deployments (multiple family members/operators)
- Pass security audit for session management best practices

---

## Product Scope

### MVP - Minimum Viable Product

**Epic P15-1: Entity UX Improvements** (P2 Priority)
- Entity modal scrolling for long event lists
- Click event in entity modal → opens event detail
- Virtual scrolling if event count is large

**Epic P15-2: Authentication & User Management** (P2 Priority)
- User model with email, roles, password management
- User invitation flow with temporary passwords
- Force password change on first login
- Active sessions list with revocation
- Role-based permissions (admin, viewer, operator)

**Epic P15-3: Settings UX Consolidation** (P3 Priority)
- Audit all settings sections for save patterns
- Standardize on explicit Save button pattern
- Add unsaved changes indicator
- Warn before navigating away with unsaved changes

### Growth Features (Post-MVP)

**Epic P15-4: Multi-Entity Event Support** (P3 Priority)
- Backend support for multiple entities per event
- Frontend multi-entity badges on event cards
- Entity assignment UI with multi-select
- Alert rules trigger on any matched entity

**Epic P15-5: AI Visual Annotations** (P3 Priority)
- Bounding boxes on detected objects in frames
- Entity type labels with confidence scores
- Color-coded boxes by entity type
- Toggle to show/hide annotations

**Epic P15-6: MCP Protocol Enhancement** (P3-P4 Priority)
- Full MCP Protocol compliance with official SDK
- A/B testing framework for context quality
- False positive frequency pattern tracking

### Vision (Future - Phase 16+)

- Audio capture from cameras (FF-015)
- Export motion events to CSV (FF-017)
- Camera list optimizations for large deployments (IMP-005)
- Additional accessibility enhancements (IMP-004)

---

## Web Application Specific Requirements

### Authentication & Authorization

**Authentication Model:**
- Session-based authentication with JWT tokens
- Password hashing with bcrypt
- Secure password reset via email token
- Session tracking with device/IP metadata

**Role-Based Access Control:**
| Role | Capabilities |
|------|-------------|
| Admin | Full system access, user management, settings |
| Operator | View/manage events, entities, cameras |
| Viewer | Read-only access to events and dashboard |

### API Endpoints (New)

```
# User Management
POST   /api/v1/users              # Create/invite user
GET    /api/v1/users              # List users (admin only)
GET    /api/v1/users/{id}         # Get user details
PUT    /api/v1/users/{id}         # Update user
DELETE /api/v1/users/{id}         # Delete user
POST   /api/v1/users/{id}/reset   # Trigger password reset

# Session Management
GET    /api/v1/auth/sessions      # List active sessions
DELETE /api/v1/auth/sessions/{id} # Revoke specific session
DELETE /api/v1/auth/sessions      # Revoke all except current
POST   /api/v1/auth/change-password # Change password
```

---

## User Experience Principles

### Visual Personality
- Professional, clean, security-focused
- Consistent with existing shadcn/ui design system
- Clear feedback for all user actions

### Key Interactions

1. **Entity Modal → Event Detail**
   - Click event in entity modal → event detail modal opens
   - Smooth transition, clear back navigation
   - Entity modal state preserved

2. **Settings Save Pattern**
   - Explicit "Save" button at bottom of each section
   - Visual indicator for unsaved changes
   - Confirmation toast on successful save
   - Warning dialog if navigating away with unsaved changes

3. **Session Management**
   - Clear list of active sessions with device info
   - Current session clearly marked
   - One-click revocation with confirmation
   - "Sign out all other sessions" bulk action

---

## Functional Requirements

### User Account & Authentication

- FR1: Administrators can create new user accounts with email and role assignment
- FR2: Users can be invited via email with secure temporary password
- FR3: Users must change password on first login when flagged
- FR4: Users can reset forgotten password via secure email token
- FR5: Users can change their own password from settings
- FR6: System enforces password complexity requirements
- FR7: Administrators can enable/disable user accounts
- FR8: Administrators can delete user accounts
- FR9: System logs all authentication and user management events

### Session Management

- FR10: System tracks all active sessions with metadata (device, IP, user agent)
- FR11: Users can view their active sessions in settings
- FR12: Users can revoke individual sessions
- FR13: Users can revoke all sessions except current
- FR14: System enforces maximum concurrent sessions per user (configurable)
- FR15: Sessions automatically expire after inactivity period
- FR16: Current session is clearly identified in session list

### Role-Based Access Control

- FR17: System supports three roles: Admin, Operator, Viewer
- FR18: Admin role has full system access including user management
- FR19: Operator role can manage events, entities, cameras but not users
- FR20: Viewer role has read-only access to dashboard and events
- FR21: Role permissions are enforced on both frontend and backend
- FR22: Administrators can change user roles

### Entity UX Improvements

- FR23: Entity detail modal supports scrolling for long event lists
- FR24: Entity modal displays events with virtual scrolling for performance
- FR25: Clicking an event in entity modal opens that event's detail view
- FR26: Navigation from event detail back to entity modal preserves state
- FR27: Entity modal shows event count and scroll position indicator

### Settings UX

- FR28: All settings sections use consistent save pattern (explicit Save button)
- FR29: Settings pages show indicator when changes are unsaved
- FR30: System warns before navigating away with unsaved changes
- FR31: Settings save shows confirmation toast on success
- FR32: Settings have Cancel/Reset button to discard changes

### Multi-Entity Events (Growth)

- FR33: Events can be associated with multiple entities
- FR34: Event cards display badges for all matched entities
- FR35: Entity detail shows events where entity appears (including multi-entity)
- FR36: Event assignment UI supports selecting multiple entities
- FR37: Alert rules can trigger on any matched entity in event

### AI Visual Annotations (Growth)

- FR38: AI can return bounding box coordinates with descriptions
- FR39: System draws bounding boxes on reference frames
- FR40: Annotations include entity type labels
- FR41: Annotations show confidence scores
- FR42: Bounding boxes are color-coded by entity type
- FR43: Users can toggle annotation visibility on/off
- FR44: Both original and annotated frame versions are stored

---

## Non-Functional Requirements

### Security

- NFR1: Passwords must be hashed with bcrypt (cost factor ≥ 12)
- NFR2: Password reset tokens expire after 24 hours
- NFR3: Session tokens use secure random generation (256-bit)
- NFR4: Failed login attempts are rate-limited (5 attempts per minute)
- NFR5: All authentication events are logged for audit
- NFR6: Session data is encrypted at rest

### Performance

- NFR7: Entity modal with 1000+ events loads within 500ms (virtual scroll)
- NFR8: Session list API responds within 100ms
- NFR9: Settings save completes within 1 second

### Accessibility

- NFR10: All new UI components meet WCAG 2.1 AA standards
- NFR11: Session management UI is keyboard navigable
- NFR12: Appropriate ARIA labels on interactive elements

---

## Implementation Planning

### Epic Breakdown

| Epic | Stories | Priority | Dependencies |
|------|---------|----------|--------------|
| P15-1: Entity UX | 3-4 | P2 | None |
| P15-2: Auth & Users | 8-10 | P2 | None |
| P15-3: Settings UX | 4-5 | P3 | None |
| P15-4: Multi-Entity | 5-6 | P3 | P15-1 |
| P15-5: AI Annotations | 4-5 | P3 | None |
| P15-6: MCP Protocol | 3-4 | P4 | None |

**Estimated Total:** 27-34 stories

### Recommended Sequence

1. **P15-1 + P15-2** (Parallel) - Core MVP functionality
2. **P15-3** - Settings consistency
3. **P15-4** - Multi-entity support
4. **P15-5 + P15-6** (Parallel) - AI enhancements

---

## References

- Backlog: docs/backlog.md (IMP-066, IMP-067, IMP-068, IMP-069, FF-036, FF-037, FF-035)
- Sprint Status: docs/sprint-artifacts/sprint-status.yaml
- Previous PRD: docs/PRD-phase14.md

---

## Next Steps

1. **Epic & Story Breakdown** - Run: `workflow create-epics-and-stories`
2. **Architecture** - Run: `workflow create-architecture` (especially for auth system)
3. **UX Design** - Run: `workflow ux-design` (for entity modal and settings patterns)

---

_This PRD captures the essence of ArgusAI Phase 15 - transforming from a single-user prototype to a production-ready multi-user security platform with polished user experience._

_Created through collaborative discovery between Brent and AI facilitator._
