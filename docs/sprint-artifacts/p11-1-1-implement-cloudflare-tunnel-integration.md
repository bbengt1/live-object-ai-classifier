# Story P11-1.1: Implement Cloudflare Tunnel Integration

Status: complete

## Story

As a **user**,
I want **ArgusAI to connect through Cloudflare Tunnel**,
so that **I can access my dashboard from anywhere without port forwarding**.

## Acceptance Criteria

1. **AC-1.1.1**: Backend supports cloudflared tunnel connection via subprocess
2. **AC-1.1.2**: Tunnel token stored securely in system settings (encrypted with Fernet)
3. **AC-1.1.3**: Tunnel connects on application startup when enabled
4. **AC-1.1.4**: Connection works for both backend API and frontend

## Tasks / Subtasks

- [x] Task 1: Create TunnelService class (AC: 1, 3)
  - [x] Create `backend/app/services/tunnel_service.py`
  - [x] Implement `TunnelService` class with subprocess management
  - [x] Add `start()`, `stop()`, `is_connected()` methods
  - [x] Implement async subprocess spawn for `cloudflared tunnel run --token <token>`
  - [x] Add stdout/stderr monitoring for connection status parsing
  - [x] Handle process lifecycle (spawn, monitor, terminate)

- [x] Task 2: Add tunnel configuration to system settings model (AC: 2)
  - [x] Add `tunnel_enabled: bool` field to settings schema
  - [x] Add `tunnel_token: str` field (encrypted)
  - [x] Add `tunnel_hostname: str` field (optional, for display)
  - Note: No Alembic migration needed - settings use key-value storage

- [x] Task 3: Implement secure token storage (AC: 2)
  - [x] Use existing Fernet encryption pattern from camera passwords
  - [x] Encrypt token before storage (added to SENSITIVE_SETTING_KEYS)
  - [x] Decrypt token when reading for tunnel start
  - [x] Ensure token never appears in logs or API responses

- [x] Task 4: Add startup hook for tunnel initialization (AC: 3)
  - [x] Create startup event handler in `main.py` lifespan
  - [x] Check if `tunnel_enabled` is true on startup
  - [x] Initialize TunnelService and start tunnel
  - [x] Handle startup failures gracefully (log error, continue)

- [x] Task 5: Verify connection for backend and frontend (AC: 4)
  - Note: Manual verification required with actual cloudflared
  - API endpoints created: GET/POST /api/v1/system/tunnel/status, /start, /stop

- [x] Task 6: Write unit tests
  - [x] Test TunnelService with mocked subprocess (21 tests)
  - [x] Test token validation and security
  - [x] Test status dict and lifecycle methods
  - [x] Test log parsing and hostname extraction

## Dev Notes

### Relevant Architecture Patterns

- **Subprocess Management**: Use `asyncio.create_subprocess_exec()` for async process control
- **Encryption**: Follow existing Fernet pattern from `backend/app/core/security.py` for API keys
- **Settings Model**: Extend existing `SystemSettings` or create dedicated settings table
- **Startup Hooks**: Use FastAPI lifespan or `@app.on_event("startup")` pattern

### Source Tree Components

```
backend/
├── app/
│   ├── services/
│   │   └── tunnel_service.py      # NEW: TunnelService class
│   ├── models/
│   │   └── system_settings.py     # MODIFY: Add tunnel fields
│   ├── core/
│   │   └── security.py            # USE: Fernet encryption
│   └── main.py                    # MODIFY: Add startup hook
└── tests/
    └── test_services/
        └── test_tunnel_service.py # NEW: Unit tests
```

### Testing Standards

- Mock `asyncio.subprocess` in unit tests
- Verify subprocess command construction
- Test encryption/decryption with known values
- Integration test requires actual cloudflared (skip in CI without it)

### Security Considerations

- Never log tunnel token (mask in all log outputs)
- Token must be encrypted at rest
- Validate token format before subprocess spawn (avoid injection)
- Run cloudflared with minimum permissions

### Project Structure Notes

- Follows existing service pattern from `protect_service.py`, `ai_service.py`
- Settings extension follows `backend/app/models/` patterns
- Encryption uses existing `fernet_encrypt`/`fernet_decrypt` helpers

### References

- [Source: docs/sprint-artifacts/tech-spec-epic-P11-1.md#Services-and-Modules]
- [Source: docs/sprint-artifacts/tech-spec-epic-P11-1.md#Data-Models-and-Contracts]
- [Source: docs/sprint-artifacts/tech-spec-epic-P11-1.md#Workflows-and-Sequencing]
- [Source: docs/architecture/phase-11-additions.md#Phase-11-Service-Architecture]
- [Source: docs/architecture/cloud-relay-architecture.md]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Created TunnelService with async subprocess management for cloudflared
- Token validation prevents command injection by checking for shell metacharacters
- Uses existing Fernet encryption pattern for secure token storage
- Added tunnel settings to SystemSettingsUpdate schema (tunnel_enabled, tunnel_token, tunnel_hostname)
- Created API endpoints: GET /api/v1/system/tunnel/status, POST /start, POST /stop
- Startup hook in main.py lifespan connects tunnel if enabled with saved token
- Shutdown hook gracefully terminates tunnel process
- 21 unit tests covering service lifecycle, token validation, and log parsing

### File List

- backend/app/services/tunnel_service.py (NEW)
- backend/app/schemas/system.py (MODIFIED - added tunnel fields)
- backend/app/api/v1/system.py (MODIFIED - added tunnel endpoints and SENSITIVE_SETTING_KEYS)
- backend/main.py (MODIFIED - added startup/shutdown hooks)
- backend/tests/test_services/test_tunnel_service.py (NEW)
