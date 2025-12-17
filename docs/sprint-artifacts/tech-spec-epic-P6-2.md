# Epic Technical Specification: Accessibility Completion

Date: 2025-12-16
Author: Brent
Epic ID: P6-2
Status: Draft

---

## Overview

Epic P6-2 completes the remaining accessibility enhancements identified in backlog item IMP-004. Previous phases (P5-5.1 and P5-5.2) addressed ARIA labels and keyboard navigation; this epic focuses on the final items: skip-to-content links and a comprehensive accessibility audit.

These improvements ensure ArgusAI meets WCAG 2.1 Level AA compliance, making the application usable for keyboard-only users and those using assistive technologies like screen readers.

## Objectives and Scope

### In Scope
- **Story P6-2.1**: Implement skip-to-content link that appears on Tab at page top
- **Story P6-2.2**: Run accessibility audit with axe-core, fix all critical/serious issues

### Out of Scope
- WCAG AAA compliance (AAA is aspirational, not required)
- Screen reader-specific optimizations beyond standard ARIA
- Accessibility for native mobile apps (web only)
- High contrast mode / dark mode accessibility (separate feature)
- Internationalization (i18n) - separate concern

## System Architecture Alignment

### Components Referenced
- **Frontend**: `frontend/app/layout.tsx` - Root layout for skip link placement
- **Frontend**: `frontend/components/layout/SkipLink.tsx` - New component
- **Frontend**: All form components - Error message accessibility
- **Frontend**: `frontend/components/ui/*` - shadcn/ui components audit

### Architecture Constraints
- Must work with Next.js App Router and React Server Components
- Skip link must be first focusable element on every page
- Cannot break existing keyboard navigation implemented in P5-5.2
- Must maintain existing shadcn/ui component styling

## Detailed Design

### Services and Modules

| Module | Responsibility | Inputs | Outputs |
|--------|---------------|--------|---------|
| `SkipLink.tsx` | Render skip-to-content link | None | Focusable link element |
| `layout.tsx` | Include SkipLink in root layout | Children | Page with skip link |
| `vitest.setup.ts` | Configure axe-core for testing | Test environment | Accessibility matchers |

### Data Models and Contracts

No database changes required. This epic is frontend-only.

**SkipLink Component Props:**
```typescript
interface SkipLinkProps {
  /** Target element ID to skip to (default: "main-content") */
  targetId?: string;
  /** Custom label text (default: "Skip to main content") */
  label?: string;
}
```

### APIs and Interfaces

No API changes required. This epic is frontend-only.

### Workflows and Sequencing

**Skip Link User Flow:**
```
User lands on page → Presses Tab →
  Skip link becomes visible and focused →
  User presses Enter →
  Focus moves to main content area →
  User continues Tab navigation from main content
```

**Accessibility Audit Flow:**
```
Developer runs npm run test:a11y →
  axe-core scans all pages →
  Reports critical/serious violations →
  Developer fixes each violation →
  Re-runs until zero violations
```

## Non-Functional Requirements

### Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| Skip link render | < 1ms | No perceptible delay |
| axe-core audit | < 5s per page | CI pipeline timing |
| Focus transition | Instant | No animation delay on skip |

### Security

No security implications. This epic adds no new data handling or API endpoints.

### Reliability/Availability

| Scenario | Behavior |
|----------|----------|
| JavaScript disabled | Skip link still renders (SSR) |
| CSS fails to load | Skip link visible by default |
| Main content ID missing | Skip link scrolls to top of page |

### Observability

| Signal | Implementation |
|--------|----------------|
| Accessibility violations | CI job failure with violation details |
| Skip link usage | Optional: track via analytics (not required) |

## Dependencies and Integrations

### Frontend Dependencies (New)
| Package | Version | Purpose | Story |
|---------|---------|---------|-------|
| @axe-core/react | ^4.8.0 | Runtime accessibility testing | P6-2.2 |
| axe-core | ^4.8.0 | Core accessibility engine | P6-2.2 |
| vitest-axe | ^0.1.0 | Vitest matchers for axe | P6-2.2 |

### Frontend Dependencies (Existing)
| Package | Version | Purpose |
|---------|---------|---------|
| react | 19.x | UI framework |
| next | 15.x | App framework |
| tailwindcss | 4.x | Styling (sr-only class) |

### Integration Points
| Integration | Type | Notes |
|-------------|------|-------|
| CI/CD Pipeline | Internal | Add a11y test job to GitHub Actions |
| shadcn/ui | Internal | Audit existing components for ARIA gaps |

## Acceptance Criteria (Authoritative)

### Story P6-2.1: Skip to Content Link
| AC# | Criterion |
|-----|-----------|
| AC1 | Skip link is first focusable element when Tab pressed on any page |
| AC2 | Skip link is visually hidden until focused |
| AC3 | Skip link text is "Skip to main content" |
| AC4 | Pressing Enter on skip link moves focus to element with id="main-content" |
| AC5 | Skip link styled to match design system when visible (bg-primary, text-primary-foreground) |
| AC6 | Skip link works on all pages (dashboard, events, cameras, settings) |

### Story P6-2.2: Accessibility Audit
| AC# | Criterion |
|-----|-----------|
| AC7 | axe-core integrated into test suite |
| AC8 | All critical accessibility violations resolved |
| AC9 | All serious accessibility violations resolved |
| AC10 | Form error messages have aria-describedby linking to inputs |
| AC11 | Dynamic content changes announced via aria-live regions |
| AC12 | Color contrast meets WCAG AA (4.5:1 for normal text, 3:1 for large text) |
| AC13 | CI pipeline includes accessibility check that fails on violations |

## Traceability Mapping

| AC | Spec Section | Component/API | Test Approach |
|----|--------------|---------------|---------------|
| AC1-AC6 | Workflows | `SkipLink.tsx`, `layout.tsx` | Unit test: RTL, verify focus behavior |
| AC7 | Dependencies | `vitest.setup.ts` | Config verification |
| AC8-AC9 | NFR | All pages | axe-core scan in CI |
| AC10 | Detailed Design | Form components | Unit test: verify aria-describedby |
| AC11 | Detailed Design | Toast, notifications | Unit test: verify aria-live |
| AC12 | NFR | All components | axe-core color contrast rule |
| AC13 | Dependencies | `.github/workflows/ci.yml` | CI job verification |

## Risks, Assumptions, Open Questions

### Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| **R1**: axe-core may report false positives | Low | Review each violation manually before fixing |
| **R2**: Fixing violations may break visual design | Medium | QA review after each fix |
| **R3**: Some shadcn/ui components may have upstream a11y issues | Low | File issues with shadcn; use aria overrides |

### Assumptions
| Assumption | Validation |
|------------|------------|
| **A1**: WCAG 2.1 AA is sufficient for target users | Industry standard for web apps |
| **A2**: shadcn/ui components are mostly accessible | Built on Radix primitives which prioritize a11y |
| **A3**: Skip link pattern is familiar to screen reader users | Standard accessibility pattern |

### Open Questions
| Question | Owner | Status |
|----------|-------|--------|
| **Q1**: Should we add a11y testing to PR checks or just main branch? | Dev Team | Recommend: PR checks |
| **Q2**: Should color contrast issues block deployment? | PM | Recommend: Yes, WCAG AA is minimum |

## Test Strategy Summary

### Test Levels

| Level | Framework | Coverage |
|-------|-----------|----------|
| Unit | Vitest + RTL | SkipLink component, focus behavior |
| Integration | vitest-axe | Page-level accessibility scans |
| Manual | Screen reader | VoiceOver/NVDA walkthrough |

### Test Cases by Story

**P6-2.1 (Skip Link)**
- Tab from fresh page load focuses skip link first
- Skip link hidden until focused (check CSS)
- Enter on skip link moves focus to #main-content
- Skip link visible when focused (check computed styles)
- Works on dashboard, events, cameras, settings pages

**P6-2.2 (Accessibility Audit)**
- Zero critical violations on all pages
- Zero serious violations on all pages
- Form errors linked with aria-describedby
- Toast notifications have aria-live="polite"
- All images have alt text or aria-hidden
- All buttons have accessible names

### Coverage Targets
- Skip link: 100% branch coverage
- Page accessibility: Zero axe violations (critical + serious)
- CI: Accessibility job passes on all PRs
