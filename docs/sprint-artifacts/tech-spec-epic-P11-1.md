# Epic Technical Specification: Remote Access via Cloudflare Tunnel

Date: 2025-12-25
Author: Brent
Epic ID: P11-1
Status: Draft

---

## Overview

Epic P11-1 implements secure remote access to ArgusAI via Cloudflare Tunnel, enabling users to access their security dashboard from anywhere without VPN or port forwarding. This builds on the cloud relay architecture designed in Phase 10 (P10-5.3), delivering the actual implementation of tunnel connectivity, status monitoring, UI configuration, and user documentation.

The tunnel integration enables ArgusAI to break free from local network constraints while maintaining security through Cloudflare's Zero Trust architecture.

## Objectives and Scope

### In Scope

- Cloudflare Tunnel integration via `cloudflared` daemon management
- Secure tunnel token storage with Fernet encryption
- Auto-reconnection on network changes or failures
- Tunnel status API endpoint (`/api/v1/system/tunnel-status`)
- Settings UI for tunnel configuration (enable/disable, token input)
- Status indicator showing connection state
- User documentation for tunnel setup

### Out of Scope

- Custom domain configuration (user responsibility)
- Cloudflare Zero Trust policies (user responsibility)
- Alternative tunnel providers (ngrok, frp, etc.)
- Mobile app integration with tunnel (Phase 11+ scope)

## System Architecture Alignment

This epic implements the cloud relay architecture from `docs/architecture/cloud-relay-architecture.md`:

- **TunnelService** class manages `cloudflared` subprocess lifecycle
- **System Settings** stores encrypted tunnel token
- **Health endpoint** reports tunnel connectivity
- **ADR-P11-001** rationale: Cloudflare Tunnel chosen for zero-cost, zero-infrastructure solution

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs |
|----------------|----------------|--------|---------|
| `TunnelService` | Manage cloudflared lifecycle | Tunnel token | Connection status |
| `tunnel.py` router | API endpoints for status | Request | Status JSON |
| `TunnelSettings.tsx` | UI configuration | User input | Settings update |
| System Settings model | Store tunnel config | Token | Encrypted storage |

### Data Models and Contracts

**System Settings Extensions:**

```python
# Add to existing SystemSettings model
class SystemSettings(Base):
    # Existing fields...

    # Tunnel configuration (P11-1)
    tunnel_enabled = Column(Boolean, default=False)
    tunnel_token = Column(Text)  # Fernet encrypted
    tunnel_hostname = Column(String(255))  # Optional: for display
```

**Tunnel Status Response:**

```python
class TunnelStatusResponse(BaseModel):
    enabled: bool
    connected: bool
    tunnel_id: Optional[str]
    hostname: Optional[str]
    last_connected: Optional[datetime]
    error: Optional[str]
    uptime_seconds: Optional[int]
```

### APIs and Interfaces

**GET /api/v1/system/tunnel-status**

```yaml
Response 200:
  {
    "enabled": true,
    "connected": true,
    "tunnel_id": "abc123-uuid",
    "hostname": "argusai.example.com",
    "last_connected": "2025-12-25T10:30:00Z",
    "error": null,
    "uptime_seconds": 3600
  }
```

**PUT /api/v1/system/settings** (extends existing)

```yaml
Request Body (partial):
  {
    "tunnel_enabled": true,
    "tunnel_token": "eyJhIjoiYWJj..."
  }
```

**POST /api/v1/system/tunnel/test**

```yaml
Response 200:
  {
    "success": true,
    "message": "Tunnel connected successfully",
    "hostname": "argusai.example.com"
  }

Response 400:
  {
    "success": false,
    "error": "Invalid tunnel token format"
  }
```

### Workflows and Sequencing

**Tunnel Startup Sequence:**

```
1. App startup → Load system settings
2. Check tunnel_enabled == true
3. Decrypt tunnel_token
4. Spawn cloudflared subprocess: `cloudflared tunnel run --token <token>`
5. Monitor stdout/stderr for connection status
6. Set TunnelService.connected = true on success
7. Start health check loop (every 30s)
```

**Reconnection Flow:**

```
1. Health check detects disconnect (process exit or timeout)
2. Log disconnect event
3. Wait backoff period (5s, 10s, 20s, 30s max)
4. Attempt reconnection
5. If 3 failures → set error state, continue monitoring
6. On success → reset backoff, log reconnect
```

**Settings Update Flow:**

```
1. User updates tunnel settings in UI
2. Frontend calls PUT /api/v1/system/settings
3. Backend validates token format
4. Encrypt and store token
5. If tunnel_enabled changed:
   - enabled=true → Start tunnel
   - enabled=false → Stop tunnel
6. Return success with new status
```

## Non-Functional Requirements

### Performance

| Metric | Target | Source |
|--------|--------|--------|
| Tunnel connection time | <5 seconds | NFR1 |
| Reconnection time | <30 seconds | NFR10 |
| Status API latency | <50ms | General |
| Settings update latency | <200ms | General |

### Security

- **NFR7**: Tunnel tokens never logged or exposed in API responses
- Token stored with Fernet encryption (existing pattern)
- Token input field uses `type="password"` with show/hide toggle
- Cloudflared runs with minimum necessary permissions
- Tunnel traffic encrypted via Cloudflare TLS

### Reliability/Availability

- **NFR10**: Auto-reconnect within 30 seconds of disconnect
- Exponential backoff prevents rapid retry storms
- Tunnel status reflects actual connection state
- Graceful degradation: local access works if tunnel fails

### Observability

- Structured logging for tunnel events:
  - `tunnel.connected`, `tunnel.disconnected`, `tunnel.reconnecting`
  - Include tunnel_id, duration, error details
- Prometheus metrics:
  - `argusai_tunnel_connected` (gauge: 0/1)
  - `argusai_tunnel_reconnect_total` (counter)
  - `argusai_tunnel_uptime_seconds` (gauge)

## Dependencies and Integrations

| Dependency | Version | Purpose |
|------------|---------|---------|
| cloudflared | 2024.x | Cloudflare Tunnel daemon |
| asyncio.subprocess | stdlib | Process management |
| cryptography (Fernet) | existing | Token encryption |

**External Integration:**
- Cloudflare Zero Trust dashboard for tunnel creation
- Cloudflare DNS for hostname routing

## Acceptance Criteria (Authoritative)

1. **AC-1.1.1**: Backend supports cloudflared tunnel connection via subprocess
2. **AC-1.1.2**: Tunnel token stored securely with Fernet encryption
3. **AC-1.1.3**: Tunnel connects on application startup when enabled
4. **AC-1.1.4**: Connection works for both backend API and frontend
5. **AC-1.2.1**: System monitors tunnel connection health every 30s
6. **AC-1.2.2**: Auto-reconnect triggers within 30 seconds of disconnect
7. **AC-1.2.3**: Connection events logged with structured format
8. **AC-1.2.4**: API endpoint `/api/v1/system/tunnel-status` returns state
9. **AC-1.3.1**: Settings > System tab includes Tunnel section
10. **AC-1.3.2**: Enable/disable toggle for tunnel
11. **AC-1.3.3**: Secure input field for tunnel token
12. **AC-1.3.4**: Status indicator shows connection state
13. **AC-1.3.5**: Test connection button validates setup
14. **AC-1.4.1**: Step-by-step guide for cloudflared installation
15. **AC-1.4.2**: Instructions for creating tunnel in Cloudflare dashboard
16. **AC-1.4.3**: Configuration guide for ArgusAI settings
17. **AC-1.4.4**: Troubleshooting section for common issues
18. **AC-1.4.5**: Security considerations documented

## Traceability Mapping

| AC | Spec Section | Component | Test Idea |
|----|--------------|-----------|-----------|
| AC-1.1.1 | Services/TunnelService | TunnelService.start() | Unit: mock subprocess, verify spawn |
| AC-1.1.2 | Data Models | SystemSettings.tunnel_token | Unit: encrypt/decrypt roundtrip |
| AC-1.1.3 | Workflows/Startup | app startup hook | Integration: start with token, verify connected |
| AC-1.1.4 | Architecture | Nginx/cloudflared | E2E: access via tunnel hostname |
| AC-1.2.1 | Workflows/Health | TunnelService._health_loop | Unit: verify interval, status update |
| AC-1.2.2 | Workflows/Reconnect | TunnelService._reconnect | Unit: mock failure, verify reconnect |
| AC-1.2.3 | Observability | Logging | Verify log output format |
| AC-1.2.4 | APIs | GET /tunnel-status | API: verify response schema |
| AC-1.3.1-5 | APIs/Frontend | TunnelSettings.tsx | Component: render, interaction tests |
| AC-1.4.1-5 | Documentation | docs/ | Manual: review docs for completeness |

## Risks, Assumptions, Open Questions

### Risks

- **R1**: cloudflared binary not installed on user system
  - *Mitigation*: Documentation covers installation, runtime check with clear error
- **R2**: Token format changes in future cloudflared versions
  - *Mitigation*: Minimal parsing, treat as opaque string
- **R3**: Subprocess management complexity on different OS
  - *Mitigation*: Use asyncio.subprocess, test on Linux/macOS

### Assumptions

- **A1**: Users have a Cloudflare account and domain
- **A2**: cloudflared is available in system PATH or specified path
- **A3**: ArgusAI server has outbound internet access on port 443

### Open Questions

- **Q1**: Should we bundle cloudflared binary or require external install?
  - *Decision*: External install (simpler, user controls updates)
- **Q2**: Support multiple tunnels for different services?
  - *Decision*: Single tunnel for MVP, expose all services

## Test Strategy Summary

### Unit Tests

- TunnelService: mock subprocess, verify start/stop/reconnect logic
- Encryption: roundtrip token encryption/decryption
- Status parsing: various cloudflared output formats

### Integration Tests

- API endpoints: status, settings update, test connection
- Settings persistence: enable/disable across restarts

### E2E Tests (Manual)

- Create tunnel in Cloudflare dashboard
- Configure token in ArgusAI
- Access dashboard via tunnel hostname
- Verify reconnection after network disruption

### Test Coverage Target

- Backend: 80%+ line coverage for TunnelService
- Frontend: Component tests for TunnelSettings
