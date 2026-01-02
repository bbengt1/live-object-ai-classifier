# Story P16-4.1: Create Entity Assignment Confirmation Dialog

Status: done

## Story

As a **user**,
I want **a confirmation dialog when assigning events to entities**,
So that **I understand the re-classification will occur**.

## Acceptance Criteria

1. **AC1**: Given I select an entity to assign an event to, when I confirm the selection, then a confirmation dialog appears before the assignment
2. **AC2**: Given the confirmation dialog is shown, when I read the content, then I see: "Assigning this event to [Entity Name] will trigger AI re-classification"
3. **AC3**: Given the confirmation dialog is shown, when I read the content, then I see: "This will update the event description based on the entity context"
4. **AC4**: Given the confirmation dialog is shown, when I read the content, then I see estimated API cost (e.g., "~$0.002 for re-analysis")
5. **AC5**: Given I click "Confirm" in the dialog, when the action completes, then the event is assigned to the entity and re-classification is triggered
6. **AC6**: Given I click "Cancel" in the dialog, when the dialog closes, then no assignment occurs and I return to entity selection

## Tasks / Subtasks

- [x] Task 1: Create EntityAssignConfirmDialog component (AC: 1, 2, 3, 4)
  - [x] Create component file at frontend/components/entities/EntityAssignConfirmDialog.tsx
  - [x] Use shadcn/ui AlertDialog component
  - [x] Display entity name in dialog message
  - [x] Display re-classification info message
  - [x] Display estimated API cost from settings
- [x] Task 2: Integrate dialog into EntitySelectModal flow (AC: 5, 6)
  - [x] Add state for showing confirmation dialog
  - [x] Intercept Confirm click to show dialog first
  - [x] Pass through to original onSelect when confirmed
  - [x] Close dialog and return to selection on cancel
- [x] Task 3: Write tests for confirmation dialog (AC: all)
  - [x] Test dialog renders with entity name
  - [x] Test confirm button triggers assignment
  - [x] Test cancel button closes without assignment

## Dev Notes

- **Component to create**: `frontend/components/entities/EntityAssignConfirmDialog.tsx`
- **Component to modify**: `frontend/components/entities/EntitySelectModal.tsx`
- **UI Component**: Use AlertDialog from shadcn/ui
- **Cost estimate**: Read from AI provider settings or use default estimate

### Project Structure Notes

- EntitySelectModal already handles entity selection
- Need to intercept the confirm action to show warning first
- AlertDialog provides proper modal semantics for confirmation

### References

- [Source: docs/epics-phase16.md#Story-P16-4.1]
- [Source: frontend/components/entities/EntitySelectModal.tsx] - Integration point
- [GitHub Issue: #337]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### File List

- frontend/components/entities/EntityAssignConfirmDialog.tsx (new)
- frontend/components/entities/EntitySelectModal.tsx (modified)
- frontend/__tests__/components/entities/EntityAssignConfirmDialog.test.tsx (new)
