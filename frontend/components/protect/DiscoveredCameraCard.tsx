/**
 * Discovered Camera Card Component
 * Story P2-2.2: Build Discovered Camera List UI with Enable/Disable
 *
 * Displays a single discovered camera from UniFi Protect controller with:
 * - Enable/disable checkbox
 * - Camera/doorbell icon based on type
 * - Camera name (bold) and type/model (muted)
 * - Online/offline status indicator
 * - Configure Filters button (placeholder for Story P2-2.3)
 *
 * AC2: All required elements displayed
 * AC4: Disabled cameras at 50% opacity with "(Disabled)" label
 * AC5: Offline cameras show red status dot with "Offline" badge
 */

'use client';

import { Camera, Bell, Settings2 } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { ProtectDiscoveredCamera } from '@/lib/api-client';

export interface DiscoveredCameraCardProps {
  camera: ProtectDiscoveredCamera;
  onToggleEnabled: (cameraId: string, enabled: boolean) => void;
  isToggling?: boolean;
}

export function DiscoveredCameraCard({
  camera,
  onToggleEnabled,
  isToggling = false,
}: DiscoveredCameraCardProps) {
  const handleCheckboxChange = (checked: boolean | 'indeterminate') => {
    if (checked !== 'indeterminate') {
      onToggleEnabled(camera.protect_camera_id, checked);
    }
  };

  // Determine icon based on camera type
  const CameraIcon = camera.is_doorbell ? Bell : Camera;

  return (
    <div
      className={cn(
        'flex items-center justify-between p-4 rounded-lg border bg-card transition-opacity',
        !camera.is_enabled_for_ai && 'opacity-50'
      )}
    >
      {/* Left side: Checkbox, Icon, Name, Type */}
      <div className="flex items-center gap-3">
        {/* Enable Checkbox (AC2) */}
        <Checkbox
          checked={camera.is_enabled_for_ai}
          onCheckedChange={handleCheckboxChange}
          disabled={isToggling}
          aria-label={`Enable ${camera.name} for AI analysis`}
        />

        {/* Camera Icon (AC2) - Doorbell or Camera based on type */}
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-muted">
          <CameraIcon className="h-4 w-4 text-muted-foreground" />
        </div>

        {/* Camera Info */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            {/* Camera Name (bold) (AC2) */}
            <span className="font-medium">{camera.name}</span>

            {/* Disabled Label (AC4) */}
            {!camera.is_enabled_for_ai && (
              <span className="text-xs text-muted-foreground">(Disabled)</span>
            )}
          </div>

          {/* Camera Type/Model (muted) (AC2) */}
          <span className="text-sm text-muted-foreground">{camera.model}</span>
        </div>
      </div>

      {/* Right side: Status, Configure Filters */}
      <div className="flex items-center gap-3">
        {/* Status Indicator (AC2, AC5) */}
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'h-2.5 w-2.5 rounded-full',
              camera.is_online ? 'bg-green-500' : 'bg-red-500'
            )}
            aria-label={camera.is_online ? 'Online' : 'Offline'}
          />
          {/* Offline Badge (AC5) */}
          {!camera.is_online && (
            <Badge variant="destructive" className="text-xs">
              Offline
            </Badge>
          )}
        </div>

        {/* Configure Filters Button (AC2) - Placeholder for Story P2-2.3 */}
        <Button
          variant="outline"
          size="sm"
          disabled={!camera.is_enabled_for_ai}
          className="gap-1"
        >
          <Settings2 className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Filters</span>
        </Button>
      </div>
    </div>
  );
}
