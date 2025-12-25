# Story P10-5.4: Define Mobile Push Architecture

Status: done

## Story

As a **developer building mobile apps for ArgusAI**,
I want **documented push notification architecture for iOS/iPadOS, watchOS, and Android**,
So that **mobile devices receive real-time security alerts through native platform push services**.

## Acceptance Criteria

1. **AC-5.4.1:** Given I read the architecture document, when I understand the push notification flow, then I know how device tokens are registered and managed for both APNS (Apple) and FCM (Google/Android)

2. **AC-5.4.2:** Given the architecture documents token storage, when I implement the mobile app, then I understand the device token data model and how tokens are associated with users

3. **AC-5.4.3:** Given the architecture defines notification payloads, when I receive a push notification, then I know the exact JSON structure matching the existing web push format

4. **AC-5.4.4:** Given multiple devices per user are supported, when a security event occurs, then all registered devices for that user receive alerts

5. **AC-5.4.5:** Given the architecture addresses token lifecycle, when tokens expire or change, then I understand the refresh/update flow to maintain notification delivery

6. **AC-5.4.6:** Given notification preferences are documented, when users configure per-device settings, then I understand how preferences affect delivery to each device

## Tasks / Subtasks

- [x] Task 1: Document APNS Integration (AC: 1, 5)
  - [x] Subtask 1.1: Document APNS certificate/key requirements (p8 auth key vs certificate)
  - [x] Subtask 1.2: Define APNS token registration flow from iOS/watchOS devices
  - [x] Subtask 1.3: Document APNS payload format with ArgusAI notification structure
  - [x] Subtask 1.4: Address APNS token refresh and invalidation handling
  - [x] Subtask 1.5: Document sandbox vs production environment handling

- [x] Task 2: Document FCM Integration (AC: 1, 5)
  - [x] Subtask 2.1: Document Firebase project setup requirements
  - [x] Subtask 2.2: Define FCM token registration flow from Android devices
  - [x] Subtask 2.3: Document FCM payload format (data vs notification messages)
  - [x] Subtask 2.4: Address FCM token refresh handling
  - [x] Subtask 2.5: Consider FCM for Apple devices as alternative to direct APNS

- [x] Task 3: Design Device Token Storage Model (AC: 2, 4)
  - [x] Subtask 3.1: Define database schema for mobile push tokens
  - [x] Subtask 3.2: Document relationship between users, devices, and tokens
  - [x] Subtask 3.3: Design token uniqueness and deduplication strategy
  - [x] Subtask 3.4: Document device metadata storage (platform, model, app version)

- [x] Task 4: Define Notification Payload Structure (AC: 3)
  - [x] Subtask 4.1: Document unified payload format compatible with web push
  - [x] Subtask 4.2: Define APNS-specific payload adaptations (aps dictionary)
  - [x] Subtask 4.3: Define FCM-specific payload adaptations
  - [x] Subtask 4.4: Include thumbnail URL handling for rich notifications
  - [x] Subtask 4.5: Document notification categories and actions

- [x] Task 5: Document Notification Preferences (AC: 6)
  - [x] Subtask 5.1: Define per-device preference storage
  - [x] Subtask 5.2: Document camera-specific notification settings
  - [x] Subtask 5.3: Document object type filtering (person, vehicle, package, etc.)
  - [x] Subtask 5.4: Document quiet hours/do-not-disturb handling
  - [x] Subtask 5.5: Cross-reference with existing web push preferences API

- [x] Task 6: Create Architecture Document (AC: 1-6)
  - [x] Subtask 6.1: Create `docs/api/mobile-push-architecture.md`
  - [x] Subtask 6.2: Include sequence diagrams (Mermaid) for registration and delivery flows
  - [x] Subtask 6.3: Document API endpoints for mobile token management
  - [x] Subtask 6.4: Include implementation recommendations
  - [x] Subtask 6.5: Cross-reference with mobile-auth-flow.md and cloud-relay-architecture.md

## Dev Notes

### Architecture Context

This story is documentation/design work only - no implementation required. The goal is to produce a comprehensive architecture document for mobile push notifications that will guide future iOS/Android app development.

**Key Requirements from PRD-phase10.md (via epics-phase10.md):**
- Push notifications for mobile devices receiving real-time alerts
- Token registration flow documentation
- APNS/FCM integration documentation
- Notification payload format definition (matching web push)
- Multi-device support per user
- Notification preferences per device
- Token refresh/expiration handling

**Existing Infrastructure from P10-5.2 (mobile-auth-flow.md):**
- Web Push with VAPID keys is already implemented
- `POST /api/v1/push/subscribe` endpoint exists
- `GET /api/v1/push/vapid-public-key` endpoint exists
- `POST /api/v1/push/preferences` and `PUT /api/v1/push/preferences` endpoints exist
- Push notification preferences include: enabled_cameras, enabled_object_types, quiet_hours

### Key Design Considerations

1. **Unified Backend:** Single push service that handles web push, APNS, and FCM
2. **Platform Detection:** Determine push service based on device registration endpoint/platform header
3. **Payload Consistency:** Same notification content across all platforms with platform-specific formatting
4. **Token Security:** Push tokens must be stored securely and associated with authenticated users
5. **Graceful Degradation:** Handle token invalidation without breaking other subscriptions

### APNS Considerations

- **Authentication:** Use APNS Auth Key (.p8) rather than certificates for easier management
- **Environments:** Sandbox (development) vs Production push endpoints
- **Payload Size:** Maximum 4KB for APNS payloads
- **Priority:** Use priority 10 for security alerts (immediate delivery)
- **Push Token Format:** Hex-encoded device token from iOS

### FCM Considerations

- **Message Types:** Data messages (handled by app) vs Notification messages (shown by system)
- **Token Refresh:** FCM tokens can change - handle `onNewToken` callback
- **Topic Subscriptions:** Consider for broadcast notifications
- **APNs Integration:** FCM can proxy to APNS for iOS devices (optional)

### Project Structure Notes

- Architecture document: `docs/api/mobile-push-architecture.md`
- Should use Mermaid diagrams for visual representation (consistent with P10-5.2, P10-5.3)
- Cross-reference existing documentation:
  - `docs/api/mobile-auth-flow.md` - Device registration, JWT authentication
  - `docs/architecture/cloud-relay-architecture.md` - Remote access considerations

### Learnings from Previous Story

**From Story p10-5-3-design-cloud-relay-architecture (Status: done)**

- **New Documentation Created**: Cloud relay architecture documented at `docs/architecture/cloud-relay-architecture.md` - includes device pairing flow that can inform push token registration
- **Mermaid Diagrams**: Use consistent Mermaid syntax for sequence diagrams and flowcharts
- **Device Management Endpoints**: P10-5.3 proposed `/api/v1/devices` endpoints that should integrate with push token management
- **Security Patterns**: TLS 1.3, JWT authentication patterns established - apply to push token registration
- **Cross-Platform Considerations**: Document addressed both iOS and general mobile - continue this approach

[Source: docs/sprint-artifacts/p10-5-3-design-cloud-relay-architecture.md#Dev-Agent-Record]

### References

- [Source: docs/PRD-phase10.md#FR44-FR47] - Apple Platform Foundation requirements
- [Source: docs/epics-phase10.md#Story-P10-5.4]
- [Source: docs/api/mobile-auth-flow.md] - Mobile authentication flow and push token management
- [Source: docs/architecture/cloud-relay-architecture.md] - Cloud relay and device management
- [Apple APNS Documentation](https://developer.apple.com/documentation/usernotifications)
- [Firebase Cloud Messaging Documentation](https://firebase.google.com/docs/cloud-messaging)

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/p10-5-4-define-mobile-push-architecture.context.xml

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Created comprehensive mobile push architecture document covering all 6 acceptance criteria
- Documentation-only story - no code implementation required

### Completion Notes List

- Created `docs/api/mobile-push-architecture.md` (comprehensive architecture document)
- Documented APNS integration with token-based (.p8) authentication, sandbox/production environments
- Documented FCM integration with service account auth, data vs notification messages
- Defined `mobile_push_tokens` database schema with platform, device, and token fields
- Documented unified notification payload structure with APNS and FCM adaptations
- Included Mermaid sequence diagrams for registration, delivery, and token refresh flows
- Defined API endpoints: register, update token, unregister, preferences
- Cross-referenced mobile-auth-flow.md and cloud-relay-architecture.md
- Included implementation recommendations (aioapns, firebase-admin libraries)
- Documented security considerations for token storage and transport

### File List

- docs/api/mobile-push-architecture.md (NEW)
- docs/sprint-artifacts/p10-5-4-define-mobile-push-architecture.md (MODIFIED)
- docs/sprint-artifacts/p10-5-4-define-mobile-push-architecture.context.xml (NEW)
- docs/sprint-artifacts/sprint-status.yaml (MODIFIED)

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-25 | Story drafted |
| 2025-12-25 | Story completed - all tasks done, architecture document created |
