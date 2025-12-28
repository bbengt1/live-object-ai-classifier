# ArgusAI - Product Requirements Document

**Author:** Brent
**Date:** 2025-12-28
**Version:** 1.0
**Phase:** 13 - Platform Maturity & External Integration

---

## Executive Summary

Phase 13 transforms ArgusAI from a capable home security AI into a **mature, externally-accessible platform**. This phase addresses the critical gap between ArgusAI's powerful local capabilities and the need for secure external access, third-party integrations, and professional polish.

After 12 phases of feature development, ArgusAI now has comprehensive AI-powered event detection, entity recognition, push notifications, and native Apple apps. Phase 13 completes the platform story by enabling:

- **Secure programmatic access** via API keys for automation and integrations
- **Remote connectivity** via cloud relay for accessing ArgusAI from anywhere
- **Accelerated development** via n8n automation pipelines
- **Improved data quality** via bulk entity reprocessing
- **Professional identity** via consistent branding across all touchpoints

### What Makes This Special

Phase 13 is about **opening ArgusAI to the world** while maintaining security and privacy. The API key system enables a new class of integrations - home automation scripts, third-party dashboards, and custom alerting systems can now securely interact with ArgusAI. The cloud relay solves the "works great at home, can't access remotely" problem that limits most self-hosted solutions.

---

## Project Classification

**Technical Type:** Full-Stack Web Application (Python/FastAPI + Next.js)
**Domain:** Home Security / IoT / AI Vision
**Complexity:** Medium-High (security-sensitive APIs, cloud infrastructure, branding assets)

This phase is primarily **infrastructure and integration focused** rather than feature-focused. It extends the platform's reach and polish rather than adding new detection capabilities.

---

## Success Criteria

### Primary Success Metrics

1. **API Key Adoption**: At least 3 active API keys created and used for external integrations within 30 days of release
2. **Remote Access Reliability**: Cloud relay maintains 99%+ uptime with <500ms added latency for remote connections
3. **Entity Data Quality**: 80%+ of historical events successfully reprocessed and matched to entities
4. **Brand Consistency**: Logo appears correctly across all 6 touchpoints (web app, docs site, PWA, iOS, macOS, social previews)
5. **Development Velocity**: n8n pipeline reduces manual development steps by 50%+

### Quality Gates

- Zero security vulnerabilities in API key implementation (validated by security review)
- Cloud relay supports concurrent connections from multiple devices
- Reprocessing handles 10,000+ events without timeout or memory issues
- All logo assets pass accessibility contrast requirements

---

## Product Scope

### MVP - Phase 13 Core Deliverables

**1. API Key Management (FF-033) - P2**
- Create, list, and revoke API keys via Settings UI
- Scoped permissions (read:events, write:cameras, admin)
- API key authentication middleware
- Usage logging and rate limiting

**2. Cloud Relay for Remote Access (FF-025) - P3**
- Cloudflare Tunnel integration for NAT traversal
- Secure WebSocket relay for real-time updates
- Device authentication and pairing
- Fallback to local network when available

**3. Reprocess Events for Entity Matching (FF-034) - P3**
- Bulk reprocessing endpoint with filters
- Background task with progress tracking
- WebSocket progress updates
- UI button in Settings or Events page

**4. ArgusAI Branding (IMP-039) - P3**
- Export logo in all required sizes
- Update frontend favicon and PWA icons
- Update docs-site branding
- Open Graph images for social sharing

**5. n8n Development Pipeline (FF-027) - P2**
- Self-hosted n8n instance configuration
- BMAD workflow integration (create-story, dev-story, code-review)
- GitHub Actions integration
- Slack/Discord notifications

### Growth Features (Post-Phase 13)

- API key auto-rotation and expiration policies
- Cloud relay with video streaming optimization
- n8n workflows for automated testing and deployment
- Entity reprocessing with ML model updates
- Animated logo variants for loading states

### Vision (Future)

- Public API with developer portal and documentation
- Multi-tenant cloud relay service
- Full CI/CD automation via n8n
- White-label branding options
- API marketplace for third-party integrations

---

## Functional Requirements

### API Key Management

- **FR1**: Administrators can generate new API keys with a descriptive name
- **FR2**: API keys are displayed only once at creation time (never retrievable again)
- **FR3**: Administrators can view a list of all API keys showing prefix, name, created date, last used, and status
- **FR4**: Administrators can revoke API keys immediately
- **FR5**: API keys can be scoped to specific permissions (read:events, read:cameras, write:cameras, admin)
- **FR6**: External systems can authenticate using API keys in the Authorization header
- **FR7**: API key usage is logged with timestamp, endpoint, and IP address
- **FR8**: API keys can have optional expiration dates
- **FR9**: Rate limiting is applied per API key (configurable limits)
- **FR10**: Revoked or expired API keys return 401 Unauthorized

### Cloud Relay & Remote Access

- **FR11**: Users can configure Cloudflare Tunnel credentials in Settings
- **FR12**: System establishes secure tunnel connection on startup when enabled
- **FR13**: Remote clients can connect to ArgusAI via the tunnel URL
- **FR14**: WebSocket connections are relayed for real-time event updates
- **FR15**: System automatically falls back to local network when available
- **FR16**: Tunnel status is displayed in Settings with connection health
- **FR17**: Users can test tunnel connectivity from Settings
- **FR18**: Remote sessions are authenticated using existing auth mechanisms

### Event Entity Reprocessing

- **FR19**: Administrators can trigger bulk entity reprocessing from Settings or Events page
- **FR20**: Reprocessing accepts optional filters (date range, camera, events without entities only)
- **FR21**: System displays estimated event count before starting reprocess
- **FR22**: Reprocessing runs as background task without blocking UI
- **FR23**: Progress is reported via WebSocket (events processed, entities matched, errors)
- **FR24**: Users can cancel in-progress reprocessing
- **FR25**: Reprocessing generates embeddings for events missing them
- **FR26**: Matched entities are updated in event records

### Branding & Visual Identity

- **FR27**: ArgusAI logo appears as favicon in web browsers
- **FR28**: ArgusAI logo appears in PWA manifest icons (all required sizes)
- **FR29**: ArgusAI logo appears in docs-site header and favicon
- **FR30**: ArgusAI logo appears in Open Graph meta tags for social sharing
- **FR31**: Apple touch icon uses ArgusAI logo
- **FR32**: Logo is consistent across light and dark themes

### n8n Development Pipeline

- **FR33**: n8n instance can be deployed via Docker Compose
- **FR34**: n8n workflows can trigger BMAD create-story workflow
- **FR35**: n8n workflows can trigger BMAD dev-story workflow
- **FR36**: n8n workflows can trigger BMAD code-review workflow
- **FR37**: n8n can receive GitHub webhook events (push, PR, issues)
- **FR38**: n8n can send notifications to Slack or Discord
- **FR39**: n8n dashboard displays pipeline status and metrics
- **FR40**: Human approval gates can pause pipeline execution

---

## Non-Functional Requirements

### Security

- **NFR1**: API keys must be hashed using bcrypt or Argon2 before storage (never stored in plaintext)
- **NFR2**: API key prefixes (first 8 chars) are stored separately for identification
- **NFR3**: All API key operations require admin authentication
- **NFR4**: Rate limiting prevents brute force attacks on API endpoints (max 100 requests/minute per key)
- **NFR5**: Cloud relay connections use TLS 1.3 encryption
- **NFR6**: Tunnel credentials are stored encrypted using Fernet
- **NFR7**: API key audit logs are retained for 90 days minimum

### Performance

- **NFR8**: API key authentication adds <10ms latency to requests
- **NFR9**: Cloud relay adds <500ms latency for remote connections
- **NFR10**: Entity reprocessing handles 100 events/second minimum
- **NFR11**: Reprocessing progress updates emit every 1 second or 100 events (whichever comes first)
- **NFR12**: n8n workflows complete story creation in <30 seconds

### Reliability

- **NFR13**: Cloud relay automatically reconnects after network interruptions
- **NFR14**: Reprocessing is resumable after server restart (tracks progress in database)
- **NFR15**: API key revocation takes effect immediately (no caching delay)

### Integration

- **NFR16**: API keys work with existing REST API endpoints without modification
- **NFR17**: n8n integrates with Claude Code CLI via subprocess execution
- **NFR18**: n8n integrates with GitHub Actions via webhooks
- **NFR19**: Cloudflare Tunnel follows standard cloudflared configuration patterns

---

## Implementation Planning

### Epic Breakdown

Phase 13 decomposes into **5 epics** aligned with the backlog items:

| Epic | Backlog ID | Priority | Estimated Stories |
|------|------------|----------|-------------------|
| P13-1: API Key Management | FF-033 | P2 | 5-7 stories |
| P13-2: Cloud Relay | FF-025 | P3 | 4-6 stories |
| P13-3: Entity Reprocessing | FF-034 | P3 | 3-4 stories |
| P13-4: Branding | IMP-039 | P3 | 2-3 stories |
| P13-5: n8n Pipeline | FF-027 | P2 | 5-7 stories |

**Total Estimated Stories:** 19-27

### Suggested Implementation Order

1. **P13-4: Branding** (Quick win, visual impact, no dependencies)
2. **P13-1: API Key Management** (Core security infrastructure)
3. **P13-3: Entity Reprocessing** (Improves existing data quality)
4. **P13-2: Cloud Relay** (Builds on API key auth)
5. **P13-5: n8n Pipeline** (Development tooling, can be parallel)

### Dependencies

- Cloud Relay depends on API Key Management for external authentication
- n8n Pipeline is independent and can be developed in parallel
- Branding has no dependencies
- Entity Reprocessing has no dependencies

---

## API Endpoints (Planned)

### API Key Management
```
POST   /api/v1/api-keys              # Create new API key
GET    /api/v1/api-keys              # List all API keys
DELETE /api/v1/api-keys/{id}         # Revoke API key
GET    /api/v1/api-keys/{id}/usage   # Get usage stats
```

### Entity Reprocessing
```
POST   /api/v1/events/reprocess-entities     # Start reprocessing
GET    /api/v1/events/reprocess-entities     # Get reprocessing status
DELETE /api/v1/events/reprocess-entities     # Cancel reprocessing
```

### Cloud Relay
```
GET    /api/v1/system/tunnel-status          # Get tunnel status
POST   /api/v1/system/tunnel/test            # Test tunnel connectivity
```

---

## References

- Product Brief: docs/product-brief.md
- Backlog: docs/backlog.md
- Architecture: docs/architecture.md
- Cloud Relay Design: docs/architecture/cloud-relay-architecture.md

---

## Summary

Phase 13 delivers **platform maturity** through:

| Feature | Value Delivered |
|---------|-----------------|
| API Keys | Secure third-party integrations and automation |
| Cloud Relay | Access ArgusAI from anywhere in the world |
| Entity Reprocessing | Improve historical data quality |
| Branding | Professional, consistent visual identity |
| n8n Pipeline | Accelerated AI-assisted development |

**40 Functional Requirements** | **19 Non-Functional Requirements** | **5 Epics** | **~23 Stories**

---

_This PRD captures Phase 13 of ArgusAI - Platform Maturity & External Integration_

_Created through collaborative discovery between Brent and AI facilitator on 2025-12-28._
