'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { IDetectionZone, IZoneVertex } from '@/types/camera';
import { Undo2, Check, X } from 'lucide-react';

interface DetectionZoneDrawerProps {
  /**
   * Existing zones to render as overlays
   */
  zones: IDetectionZone[];
  /**
   * Callback when user finishes drawing a new zone
   * @param vertices - Array of vertices in normalized 0-1 scale
   */
  onZoneComplete: (vertices: IZoneVertex[]) => void;
  /**
   * Callback when user cancels drawing
   */
  onCancel: () => void;
  /**
   * Width of the canvas (default: 640)
   */
  canvasWidth?: number;
  /**
   * Height of the canvas (default: 480)
   */
  canvasHeight?: number;
  /**
   * Optional camera preview image (base64 or URL)
   */
  previewImage?: string;
}

/**
 * Color palette for zone overlays (cycling through distinct colors)
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
 * DetectionZoneDrawer - Interactive polygon drawing canvas for detection zones
 *
 * Features:
 * - HTML5 Canvas with click handlers for polygon drawing
 * - Vertex tracking with normalized coordinates (0-1 scale)
 * - Double-click or "Finish" button to close polygon
 * - "Undo Last Vertex" button to remove mistakes
 * - Visual feedback: vertex markers, first vertex highlighted, vertex count indicator
 * - Renders existing zones as overlays with distinct colors
 */
export function DetectionZoneDrawer({
  zones,
  onZoneComplete,
  onCancel,
  canvasWidth = 640,
  canvasHeight = 480,
  previewImage,
}: DetectionZoneDrawerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [vertices, setVertices] = useState<IZoneVertex[]>([]);
  const [previewImageLoaded, setPreviewImageLoaded] = useState(false);
  const imageRef = useRef<HTMLImageElement | null>(null);

  // Load preview image if provided
  useEffect(() => {
    if (previewImage) {
      const img = new Image();
      img.onload = () => {
        imageRef.current = img;
        setPreviewImageLoaded(true);
      };
      img.src = previewImage;
    }
  }, [previewImage]);

  /**
   * Normalize canvas coordinates to 0-1 scale
   */
  const normalizeCoordinate = useCallback((x: number, y: number): IZoneVertex => {
    return {
      x: Math.max(0, Math.min(1, x / canvasWidth)),
      y: Math.max(0, Math.min(1, y / canvasHeight)),
    };
  }, [canvasWidth, canvasHeight]);

  /**
   * Denormalize 0-1 coordinates to canvas pixel coordinates
   */
  const denormalizeCoordinate = useCallback((vertex: IZoneVertex): { x: number; y: number } => {
    return {
      x: vertex.x * canvasWidth,
      y: vertex.y * canvasHeight,
    };
  }, [canvasWidth, canvasHeight]);

  /**
   * Handle canvas click to add vertex
   */
  const handleCanvasClick = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const normalized = normalizeCoordinate(x, y);
    setVertices((prev) => [...prev, normalized]);
  }, [normalizeCoordinate]);

  /**
   * Handle canvas double-click to finish polygon
   */
  const handleCanvasDoubleClick = useCallback(() => {
    if (vertices.length >= 3) {
      onZoneComplete(vertices);
      setVertices([]);
    }
  }, [vertices, onZoneComplete]);

  /**
   * Handle "Undo Last Vertex" button
   */
  const handleUndo = useCallback(() => {
    setVertices((prev) => prev.slice(0, -1));
  }, []);

  /**
   * Handle "Finish" button
   */
  const handleFinish = useCallback(() => {
    if (vertices.length >= 3) {
      onZoneComplete(vertices);
      setVertices([]);
    }
  }, [vertices, onZoneComplete]);

  /**
   * Handle "Cancel" button
   */
  const handleCancelDrawing = useCallback(() => {
    setVertices([]);
    onCancel();
  }, [onCancel]);

  /**
   * Draw canvas overlay with existing zones and current polygon
   */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    // Draw preview image if loaded
    if (previewImageLoaded && imageRef.current) {
      ctx.drawImage(imageRef.current, 0, 0, canvasWidth, canvasHeight);
    } else {
      // Draw placeholder background (light gray)
      ctx.fillStyle = '#f3f4f6';
      ctx.fillRect(0, 0, canvasWidth, canvasHeight);
    }

    // Draw existing zones as overlays
    zones.forEach((zone, index) => {
      const color = ZONE_COLORS[index % ZONE_COLORS.length];
      const opacity = zone.enabled ? 0.3 : 0.1;

      ctx.fillStyle = color + Math.floor(opacity * 255).toString(16).padStart(2, '0');
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;

      if (zone.vertices.length > 0) {
        ctx.beginPath();
        const first = denormalizeCoordinate(zone.vertices[0]);
        ctx.moveTo(first.x, first.y);

        zone.vertices.slice(1).forEach((vertex) => {
          const point = denormalizeCoordinate(vertex);
          ctx.lineTo(point.x, point.y);
        });

        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Draw zone name label
        ctx.fillStyle = color;
        ctx.font = '14px sans-serif';
        ctx.fillText(zone.name, first.x + 5, first.y - 5);
      }
    });

    // Draw current polygon being drawn
    if (vertices.length > 0) {
      ctx.strokeStyle = '#3b82f6'; // blue-500
      ctx.fillStyle = '#3b82f633'; // blue-500 with 20% opacity
      ctx.lineWidth = 2;

      ctx.beginPath();
      const first = denormalizeCoordinate(vertices[0]);
      ctx.moveTo(first.x, first.y);

      vertices.slice(1).forEach((vertex) => {
        const point = denormalizeCoordinate(vertex);
        ctx.lineTo(point.x, point.y);
      });

      // Close path visually (line back to first vertex) but don't fill yet
      if (vertices.length >= 3) {
        ctx.lineTo(first.x, first.y);
        ctx.fill();
      }

      ctx.stroke();

      // Draw vertex markers
      vertices.forEach((vertex, index) => {
        const point = denormalizeCoordinate(vertex);

        // Highlight first vertex
        if (index === 0) {
          ctx.fillStyle = '#ef4444'; // red-500 for first vertex
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(point.x, point.y, 6, 0, 2 * Math.PI);
          ctx.fill();
          ctx.stroke();
        } else {
          ctx.fillStyle = '#3b82f6'; // blue-500 for other vertices
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(point.x, point.y, 4, 0, 2 * Math.PI);
          ctx.fill();
          ctx.stroke();
        }
      });
    }
  }, [zones, vertices, canvasWidth, canvasHeight, denormalizeCoordinate, previewImageLoaded]);

  return (
    <div className="space-y-4">
      {/* Vertex count indicator */}
      <div className="flex items-center justify-between bg-muted/20 p-3 rounded-md border">
        <div className="text-sm font-medium">
          {vertices.length === 0 && 'Click on the canvas to start drawing a polygon'}
          {vertices.length > 0 && vertices.length < 3 && (
            <>
              <span className="text-blue-600 font-semibold">{vertices.length} vertices</span>
              <span className="text-muted-foreground"> - need at least 3 to finish (click to add more)</span>
            </>
          )}
          {vertices.length >= 3 && (
            <>
              <span className="text-green-600 font-semibold">{vertices.length} vertices</span>
              <span className="text-muted-foreground"> - click to add more, double-click or press Finish to complete</span>
            </>
          )}
        </div>

        {/* Control buttons */}
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleUndo}
            disabled={vertices.length === 0}
          >
            <Undo2 className="h-4 w-4 mr-1" />
            Undo Last
          </Button>
          <Button
            type="button"
            variant="default"
            size="sm"
            onClick={handleFinish}
            disabled={vertices.length < 3}
          >
            <Check className="h-4 w-4 mr-1" />
            Finish
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleCancelDrawing}
          >
            <X className="h-4 w-4 mr-1" />
            Cancel
          </Button>
        </div>
      </div>

      {/* Canvas */}
      <div className="border rounded-md overflow-hidden bg-muted/10">
        <canvas
          ref={canvasRef}
          width={canvasWidth}
          height={canvasHeight}
          onClick={handleCanvasClick}
          onDoubleClick={handleCanvasDoubleClick}
          className="cursor-crosshair w-full"
          style={{ maxWidth: '100%', height: 'auto' }}
        />
      </div>
    </div>
  );
}
