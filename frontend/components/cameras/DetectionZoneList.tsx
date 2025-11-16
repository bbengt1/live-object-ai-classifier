'use client';

import React, { useState } from 'react';
import { IDetectionZone } from '@/types/camera';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Trash2, Check, X, Edit2 } from 'lucide-react';

interface DetectionZoneListProps {
  /**
   * Array of detection zones to display
   */
  zones: IDetectionZone[];
  /**
   * Callback when zone is updated (name, enabled status)
   */
  onZoneUpdate: (zoneId: string, updates: Partial<IDetectionZone>) => void;
  /**
   * Callback when zone is deleted
   */
  onZoneDelete: (zoneId: string) => void;
}

/**
 * Color palette for zone badges (matches DetectionZoneDrawer)
 */
const ZONE_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#14b8a6', // teal-500
  '#f97316', // orange-500
];

/**
 * DetectionZoneList - Zone management UI component
 *
 * Features:
 * - Display all zones in a list with name, enabled toggle, and delete button
 * - Inline zone name editing (click to edit text)
 * - Enable/disable toggle switch per zone
 * - Delete confirmation dialog using shadcn/ui Dialog component
 * - Visual color badges matching canvas overlay colors
 */
export function DetectionZoneList({
  zones,
  onZoneUpdate,
  onZoneDelete,
}: DetectionZoneListProps) {
  const [editingZoneId, setEditingZoneId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [deleteConfirmZoneId, setDeleteConfirmZoneId] = useState<string | null>(null);

  /**
   * Start editing zone name
   */
  const handleStartEdit = (zone: IDetectionZone) => {
    setEditingZoneId(zone.id);
    setEditingName(zone.name);
  };

  /**
   * Save edited zone name
   */
  const handleSaveEdit = (zoneId: string) => {
    if (editingName.trim()) {
      onZoneUpdate(zoneId, { name: editingName.trim() });
    }
    setEditingZoneId(null);
    setEditingName('');
  };

  /**
   * Cancel editing zone name
   */
  const handleCancelEdit = () => {
    setEditingZoneId(null);
    setEditingName('');
  };

  /**
   * Toggle zone enabled status
   */
  const handleToggleEnabled = (zone: IDetectionZone) => {
    onZoneUpdate(zone.id, { enabled: !zone.enabled });
  };

  /**
   * Open delete confirmation dialog
   */
  const handleDeleteClick = (zoneId: string) => {
    setDeleteConfirmZoneId(zoneId);
  };

  /**
   * Confirm zone deletion
   */
  const handleConfirmDelete = () => {
    if (deleteConfirmZoneId) {
      onZoneDelete(deleteConfirmZoneId);
      setDeleteConfirmZoneId(null);
    }
  };

  /**
   * Cancel zone deletion
   */
  const handleCancelDelete = () => {
    setDeleteConfirmZoneId(null);
  };

  if (zones.length === 0) {
    return (
      <div className="text-center p-6 bg-muted/20 rounded-md border border-dashed">
        <p className="text-sm text-muted-foreground">
          No detection zones configured. Click &quot;Draw New Zone&quot; to add one.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-2">
        {zones.map((zone, index) => {
          const color = ZONE_COLORS[index % ZONE_COLORS.length];
          const isEditing = editingZoneId === zone.id;

          return (
            <Card key={zone.id} className="overflow-hidden">
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-4">
                  {/* Color badge */}
                  <div
                    className="w-4 h-4 rounded-full border-2 border-white shadow-sm flex-shrink-0"
                    style={{ backgroundColor: color }}
                  />

                  {/* Zone name (editable) */}
                  <div className="flex-1 min-w-0">
                    {isEditing ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveEdit(zone.id);
                            if (e.key === 'Escape') handleCancelEdit();
                          }}
                          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
                          autoFocus
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSaveEdit(zone.id)}
                        >
                          <Check className="h-4 w-4 text-green-600" />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={handleCancelEdit}
                        >
                          <X className="h-4 w-4 text-red-600" />
                        </Button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">{zone.name}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleStartEdit(zone)}
                          className="h-6 w-6 p-0"
                        >
                          <Edit2 className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      {zone.vertices.length} vertices
                    </p>
                  </div>

                  {/* Enable/disable toggle */}
                  <div className="flex items-center gap-2">
                    <Label htmlFor={`zone-${zone.id}-enabled`} className="text-xs">
                      {zone.enabled ? 'Enabled' : 'Disabled'}
                    </Label>
                    <button
                      type="button"
                      id={`zone-${zone.id}-enabled`}
                      role="switch"
                      aria-checked={zone.enabled}
                      onClick={() => handleToggleEnabled(zone)}
                      className={`
                        relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50
                        ${zone.enabled ? 'bg-blue-600' : 'bg-gray-300'}
                      `}
                    >
                      <span
                        className={`
                          inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                          ${zone.enabled ? 'translate-x-4' : 'translate-x-0.5'}
                        `}
                      />
                    </button>
                  </div>

                  {/* Delete button */}
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteClick(zone.id)}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteConfirmZoneId !== null} onOpenChange={handleCancelDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Detection Zone?</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this detection zone? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleCancelDelete}>
              Cancel
            </Button>
            <Button type="button" variant="destructive" onClick={handleConfirmDelete}>
              Delete Zone
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
