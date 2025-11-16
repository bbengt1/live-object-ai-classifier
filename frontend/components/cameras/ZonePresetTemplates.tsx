'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { IZoneVertex } from '@/types/camera';
import { Square, Triangle, MoveHorizontal } from 'lucide-react';

interface ZonePresetTemplatesProps {
  /**
   * Callback when user selects a preset template
   * @param vertices - Pre-defined vertices for the selected shape (normalized 0-1)
   */
  onTemplateSelect: (vertices: IZoneVertex[]) => void;
}

/**
 * Preset template shapes with normalized coordinates (0-1 scale)
 */
const PRESET_TEMPLATES = {
  /**
   * Rectangle template - centered, covering ~60% of canvas
   */
  rectangle: (): IZoneVertex[] => [
    { x: 0.2, y: 0.2 },  // Top-left
    { x: 0.8, y: 0.2 },  // Top-right
    { x: 0.8, y: 0.8 },  // Bottom-right
    { x: 0.2, y: 0.8 },  // Bottom-left
  ],

  /**
   * Triangle template - centered, pointing upward
   */
  triangle: (): IZoneVertex[] => [
    { x: 0.5, y: 0.2 },  // Top
    { x: 0.8, y: 0.8 },  // Bottom-right
    { x: 0.2, y: 0.8 },  // Bottom-left
  ],

  /**
   * L-shape template - bottom-left corner
   * Useful for covering entryways, doorways, or specific corners
   */
  lShape: (): IZoneVertex[] => [
    { x: 0.1, y: 0.1 },  // Top-left of vertical part
    { x: 0.3, y: 0.1 },  // Top-right of vertical part
    { x: 0.3, y: 0.6 },  // Elbow inner corner
    { x: 0.9, y: 0.6 },  // Top-right of horizontal part
    { x: 0.9, y: 0.9 },  // Bottom-right
    { x: 0.1, y: 0.9 },  // Bottom-left
  ],
};

/**
 * ZonePresetTemplates - Preset shape templates for quick zone creation
 *
 * Features:
 * - Pre-defined shapes: Rectangle, Triangle, L-shape
 * - Normalized coordinates (0-1 scale) for responsive display
 * - One-click zone creation for common use cases
 * - Visual icons matching each shape
 */
export function ZonePresetTemplates({ onTemplateSelect }: ZonePresetTemplatesProps) {
  const handleRectangle = () => {
    onTemplateSelect(PRESET_TEMPLATES.rectangle());
  };

  const handleTriangle = () => {
    onTemplateSelect(PRESET_TEMPLATES.triangle());
  };

  const handleLShape = () => {
    onTemplateSelect(PRESET_TEMPLATES.lShape());
  };

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium text-muted-foreground">
        Quick Templates
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleRectangle}
          className="flex items-center gap-2"
        >
          <Square className="h-4 w-4" />
          Rectangle
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleTriangle}
          className="flex items-center gap-2"
        >
          <Triangle className="h-4 w-4" />
          Triangle
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleLShape}
          className="flex items-center gap-2"
        >
          <MoveHorizontal className="h-4 w-4" />
          L-Shape
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        Click a template to use a pre-defined shape, or draw your own custom polygon
      </p>
    </div>
  );
}
