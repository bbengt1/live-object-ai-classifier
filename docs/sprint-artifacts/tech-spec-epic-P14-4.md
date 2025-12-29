# Epic Technical Specification: P14-4 Frontend Code Quality

Date: 2025-12-29
Author: Claude (AI-Generated)
Epic ID: P14-4
Status: Draft
Priority: P2-P3

---

## Overview

Epic P14-4 addresses frontend code quality issues including debug console.log statements, test type mismatches, failing tests, test fixture consolidation, unused imports, and React anti-patterns. The frontend has a good test foundation with 39+ test files but needs cleanup for maintainability.

## Current State Analysis

### Debug Console.log Statements

**Found in production code:**

| File | Line | Context |
|------|------|---------|
| `NotificationContext.tsx` | 164 | `console.log('Alert triggered:', data)` |
| `status/page.tsx` | 101 | `console.log('Log download not yet implemented')` |
| `settings/page.tsx` | 242 | `console.log('Export format requested:', format)` |
| `cameras/[id]/page.tsx` | 42, 48, 50 | Multiple form submit logs |
| `CameraForm.tsx` | 266 | `console.log('Form state:', {...})` |

### Test File Count

| Category | Files |
|----------|-------|
| Component tests | 31 |
| Hook tests | 5 |
| Accessibility tests | 2 |
| Utility tests | 1 |
| **Total** | **39** |

### Known Test Issues

1. **TunnelSettings.test.tsx** - API contract mismatch after P13-2.4 changes
2. Type mismatches between test mocks and actual types
3. Duplicate test utilities across files

## Objectives and Scope

### In Scope

- Remove all debug console.log/console.debug statements
- Fix test type mismatches with actual API types
- Fix failing TunnelSettings test
- Create shared test fixtures factory
- Clean up unused test imports
- Clean up unused component imports
- Fix setState in useEffect anti-patterns
- Extract reusable SortIcon component

### Out of Scope

- Adding new test coverage (covered in separate testing epic)
- Performance optimization
- UI/UX changes
- Accessibility improvements

## Detailed Design

### Story P14-4.1: Remove Debug Console.log Statements

**Files to Update:**

```typescript
// NotificationContext.tsx:164
// REMOVE:
console.log('Alert triggered:', data);

// status/page.tsx:101
// REPLACE:
console.log('Log download not yet implemented');
// WITH:
// TODO: Implement log download (tracked in backlog)

// settings/page.tsx:242
// REMOVE:
console.log('Export format requested:', format);

// cameras/[id]/page.tsx:42,48,50
// REMOVE all console.log statements in handleSubmit

// CameraForm.tsx:266
// REMOVE:
console.log('Form state:', {...});
```

**ESLint Rule (add to `.eslintrc.json`):**
```json
{
  "rules": {
    "no-console": ["error", { "allow": ["warn", "error"] }]
  }
}
```

### Story P14-4.2: Fix Test Type Mismatches

**Problem:** Test mocks don't match actual TypeScript types, causing runtime issues and maintenance burden.

**Example Issue:**
```typescript
// Test creates mock event
const mockEvent = {
  id: '1',
  description: 'Test event',
  // Missing required fields: timestamp, camera_id, etc.
};

// Actual type requires all fields
interface IEvent {
  id: string;
  camera_id: string;
  timestamp: string;
  description: string;
  thumbnail?: string;
  // ... many more fields
}
```

**Solution: Create type-safe factory functions:**

```typescript
// __tests__/factories/event.factory.ts

import type { IEvent } from '@/types/event';

export function createMockEvent(overrides: Partial<IEvent> = {}): IEvent {
  return {
    id: crypto.randomUUID(),
    camera_id: 'camera-1',
    camera_name: 'Test Camera',
    timestamp: new Date().toISOString(),
    description: 'A person was detected',
    thumbnail: '/api/thumbnails/test.jpg',
    source_type: 'protect',
    ai_provider: 'openai',
    analysis_mode: 'single_frame',
    is_starred: false,
    smart_detection_type: null,
    correlation_group_id: null,
    ...overrides,
  };
}

export function createMockEventList(
  count: number,
  overrides: Partial<IEvent> = {}
): IEvent[] {
  return Array.from({ length: count }, (_, i) =>
    createMockEvent({ ...overrides, id: `event-${i}` })
  );
}
```

### Story P14-4.3: Fix Failing TunnelSettings Test

**Root Cause:** P13-2.4 added a new `test()` method to tunnel API, but tests weren't updated.

**Current Test Mock:**
```typescript
vi.mock('@/lib/api-client', () => ({
  apiClient: {
    tunnel: {
      getStatus: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
      test: vi.fn(),  // Added but not properly mocked for new behavior
    },
  },
}));
```

**Fix:** Update test to handle new test endpoint response:

```typescript
// TunnelSettings.test.tsx

const mockTestSuccess = {
  success: true,
  error: null,
  latency_ms: 2500,
  hostname: 'my-tunnel.trycloudflare.com',
};

const mockTestFailure = {
  success: false,
  error: 'Invalid token',
  latency_ms: null,
  hostname: null,
};

describe('Test Connection', () => {
  it('should use test endpoint when token is provided', async () => {
    vi.mocked(apiClient.tunnel.getStatus).mockResolvedValue(mockStatusDisconnected);
    vi.mocked(apiClient.tunnel.test).mockResolvedValue(mockTestSuccess);

    renderWithProviders(<TunnelSettings />);

    // Enter a token
    const tokenInput = screen.getByLabelText(/tunnel token/i);
    await userEvent.type(tokenInput, 'my-test-token');

    // Click test button
    const testButton = screen.getByRole('button', { name: /test connection/i });
    await userEvent.click(testButton);

    await waitFor(() => {
      expect(apiClient.tunnel.test).toHaveBeenCalledWith({ token: 'my-test-token' });
    });
  });
});
```

### Story P14-4.4: Create Shared Test Fixtures Factory

**Problem:** Each test file creates its own mock data, leading to:
- Inconsistent test data
- Type mismatches
- Duplicate code
- Maintenance burden

**Solution:** Create centralized factory pattern:

```typescript
// __tests__/factories/index.ts

export * from './event.factory';
export * from './camera.factory';
export * from './entity.factory';
export * from './user.factory';
export * from './alert-rule.factory';
export * from './notification.factory';

// __tests__/factories/camera.factory.ts

import type { ICamera, CameraSourceType, AnalysisMode } from '@/types/camera';

export function createMockCamera(overrides: Partial<ICamera> = {}): ICamera {
  return {
    id: crypto.randomUUID(),
    name: 'Test Camera',
    rtsp_url: 'rtsp://192.168.1.100:554/stream',
    username: 'admin',
    source_type: 'rtsp' as CameraSourceType,
    analysis_mode: 'single_frame' as AnalysisMode,
    is_enabled: true,
    motion_detection_enabled: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

// __tests__/factories/entity.factory.ts

import type { IEntity, EntityType } from '@/types/entity';

export function createMockEntity(overrides: Partial<IEntity> = {}): IEntity {
  return {
    id: crypto.randomUUID(),
    name: 'Test Person',
    entity_type: 'person' as EntityType,
    description: null,
    thumbnail: '/api/thumbnails/entity-test.jpg',
    appearance_count: 5,
    first_seen_at: new Date().toISOString(),
    last_seen_at: new Date().toISOString(),
    is_favorite: false,
    ...overrides,
  };
}
```

**Usage in Tests:**
```typescript
// Before:
const mockEvent = {
  id: '1',
  description: 'Test',
  // Missing many fields...
};

// After:
import { createMockEvent } from '../factories';

const mockEvent = createMockEvent({
  description: 'Person walking to door',
});
```

### Story P14-4.5: Clean Up Unused Test Imports

**Problem:** Many test files import utilities that aren't used.

**Common Issues Found:**
```typescript
// Unused waitFor
import { render, screen, waitFor } from '@testing-library/react';

// Unused act
import { renderHook, waitFor, act } from '@testing-library/react';

// Unused React import (not needed in modern React)
import React from 'react';
```

**Solution:** Run ESLint with unused imports rule:

```json
// .eslintrc.json
{
  "rules": {
    "@typescript-eslint/no-unused-vars": ["error", {
      "argsIgnorePattern": "^_",
      "varsIgnorePattern": "^_"
    }]
  }
}
```

**Files to Clean:**
- `__tests__/hooks/useEvents.test.tsx` - Remove unused `act`
- `__tests__/hooks/useCamerasQuery.test.ts` - Remove unused imports
- `__tests__/components/entities/*.test.tsx` - Remove unused React import
- Most test files - Remove explicit React import

### Story P14-4.6: Clean Up Unused Component Imports

**Problem:** Some components import utilities/types that are no longer used.

**Detection:** Run `npm run lint` with enhanced rules, or use `npx knip`:

```bash
cd frontend
npx knip --no-gitignore
```

**Common Patterns to Fix:**
- Unused type imports from `@/types/*`
- Unused utility functions from `@/lib/*`
- Unused icon imports from `lucide-react`

### Story P14-4.7: Fix setState in useEffect Anti-patterns

**Problem Pattern:**
```typescript
// Anti-pattern: Setting state immediately in useEffect
useEffect(() => {
  setIsLoading(true);
  fetchData().then(data => {
    setData(data);
    setIsLoading(false);
  });
}, []);
```

**Correct Pattern:**
```typescript
// Better: Use query state or derive from existing state
const { data, isLoading } = useQuery({
  queryKey: ['data'],
  queryFn: fetchData,
});

// Or if custom hook is needed:
function useDataFetch() {
  const [state, setState] = useState<{
    data: Data | null;
    isLoading: boolean;
    error: Error | null;
  }>({
    data: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    fetchData()
      .then(data => {
        if (!cancelled) {
          setState({ data, isLoading: false, error: null });
        }
      })
      .catch(error => {
        if (!cancelled) {
          setState({ data: null, isLoading: false, error });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
```

**Files to Review:**
- Components using local state for loading/error when React Query is available
- Custom hooks that set state in useEffect without cleanup

### Story P14-4.8: Extract SortIcon Component

**Problem:** Sort icon logic is duplicated across table components.

**Current Pattern (duplicated):**
```typescript
// In EventsTable.tsx
{sortConfig.key === 'timestamp' && (
  sortConfig.direction === 'asc' ? <ChevronUp /> : <ChevronDown />
)}

// In CameraList.tsx
{sortConfig.key === 'name' && (
  sortConfig.direction === 'asc' ? <ChevronUp /> : <ChevronDown />
)}

// In EntitiesTable.tsx
// ... same pattern again
```

**Solution: Extract to reusable component:**

```typescript
// components/ui/sort-icon.tsx

import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SortIconProps {
  columnKey: string;
  currentSortKey: string | null;
  direction: 'asc' | 'desc';
  className?: string;
}

export function SortIcon({
  columnKey,
  currentSortKey,
  direction,
  className,
}: SortIconProps) {
  if (columnKey !== currentSortKey) {
    return <ChevronsUpDown className={cn('h-4 w-4 text-muted-foreground', className)} />;
  }

  return direction === 'asc' ? (
    <ChevronUp className={cn('h-4 w-4', className)} />
  ) : (
    <ChevronDown className={cn('h-4 w-4', className)} />
  );
}
```

**Usage:**
```typescript
import { SortIcon } from '@/components/ui/sort-icon';

<th onClick={() => handleSort('timestamp')}>
  Timestamp
  <SortIcon
    columnKey="timestamp"
    currentSortKey={sortConfig.key}
    direction={sortConfig.direction}
  />
</th>
```

## Acceptance Criteria

### AC-1: Debug Statements
- [ ] No console.log statements in production code
- [ ] No console.debug statements in production code
- [ ] ESLint rule configured to prevent future additions
- [ ] console.warn and console.error allowed for legitimate use

### AC-2: Test Types
- [ ] All test mocks use factory functions
- [ ] Factory functions return types matching actual interfaces
- [ ] TypeScript compilation passes with `strict: true`

### AC-3: TunnelSettings Test
- [ ] TunnelSettings test passes
- [ ] Test covers new test endpoint behavior
- [ ] No type errors in test file

### AC-4: Test Fixtures
- [ ] Factory files created for Event, Camera, Entity, User, AlertRule
- [ ] Each factory returns complete, type-safe objects
- [ ] Existing tests updated to use factories

### AC-5: Unused Imports (Tests)
- [ ] No unused imports in test files
- [ ] ESLint reports 0 unused variable warnings

### AC-6: Unused Imports (Components)
- [ ] No unused imports in component files
- [ ] knip reports 0 unused exports

### AC-7: React Patterns
- [ ] No setState immediately in useEffect without proper handling
- [ ] All data fetching uses React Query where appropriate

### AC-8: SortIcon Component
- [ ] SortIcon component created in `components/ui/`
- [ ] At least 3 table components updated to use SortIcon
- [ ] Unit tests for SortIcon component

## Test Strategy

### Running Frontend Tests

```bash
cd frontend

# All tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage

# Specific file
npm test -- TunnelSettings
```

### Linting

```bash
# Run ESLint
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix

# Check unused exports
npx knip
```

## Non-Functional Requirements

| Metric | Requirement |
|--------|-------------|
| Build time | No regression from changes |
| Bundle size | No increase from changes |
| Test runtime | No significant increase |
| Type coverage | Maintain or improve |

---

_Tech spec generated for Phase 14 Epic P14-4: Frontend Code Quality_
