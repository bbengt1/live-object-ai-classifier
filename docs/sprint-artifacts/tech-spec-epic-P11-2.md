# Epic Technical Specification: Mobile Push Notifications

Date: 2025-12-25
Author: Brent
Epic ID: P11-2
Status: Draft

---

## Overview

Epic P11-2 implements native push notifications for iOS (APNS) and Android (FCM) devices, enabling ArgusAI users to receive security event alerts on their mobile devices. This builds on the mobile push architecture designed in Phase 10 (docs/api/mobile-push-architecture.md) and extends the existing Web Push infrastructure.

The implementation introduces a unified push dispatch system that routes notifications to the appropriate provider based on device platform, handles device registration and token management, and supports rich notifications with thumbnails.

## Objectives and Scope

### In Scope

- APNS provider for iOS push notifications (HTTP/2, p8 auth key)
- FCM provider for Android push notifications (HTTP v1 API, service account)
- Unified PushDispatchService routing to Web Push, APNS, and FCM
- Device registration API and token management
- Quiet hours with timezone support
- Notification thumbnails/attachments
- Token invalidation and cleanup

### Out of Scope

- Native iOS/Android app development (future phase)
- Apple Watch notifications (future phase)
- SMS/email fallback notifications
- Per-notification customization beyond event type

## System Architecture Alignment

This epic implements the push architecture from `docs/api/mobile-push-architecture.md`:

- **APNSProvider** connects via HTTP/2 to Apple's servers (ADR-P11-002)
- **FCMProvider** uses Firebase Admin SDK for Android
- **PushDispatchService** unifies routing with parallel dispatch
- **Device model** stores encrypted push tokens
- Extends existing **WebPushService** and **NotificationPreferences**

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs |
|----------------|----------------|--------|---------|
| `APNSProvider` | iOS push delivery | Token, payload | DeliveryResult |
| `FCMProvider` | Android push delivery | Token, payload | DeliveryResult |
| `PushDispatchService` | Route to providers | User ID, notification | DispatchResult |
| `TokenManager` | Token lifecycle | Token operations | CRUD results |
| `devices.py` router | Device registration API | Requests | Device records |
| Device model | Token storage | Device data | Encrypted storage |

### Data Models and Contracts

**Device Model:**

```python
class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    device_id = Column(String(255), unique=True, nullable=False)
    platform = Column(String(20), nullable=False)  # ios, android, web
    name = Column(String(100))
    push_token = Column(Text)  # Fernet encrypted
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="devices")
```

**NotificationPreferences Extensions:**

```python
# Add to existing NotificationPreferences
quiet_hours_start = Column(Time)  # e.g., 22:00
quiet_hours_end = Column(Time)    # e.g., 07:00
quiet_hours_timezone = Column(String(50))  # e.g., "America/Chicago"
quiet_hours_enabled = Column(Boolean, default=False)
quiet_hours_override_critical = Column(Boolean, default=True)
```

**APNS Configuration:**

```python
class APNSConfig(BaseModel):
    team_id: str
    key_id: str
    key_path: str  # Path to .p8 file
    bundle_id: str
    sandbox: bool = False
```

**FCM Configuration:**

```python
class FCMConfig(BaseModel):
    project_id: str
    credentials_path: str  # Path to service account JSON
```

**Delivery Result:**

```python
class DeliveryResult(BaseModel):
    success: bool
    message_id: Optional[str]
    error: Optional[str]
    token_invalid: bool = False
```

### APIs and Interfaces

**POST /api/v1/devices** - Register device

```yaml
Request:
  {
    "device_id": "uuid-from-device",
    "platform": "ios",
    "name": "iPhone 15 Pro",
    "push_token": "apns-token-hex"
  }

Response 201:
  {
    "id": "device-uuid",
    "device_id": "uuid-from-device",
    "platform": "ios",
    "name": "iPhone 15 Pro",
    "last_seen_at": "2025-12-25T10:30:00Z",
    "created_at": "2025-12-25T10:30:00Z"
  }
```

**GET /api/v1/devices** - List user's devices

```yaml
Response 200:
  {
    "devices": [
      {
        "id": "device-uuid",
        "device_id": "uuid-from-device",
        "platform": "ios",
        "name": "iPhone 15 Pro",
        "last_seen_at": "2025-12-25T10:30:00Z"
      }
    ]
  }
```

**DELETE /api/v1/devices/{device_id}** - Remove device

```yaml
Response 204: (no content)
```

**PUT /api/v1/devices/{device_id}/token** - Update push token

```yaml
Request:
  {
    "push_token": "new-apns-token-hex"
  }

Response 200:
  {
    "success": true
  }
```

### Workflows and Sequencing

**Device Registration Flow:**

```
1. Mobile app obtains push token (APNS/FCM)
2. App calls POST /api/v1/devices with token
3. Backend validates request
4. Encrypt push_token with Fernet
5. Upsert device record (by device_id)
6. Return device info (without token)
```

**Notification Dispatch Flow:**

```
1. Event detected → EventProcessor triggers notification
2. PushDispatchService.dispatch(user_id, notification)
3. Load user's devices and preferences
4. Check quiet hours (timezone-aware)
   - If quiet and not critical → skip, return skipped result
5. For each device (parallel):
   - web → WebPushService.send()
   - ios → APNSProvider.send()
   - android → FCMProvider.send()
6. Collect results, handle failures:
   - token_invalid → mark for cleanup
   - transient error → queue for retry
7. Return DispatchResult with success/failure counts
```

**APNS Send Flow:**

```
1. Generate JWT (ES256 with p8 key)
   - iss: team_id, iat: now, kid: key_id
2. Build payload:
   {
     "aps": {
       "alert": { "title": "...", "body": "..." },
       "sound": "default",
       "mutable-content": 1
     },
     "event_id": "...",
     "thumbnail_url": "..."
   }
3. POST to api.push.apple.com/3/device/{token}
   - Headers: apns-topic, apns-push-type, authorization
4. Handle response:
   - 200 → success
   - 400 BadDeviceToken → token_invalid
   - 410 Unregistered → token_invalid
   - 429/503 → retry with backoff
```

**FCM Send Flow:**

```
1. Build Message object:
   - notification: title, body, image
   - data: event_id, camera_name, etc.
   - android: priority=high, channel_id
2. Call messaging.send(message)
3. Handle exceptions:
   - UnregisteredError → token_invalid
   - QuotaExceeded → log, skip
   - Other → retry with backoff
```

**Quiet Hours Check:**

```python
def is_quiet_hours(prefs: NotificationPreferences, now: datetime) -> bool:
    if not prefs.quiet_hours_enabled:
        return False

    user_tz = pytz.timezone(prefs.quiet_hours_timezone)
    user_now = now.astimezone(user_tz).time()

    start = prefs.quiet_hours_start
    end = prefs.quiet_hours_end

    if start <= end:
        # Same day: e.g., 22:00-23:00
        return start <= user_now <= end
    else:
        # Overnight: e.g., 22:00-07:00
        return user_now >= start or user_now <= end
```

## Non-Functional Requirements

### Performance

| Metric | Target | Source |
|--------|--------|--------|
| Push dispatch latency | <100ms | Internal |
| APNS delivery | <1s | Apple SLA |
| FCM delivery | <1s | Google SLA |
| Event-to-notification | <3s | NFR2 |
| Parallel dispatch | 100 concurrent | NFR14 |

### Security

- **NFR6**: APNS/FCM credentials stored encrypted at rest
- **NFR8**: Device tokens validated before push delivery
- Push tokens encrypted with Fernet before storage
- Service account/p8 files stored outside webroot
- API authentication required for device endpoints

### Reliability/Availability

- **NFR11**: Push delivery retries up to 3 times with backoff
- **NFR13**: Device registration survives server restarts
- Token invalidation cleanup prevents stale deliveries
- Fail-open: event processing continues if push fails

### Observability

- Structured logging:
  - `push.dispatched`: user_id, device_count, platforms
  - `push.delivered`: device_id, platform, latency_ms
  - `push.failed`: device_id, platform, error
  - `push.token_invalid`: device_id, platform
- Prometheus metrics:
  - `argusai_push_sent_total{platform,status}`
  - `argusai_push_latency_seconds{platform}`
  - `argusai_push_devices_total{platform}`

## Dependencies and Integrations

| Dependency | Version | Purpose |
|------------|---------|---------|
| httpx | 0.26+ | APNS HTTP/2 client |
| PyJWT | 2.8+ | APNS JWT generation |
| cryptography | existing | ES256 signing, Fernet |
| firebase-admin | 6.4+ | FCM HTTP v1 API |
| pytz | existing | Timezone handling |

**External Integrations:**
- Apple Developer account for APNS credentials
- Firebase project for FCM credentials

## Acceptance Criteria (Authoritative)

1. **AC-2.1.1**: APNSProvider connects via HTTP/2 to Apple's servers
2. **AC-2.1.2**: APNS authentication uses p8 auth key file
3. **AC-2.1.3**: Configuration stores key_id, team_id, key_file path
4. **AC-2.1.4**: Payloads formatted per Apple's notification format
5. **AC-2.1.5**: Error responses handled (invalid token, etc.)
6. **AC-2.1.6**: Token invalidation removes stale device tokens
7. **AC-2.2.1**: FCMProvider connects to FCM HTTP v1 API
8. **AC-2.2.2**: FCM authentication uses service account JSON
9. **AC-2.2.3**: Configuration stores service account path securely
10. **AC-2.2.4**: Payloads formatted per FCM notification format
11. **AC-2.2.5**: Data messages supported for background processing
12. **AC-2.2.6**: Error responses handled (invalid token, quota)
13. **AC-2.3.1**: PushDispatchService routes to WebPush, APNS, FCM
14. **AC-2.3.2**: Service queries device tokens by user_id
15. **AC-2.3.3**: Notifications sent to all devices in parallel
16. **AC-2.3.4**: Retry logic with exponential backoff (max 3)
17. **AC-2.3.5**: Delivery status tracked per device
18. **AC-2.3.6**: Notification preferences applied before dispatch
19. **AC-2.4.1**: Device model stores device_id, platform, name, push_token, user_id, last_seen
20. **AC-2.4.2**: POST `/api/v1/devices` registers new device
21. **AC-2.4.3**: GET `/api/v1/devices` lists user's devices
22. **AC-2.4.4**: DELETE `/api/v1/devices/{id}` revokes device
23. **AC-2.4.5**: Device tokens encrypted at rest
24. **AC-2.4.6**: Duplicate device_id updates existing record
25. **AC-2.5.1**: User can set quiet hours start and end time
26. **AC-2.5.2**: Quiet hours respect user's timezone
27. **AC-2.5.3**: Notifications suppressed during quiet hours
28. **AC-2.5.4**: Override option for critical alerts
29. **AC-2.5.5**: Per-device quiet hours supported
30. **AC-2.6.1**: iOS notifications include image attachment
31. **AC-2.6.2**: Android notifications include BigPicture style
32. **AC-2.6.3**: Thumbnail URL accessible via signed temporary link
33. **AC-2.6.4**: Images optimized for notification display
34. **AC-2.6.5**: Fallback to text-only if image unavailable

## Traceability Mapping

| AC | Spec Section | Component | Test Idea |
|----|--------------|-----------|-----------|
| AC-2.1.1-6 | Services/APNSProvider | apns_provider.py | Unit: mock HTTP/2, verify JWT |
| AC-2.2.1-6 | Services/FCMProvider | fcm_provider.py | Unit: mock firebase, verify message |
| AC-2.3.1-6 | Services/Dispatch | dispatch_service.py | Unit: routing logic, parallel send |
| AC-2.4.1-6 | APIs/Data Models | devices.py, Device | API: CRUD tests, encryption |
| AC-2.5.1-5 | Workflows/QuietHours | NotificationPreferences | Unit: timezone edge cases |
| AC-2.6.1-5 | Services/Attachments | APNSPayload, FCMPayload | Integration: verify attachment delivery |

## Risks, Assumptions, Open Questions

### Risks

- **R1**: APNS certificate/key management complexity
  - *Mitigation*: Clear documentation, validation on startup
- **R2**: FCM quota limits for high-volume users
  - *Mitigation*: Monitor quotas, implement backpressure
- **R3**: HTTP/2 connection pooling issues
  - *Mitigation*: Use httpx with connection limits

### Assumptions

- **A1**: Users will configure APNS/FCM credentials correctly
- **A2**: Mobile app (future) will provide valid device tokens
- **A3**: Event thumbnails are accessible via URL

### Open Questions

- **Q1**: How to test without native mobile app?
  - *Decision*: Use Postman/curl to simulate device registration, verify push delivery via APNS/FCM testing tools
- **Q2**: Should we support topic-based subscriptions?
  - *Decision*: Defer to future - start with per-user delivery

## Test Strategy Summary

### Unit Tests

- APNSProvider: JWT generation, payload formatting, error handling
- FCMProvider: Message building, error handling
- PushDispatchService: Routing logic, parallel dispatch, retry
- Device model: Encryption/decryption, upsert logic
- Quiet hours: Timezone calculations, edge cases

### Integration Tests

- Device API: Registration, listing, deletion
- End-to-end dispatch with mocked providers
- Token cleanup on invalidation

### Manual Testing

- Register real iOS device via Apple Developer testing
- Register real Android device via Firebase testing
- Verify notification appearance and actions

### Test Coverage Target

- Backend: 85%+ for push/ directory
- API endpoints: 100% coverage
