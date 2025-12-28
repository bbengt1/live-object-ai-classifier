# Epic Technical Specification: Platform Polish & Documentation

Date: 2025-12-25
Author: Brent
Epic ID: P11-5
Status: Draft

---

## Overview

Epic P11-5 delivers platform polish and user documentation for ArgusAI. This includes camera list performance optimizations (React.memo, virtual scrolling), a test connection feature before camera save, a GitHub Pages documentation site, and CSV export for motion events. These improvements address user experience issues and documentation gaps identified in previous phases.

## Objectives and Scope

### In Scope

- Camera list performance optimization (React.memo, react-window)
- Test connection endpoint and UI before camera save
- GitHub Pages documentation site with Docusaurus
- CSV export for motion events with streaming

### Out of Scope

- Mobile app UI optimization
- Real-time camera preview improvements
- Video documentation (tutorials)
- Localization/internationalization

## System Architecture Alignment

This epic addresses backlog items for UX and documentation:

- **IMP-005**: Camera list performance
- **FF-011**: Test connection before save
- **FF-017**: GitHub Pages documentation
- **FF-026**: CSV export

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs |
|----------------|----------------|--------|---------|
| `CameraListVirtual.tsx` | Virtual scrolling | Camera list | Virtualized UI |
| `CameraPreview.tsx` | Memoized preview | Camera data | Optimized render |
| `cameras.py` router | Test connection API | Camera config | Test result |
| `events.py` router | CSV export API | Filters | CSV stream |
| `docs-site/` | Docusaurus site | Markdown | Static HTML |

### Story P11-5.1: Camera List Performance

**Problem:** Camera list re-renders all items on any change, causing UI lag with 50+ cameras.

**Solution:** React.memo + react-window virtual scrolling.

**Implementation:**

```typescript
// CameraPreview.tsx - Memoized component
import { memo } from 'react';

interface CameraPreviewProps {
  camera: Camera;
  onSelect: (id: string) => void;
  isSelected: boolean;
}

export const CameraPreview = memo(function CameraPreview({
  camera,
  onSelect,
  isSelected,
}: CameraPreviewProps) {
  return (
    <div
      className={cn("camera-preview", isSelected && "selected")}
      onClick={() => onSelect(camera.id)}
    >
      <img
        src={camera.preview_url}
        alt={camera.name}
        loading="lazy"
      />
      <span>{camera.name}</span>
      <StatusBadge status={camera.status} />
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for optimal memo
  return (
    prevProps.camera.id === nextProps.camera.id &&
    prevProps.camera.status === nextProps.camera.status &&
    prevProps.camera.preview_url === nextProps.camera.preview_url &&
    prevProps.isSelected === nextProps.isSelected
  );
});
```

```typescript
// CameraListVirtual.tsx - Virtual scrolling
import { FixedSizeList as List } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';

interface CameraListProps {
  cameras: Camera[];
  onSelect: (id: string) => void;
  selectedId?: string;
}

export function CameraListVirtual({ cameras, onSelect, selectedId }: CameraListProps) {
  const ITEM_HEIGHT = 120; // px

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const camera = cameras[index];
    return (
      <div style={style}>
        <CameraPreview
          camera={camera}
          onSelect={onSelect}
          isSelected={camera.id === selectedId}
        />
      </div>
    );
  };

  return (
    <AutoSizer>
      {({ height, width }) => (
        <List
          height={height}
          itemCount={cameras.length}
          itemSize={ITEM_HEIGHT}
          width={width}
        >
          {Row}
        </List>
      )}
    </AutoSizer>
  );
}
```

### Story P11-5.2: Test Connection Before Save

**Problem:** Users save camera configs that fail to connect, requiring edit/delete cycle.

**Solution:** Test connection endpoint that validates RTSP before save.

**API:**

```yaml
POST /api/v1/cameras/test:
  Request:
    {
      "rtsp_url": "rtsp://user:pass@192.168.1.100:554/stream",
      "timeout": 10
    }

  Response 200 (success):
    {
      "success": true,
      "message": "Connection successful",
      "resolution": "1920x1080",
      "fps": 30,
      "codec": "H.264"
    }

  Response 200 (failure):
    {
      "success": false,
      "error": "Connection timeout",
      "error_code": "TIMEOUT"
    }

  Error codes:
    - TIMEOUT: Connection timed out
    - AUTH_FAILED: Invalid credentials
    - INVALID_URL: Malformed RTSP URL
    - CONNECTION_REFUSED: Host unreachable
    - STREAM_ERROR: Connected but no stream
```

**Backend Implementation:**

```python
@router.post("/cameras/test", response_model=TestConnectionResponse)
async def test_camera_connection(
    request: TestConnectionRequest,
    timeout: int = Query(default=10, le=30),
):
    """Test RTSP camera connection without saving."""
    try:
        result = await camera_service.test_connection(
            rtsp_url=request.rtsp_url,
            timeout=timeout,
        )
        return TestConnectionResponse(
            success=True,
            message="Connection successful",
            resolution=result.resolution,
            fps=result.fps,
            codec=result.codec,
        )
    except ConnectionTimeoutError:
        return TestConnectionResponse(
            success=False,
            error="Connection timed out",
            error_code="TIMEOUT",
        )
    except AuthenticationError:
        return TestConnectionResponse(
            success=False,
            error="Invalid credentials",
            error_code="AUTH_FAILED",
        )
    # ... other error handling
```

**Frontend UI:**

```typescript
function CameraForm() {
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const handleTestConnection = async () => {
    setIsTesting(true);
    try {
      const result = await api.cameras.testConnection({
        rtsp_url: formValues.rtsp_url,
      });
      setTestResult(result);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <form>
      {/* RTSP URL input */}
      <Input name="rtsp_url" ... />

      {/* Test Connection button */}
      <Button
        type="button"
        variant="outline"
        onClick={handleTestConnection}
        disabled={isTesting || !formValues.rtsp_url}
      >
        {isTesting ? <Loader2 className="animate-spin" /> : "Test Connection"}
      </Button>

      {/* Test result display */}
      {testResult && (
        <Alert variant={testResult.success ? "default" : "destructive"}>
          {testResult.success ? (
            <>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                Connected! {testResult.resolution} @ {testResult.fps}fps
              </AlertDescription>
            </>
          ) : (
            <>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{testResult.error}</AlertDescription>
            </>
          )}
        </Alert>
      )}

      {/* Save button - enabled only after successful test */}
      <Button
        type="submit"
        disabled={!testResult?.success}
      >
        Save Camera
      </Button>
    </form>
  );
}
```

### Story P11-5.3: GitHub Pages Documentation Site

**Structure:**

```
docs-site/
├── docusaurus.config.js
├── package.json
├── sidebars.js
├── docs/
│   ├── intro.md
│   ├── installation/
│   │   ├── quick-start.md
│   │   ├── docker.md
│   │   ├── kubernetes.md
│   │   └── requirements.md
│   ├── configuration/
│   │   ├── cameras.md
│   │   ├── ai-providers.md
│   │   ├── notifications.md
│   │   └── integrations.md
│   ├── api-reference/
│   │   └── index.md  (generated from OpenAPI)
│   └── troubleshooting/
│       ├── common-issues.md
│       └── faq.md
├── src/
│   ├── pages/
│   │   └── index.tsx  (landing page)
│   └── css/
│       └── custom.css
└── static/
    ├── img/
    │   └── logo.svg
    └── CNAME  (for custom domain)
```

**docusaurus.config.js:**

```javascript
module.exports = {
  title: 'ArgusAI',
  tagline: 'AI-Powered Security Camera Analysis',
  url: 'https://project-argusai.github.io',
  baseUrl: '/ArgusAI/',
  organizationName: 'project-argusai',
  projectName: 'ArgusAI',
  deploymentBranch: 'gh-pages',

  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/project-argusai/ArgusAI/edit/main/docs-site/',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'ArgusAI',
      logo: { alt: 'ArgusAI Logo', src: 'img/logo.svg' },
      items: [
        { type: 'doc', docId: 'intro', label: 'Docs' },
        { href: 'https://github.com/project-argusai/ArgusAI', label: 'GitHub' },
      ],
    },
    footer: {
      style: 'dark',
      copyright: `Copyright © ${new Date().getFullYear()} ArgusAI`,
    },
  },
};
```

**GitHub Actions Workflow:**

```yaml
# .github/workflows/docs.yml
name: Deploy Documentation

on:
  push:
    branches: [main]
    paths:
      - 'docs-site/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: docs-site/package-lock.json

      - name: Install dependencies
        working-directory: docs-site
        run: npm ci

      - name: Build
        working-directory: docs-site
        run: npm run build

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs-site/build
```

### Story P11-5.4: CSV Export

**API:**

```yaml
GET /api/v1/events/export:
  Query Parameters:
    format: csv (required)
    start_date: ISO datetime (optional)
    end_date: ISO datetime (optional)
    camera_id: string (optional)

  Response 200:
    Content-Type: text/csv
    Content-Disposition: attachment; filename="events-2025-12-25.csv"

    timestamp,camera_name,event_type,description,confidence,objects,duration_seconds
    2025-12-25T10:30:00Z,Front Door,motion,"Person approaching...",0.92,"person,package",15.2
    ...
```

**Backend Implementation:**

```python
from fastapi.responses import StreamingResponse
import csv
import io

@router.get("/events/export")
async def export_events(
    format: str = Query(..., regex="^csv$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    camera_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Export events to CSV with streaming."""

    async def generate_csv():
        # Write header
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "timestamp", "camera_name", "event_type", "description",
            "confidence", "objects", "duration_seconds"
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Stream events in batches
        offset = 0
        batch_size = 100

        while True:
            query = select(Event).join(Camera)
            if start_date:
                query = query.where(Event.created_at >= start_date)
            if end_date:
                query = query.where(Event.created_at <= end_date)
            if camera_id:
                query = query.where(Event.camera_id == camera_id)

            query = query.order_by(Event.created_at.desc())
            query = query.offset(offset).limit(batch_size)

            result = await db.execute(query)
            events = result.scalars().all()

            if not events:
                break

            for event in events:
                writer.writerow([
                    event.created_at.isoformat(),
                    event.camera.name,
                    event.event_type,
                    event.description,
                    event.confidence,
                    ",".join(event.detected_objects or []),
                    event.duration,
                ])

            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

            offset += batch_size

    filename = f"events-{datetime.now().strftime('%Y-%m-%d')}.csv"
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

## Non-Functional Requirements

### Performance

| Metric | Target | Source |
|--------|--------|--------|
| Camera list render (100 items) | <100ms | NFR4 |
| Test connection timeout | 10s default | Goal |
| CSV export streaming | No memory limit | Goal |
| Docs site build | <60s | Goal |

### Security

- Test connection endpoint validates URL format
- CSV export requires authentication
- No sensitive data in exported CSV

### Reliability/Availability

- Virtual scrolling handles 1000+ cameras
- Streaming export prevents memory issues
- Docs site deployed to GitHub CDN

### Observability

- Console logging for render performance (dev mode)
- API logging for export requests
- GitHub Actions logs for docs deployment

## Dependencies and Integrations

| Dependency | Version | Purpose |
|------------|---------|---------|
| react-window | 1.8+ | Virtual scrolling |
| react-virtualized-auto-sizer | 1.0+ | Container sizing |
| @docusaurus/preset-classic | 3.x | Documentation site |

## Acceptance Criteria (Authoritative)

1. **AC-5.1.1**: CameraPreview uses React.memo to prevent re-renders
2. **AC-5.1.2**: Virtual scrolling enabled for lists > 20 cameras
3. **AC-5.1.3**: React Query provides caching and deduplication
4. **AC-5.1.4**: 100 cameras render without UI lag
5. **AC-5.1.5**: Preview images lazy-loaded on scroll
6. **AC-5.2.1**: POST `/api/v1/cameras/test` accepts camera config
7. **AC-5.2.2**: Returns specific error messages for connection issues
8. **AC-5.2.3**: UI shows "Test Connection" button
9. **AC-5.2.4**: Test results displayed before save enabled
10. **AC-5.2.5**: Timeout after 10 seconds with appropriate message
11. **AC-5.3.1**: GitHub Pages site live at project URL
12. **AC-5.3.2**: Landing page with project overview
13. **AC-5.3.3**: Installation guide with copy-paste commands
14. **AC-5.3.4**: Configuration reference
15. **AC-5.3.5**: API documentation
16. **AC-5.3.6**: Auto-deploys on push to main
17. **AC-5.4.1**: GET `/api/v1/events/export?format=csv` returns CSV
18. **AC-5.4.2**: Export includes timestamp, camera, description, confidence, objects
19. **AC-5.4.3**: Date range filtering supported
20. **AC-5.4.4**: UI button triggers download
21. **AC-5.4.5**: Large exports streamed to prevent memory issues

## Traceability Mapping

| AC | Spec Section | Component | Test Idea |
|----|--------------|-----------|-----------|
| AC-5.1.1-5 | Story P11-5.1 | CameraListVirtual.tsx | Component: render count, scroll perf |
| AC-5.2.1-5 | Story P11-5.2 | cameras.py, CameraForm | API: error codes, UI states |
| AC-5.3.1-6 | Story P11-5.3 | docs-site/ | Manual: site loads, links work |
| AC-5.4.1-5 | Story P11-5.4 | events.py | API: streaming, filters, format |

## Risks, Assumptions, Open Questions

### Risks

- **R1**: react-window compatibility with existing styling
  - *Mitigation*: Test early, fallback to windowed scrolling
- **R2**: Docusaurus version conflicts
  - *Mitigation*: Use LTS version, separate package.json
- **R3**: Large CSV exports timeout
  - *Mitigation*: Streaming response, client-side progress

### Assumptions

- **A1**: 100 cameras is sufficient for most users
- **A2**: GitHub Pages sufficient for documentation needs
- **A3**: CSV format acceptable for export

### Open Questions

- **Q1**: Custom domain for docs site?
  - *Decision*: Use GitHub-provided URL initially
- **Q2**: Include thumbnails in CSV export?
  - *Decision*: No, text only for simplicity

## Test Strategy Summary

### Unit Tests

- CameraPreview: Memo behavior, render count
- CSV streaming: Generator function, formatting

### Integration Tests

- Camera list: Virtual scrolling with mock data
- Test connection: Various error scenarios
- Export: Date filtering, streaming

### Manual Testing

- Scroll camera list with 100+ items
- Test connection with valid/invalid URLs
- Download CSV, open in Excel
- Browse documentation site

### Test Coverage Target

- Frontend components: 70%+ coverage
- Backend endpoints: 100% coverage
