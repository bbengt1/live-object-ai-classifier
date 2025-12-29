# Epic Technical Specification: P14-7 Frontend Enhancements

Date: 2025-12-29
Author: Claude (AI-Generated)
Epic ID: P14-7
Status: Draft
Priority: P3-P4

---

## Overview

Epic P14-7 addresses frontend improvements including accessibility fixes, image optimization, TypeScript strictness, hook test coverage, and developer tooling. These are lower-priority improvements that enhance maintainability and developer experience.

## Objectives and Scope

### In Scope

1. Add alt text to backup/restore images (accessibility)
2. Replace `<img>` with `next/image` for optimization
3. Enable stricter TypeScript checks
4. Increase hook test coverage
5. Add React Query devtools
6. Add OpenAPI summaries and tags

### Out of Scope

- New UI features
- Major architectural changes
- Performance optimization beyond images

## Detailed Design

### Story P14-7.1: Add Alt Text to Backup/Restore Images

**Problem:** Images in backup/restore UI lack alt text for screen readers.

**Files to Update:**
- `components/settings/BackupRestore.tsx`
- Any other components with `<img>` tags missing alt

**Solution:**
```tsx
// Before:
<img src={backupIcon} className="..." />

// After:
<img
  src={backupIcon}
  alt="Database backup icon"
  className="..."
/>
```

**Acceptance Criteria:**
- [ ] All `<img>` tags have descriptive alt text
- [ ] Alt text describes image content, not function
- [ ] Decorative images use `alt=""`

### Story P14-7.2: Replace img with next/image

**Problem:** Standard `<img>` tags don't benefit from Next.js image optimization.

**Files to Update:**
```
components/events/EventCard.tsx
components/entities/EntityCard.tsx
components/cameras/CameraPreview.tsx
app/cameras/[id]/page.tsx
```

**Solution:**
```tsx
// Before:
<img
  src={thumbnail}
  alt="Event thumbnail"
  className="w-full h-48 object-cover"
/>

// After:
import Image from 'next/image';

<Image
  src={thumbnail}
  alt="Event thumbnail"
  width={400}
  height={192}
  className="w-full h-48 object-cover"
  unoptimized={thumbnail.startsWith('data:')}  // Skip optimization for data URIs
/>
```

**Configuration:**
```js
// next.config.js
module.exports = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/api/**',
      },
    ],
  },
};
```

**Acceptance Criteria:**
- [ ] All thumbnail images use `next/image`
- [ ] next.config.js configured for API images
- [ ] Data URI thumbnails handled correctly
- [ ] No layout shift from image loading

### Story P14-7.3: Enable Stricter TypeScript Checks

**Problem:** TypeScript could catch more bugs with stricter settings.

**Changes to `tsconfig.json`:**
```json
{
  "compilerOptions": {
    // Enable stricter checks
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "exactOptionalPropertyTypes": true
  }
}
```

**Expected Issues to Fix:**
- Array access without undefined checks
- Switch statements without default cases
- Functions with implicit undefined returns
- Optional properties with undefined values

**Acceptance Criteria:**
- [ ] New TypeScript settings enabled
- [ ] All resulting errors fixed
- [ ] Build passes with strict settings
- [ ] No runtime regressions

### Story P14-7.4: Increase Hook Test Coverage

**Current Hook Test Files:**
- `useEvents.test.tsx`
- `useCamerasQuery.test.ts`
- `useDebounce.test.ts`
- `useEntities.test.ts`
- `useWebSocket.test.ts`

**Hooks Missing Tests:**
| Hook | File | Priority |
|------|------|----------|
| `useSettings` | `lib/hooks/useSettings.ts` | P2 |
| `useAlertRules` | `lib/hooks/useAlertRules.ts` | P2 |
| `usePush` | `lib/hooks/usePush.ts` | P3 |
| `useAuth` | `lib/hooks/useAuth.ts` | P3 |

**Test Template:**
```tsx
// __tests__/hooks/useSettings.test.ts

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { useSettings, useUpdateSettings } from '@/lib/hooks/useSettings';
import { apiClient } from '@/lib/api-client';

vi.mock('@/lib/api-client');

describe('useSettings', () => {
  it('fetches settings on mount', async () => {
    vi.mocked(apiClient.settings.get).mockResolvedValue({
      ai_provider: 'openai',
      analysis_mode: 'single_frame',
    });

    const { result } = renderHook(() => useSettings(), { wrapper });

    await waitFor(() => {
      expect(result.current.data).toBeDefined();
    });

    expect(result.current.data?.ai_provider).toBe('openai');
  });

  it('handles error gracefully', async () => {
    vi.mocked(apiClient.settings.get).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useSettings(), { wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe('useUpdateSettings', () => {
  it('updates settings and invalidates cache', async () => {
    // ...
  });
});
```

**Acceptance Criteria:**
- [ ] useSettings tests created
- [ ] useAlertRules tests created
- [ ] usePush tests created (if time permits)
- [ ] Each hook has 5+ test cases

### Story P14-7.5: Add React Query Devtools

**Problem:** Debugging React Query cache is difficult without devtools.

**Installation:**
```bash
npm install @tanstack/react-query-devtools
```

**Integration:**
```tsx
// app/providers.tsx

import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
```

**Acceptance Criteria:**
- [ ] Devtools installed and configured
- [ ] Only visible in development
- [ ] Opens with keyboard shortcut
- [ ] Shows cache state and queries

### Story P14-7.6: Add OpenAPI Summaries and Tags

**Problem:** OpenAPI documentation could be more descriptive.

**Current:**
```python
@router.get("/events")
async def get_events(...):
    """Get paginated list of events."""
```

**Improved:**
```python
@router.get(
    "/events",
    summary="List Events",
    description="Get a paginated list of events with optional filtering by camera, date range, and detection type.",
    tags=["Events"],
    response_description="Paginated list of events with total count",
)
async def get_events(...):
    """..."""
```

**Tag Organization:**
| Tag | Endpoints |
|-----|-----------|
| Events | `/events/*` |
| Cameras | `/cameras/*` |
| Entities | `/context/entities/*` |
| Alert Rules | `/alert-rules/*` |
| System | `/system/*` |
| AI | `/ai/*` |
| Push | `/push/*` |
| Tunnel | `/system/tunnel/*` |

**Acceptance Criteria:**
- [ ] All endpoints have summary and description
- [ ] Endpoints grouped by logical tags
- [ ] Response descriptions included
- [ ] OpenAPI spec validates

## Non-Functional Requirements

| Metric | Requirement |
|--------|-------------|
| Build time | No regression |
| Bundle size | <5% increase from devtools |
| Lighthouse accessibility | 95+ score |

---

_Tech spec generated for Phase 14 Epic P14-7: Frontend Enhancements_
