# Story P5-6.1: Add MQTT 5.0 Message Expiry Support

Status: review

## Story

As a home automation user,
I want MQTT event messages to expire after a configurable time,
so that stale events don't accumulate on the broker and Home Assistant receives only relevant, timely notifications.

## Acceptance Criteria

1. Event messages include MessageExpiryInterval property when published to MQTT 5.0 brokers
2. Expiry time configurable in MQTT settings with default of 300 seconds (5 minutes)
3. Settings UI shows expiry time input with validation (60-3600 seconds range)
4. Messages published to MQTT 5.0 broker include expiry property
5. Messages not consumed within TTL are discarded by broker
6. Works gracefully with MQTT 3.1.1 brokers (expiry property ignored, no errors)

## Tasks / Subtasks

- [x] Task 1: Add message_expiry_seconds field to MQTT configuration (AC: 2, 6)
  - [x] 1.1: Create Alembic migration to add `message_expiry_seconds` column to `mqtt_config` table (default 300)
  - [x] 1.2: Update MQTTConfig model with new field and validation (60-3600 range)
  - [x] 1.3: Update MQTT config schemas for API request/response
  - [x] 1.4: Add field to MQTTConfigUpdate schema and API endpoint

- [x] Task 2: Implement MQTT 5.0 message expiry in publish method (AC: 1, 4, 5)
  - [x] 2.1: Update mqtt_service.py to use MQTT 5.0 protocol when connecting
  - [x] 2.2: Modify publish() method to include MessageExpiryInterval property
  - [x] 2.3: Import and use paho.mqtt.properties.Properties for MQTT 5.0 properties
  - [x] 2.4: Ensure expiry property is set from config's message_expiry_seconds value

- [x] Task 3: Ensure graceful fallback for MQTT 3.1.1 brokers (AC: 6)
  - [x] 3.1: Add protocol version detection/handling in connect method
  - [x] 3.2: Test that connection and publish work with MQTT 3.1.1 brokers
  - [x] 3.3: Log warning if MQTT 5.0 features unavailable but don't fail

- [x] Task 4: Update frontend MQTT settings UI (AC: 3)
  - [x] 4.1: Add message_expiry_seconds input field to MQTTSettings.tsx
  - [x] 4.2: Add Zod validation schema for expiry field (60-3600 range)
  - [x] 4.3: Add helpful description text explaining message expiry
  - [x] 4.4: Update frontend types for MQTTConfigUpdate

- [x] Task 5: Write tests for message expiry functionality (All ACs)
  - [x] 5.1: Add unit test for MQTTConfig model with expiry field validation
  - [x] 5.2: Add unit test for publish method with expiry property
  - [x] 5.3: Add API test for updating message_expiry_seconds setting

## Dev Notes

### Relevant Architecture Patterns

**MQTT Service Architecture (Phase 4):**
- Existing `mqtt_service.py` uses paho-mqtt 2.0+ with CallbackAPIVersion.VERSION2
- Currently connects using `mqtt.MQTTv311` protocol - needs update to `mqtt.MQTTv5`
- Service already handles Will message (LWT) for availability

**MQTT 5.0 Message Expiry Implementation:**
```python
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes

# Create properties with expiry
props = Properties(PacketTypes.PUBLISH)
props.MessageExpiryInterval = settings.message_expiry_seconds

# Publish with properties
client.publish(topic, payload, qos=qos, retain=retain, properties=props)
```

**Database Schema Change:**
```sql
ALTER TABLE mqtt_config ADD COLUMN message_expiry_seconds INTEGER NOT NULL DEFAULT 300;
```

### Project Structure Notes

Files to modify:
- `backend/app/models/mqtt_config.py` - Add message_expiry_seconds field
- `backend/app/services/mqtt_service.py` - Add MQTT 5.0 protocol and expiry properties
- `backend/app/schemas/mqtt.py` - Update request/response schemas
- `backend/alembic/versions/` - New migration for database column
- `frontend/components/settings/MQTTSettings.tsx` - Add expiry configuration UI
- `frontend/types/settings.ts` - Update TypeScript types

### Protocol Compatibility Notes

- MQTT 5.0 is required for message expiry feature
- paho-mqtt 2.0+ supports MQTT 5.0 via `protocol=mqtt.MQTTv5`
- When connecting to MQTT 3.1.1 broker with MQTTv5 protocol:
  - Connection may be refused or downgraded
  - Need to handle gracefully without breaking functionality
- Mosquitto 2.0+ supports MQTT 5.0 (most Home Assistant setups use this)

### Learnings from Previous Story

**From Story p5-5-5-update-readme-with-frontend-setup-docs (Status: done)**

- **Documentation standards**: README should have clear sections with code blocks
- **No architectural changes**: Previous story was docs-only, no code changes to reference
- **Test verification**: `npm run lint` should pass before completion

[Source: docs/sprint-artifacts/p5-5-5-update-readme-with-frontend-setup-docs.md#Dev-Agent-Record]

### References

- [Source: docs/epics-phase5.md#P5-6.1] - Story definition and acceptance criteria
- [Source: docs/sprint-artifacts/tech-spec-epic-p5-6.md] - Technical specification
- [Source: docs/backlog.md#FF-012] - Feature request (GitHub Issue #37)
- [Source: docs/architecture/phase-4-additions.md#MQTT] - MQTT architecture
- [Source: backend/app/services/mqtt_service.py] - Current MQTT implementation
- [Source: backend/app/models/mqtt_config.py] - Current MQTT config model

## Dev Agent Record

### Context Reference

- docs/sprint-artifacts/p5-6-1-add-mqtt-5-0-message-expiry-support.context.xml

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Implemented MQTT 5.0 protocol support with message expiry (MessageExpiryInterval property)
- Added graceful fallback: if broker returns reason code 132 (Unsupported Protocol Version), service downgrades to MQTT 3.1.1
- Database migration adds `message_expiry_seconds` column with default 300 seconds
- Model validation ensures expiry is within 60-3600 second range
- Frontend UI includes input field with description explaining the feature
- All 46 MQTT service tests pass, including new tests for message expiry

### File List

**New Files:**
- backend/alembic/versions/046_add_mqtt_message_expiry.py

**Modified Files:**
- backend/app/models/mqtt_config.py
- backend/app/services/mqtt_service.py
- backend/app/api/v1/integrations.py
- backend/tests/test_services/test_mqtt_service.py
- frontend/components/settings/MQTTSettings.tsx
- frontend/types/settings.ts
- frontend/__tests__/components/settings/MQTTSettings.test.tsx

## Change Log

| Date | Change |
|------|--------|
| 2025-12-16 | Story drafted from epics-phase5.md and tech-spec-epic-p5-6.md |
| 2025-12-16 | Implementation complete - all tasks and ACs satisfied |
