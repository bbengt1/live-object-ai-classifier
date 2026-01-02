/**
 * EntityAssignConfirmDialog component - confirmation dialog for entity assignment (Story P16-4.1)
 * AC-4.1.1: Confirmation dialog appears before assignment
 * AC-4.1.2: Shows entity name in message
 * AC-4.1.3: Shows re-classification info
 * AC-4.1.4: Shows estimated API cost
 * AC-4.1.5: Confirm triggers assignment
 * AC-4.1.6: Cancel returns to entity selection
 */

'use client';

import { AlertTriangle } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface EntityAssignConfirmDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Entity name to display in the confirmation message */
  entityName: string;
  /** Callback when user confirms the assignment */
  onConfirm: () => void;
  /** Callback when user cancels the assignment */
  onCancel: () => void;
  /** Whether the confirmation action is in progress */
  isLoading?: boolean;
  /** Estimated cost for re-analysis (default: ~$0.002) */
  estimatedCost?: string;
}

/**
 * EntityAssignConfirmDialog - warns user about AI re-classification before entity assignment
 */
export function EntityAssignConfirmDialog({
  open,
  onOpenChange,
  entityName,
  onConfirm,
  onCancel,
  isLoading = false,
  estimatedCost = '~$0.002',
}: EntityAssignConfirmDialogProps) {
  const handleCancel = () => {
    onCancel();
    onOpenChange(false);
  };

  const handleConfirm = () => {
    onConfirm();
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            <AlertDialogTitle>Confirm Entity Assignment</AlertDialogTitle>
          </div>
          <AlertDialogDescription asChild>
            <div className="space-y-3 pt-2">
              <p>
                Assigning this event to <strong>{entityName}</strong> will trigger AI re-classification.
              </p>
              <p>
                This will update the event description based on the entity context.
              </p>
              <p className="text-xs text-muted-foreground">
                Estimated API cost: {estimatedCost} for re-analysis
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel} disabled={isLoading}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={isLoading}>
            {isLoading ? 'Assigning...' : 'Confirm'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
