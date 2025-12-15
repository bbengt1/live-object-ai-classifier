/**
 * DiscoveredCameraCard - Card component for displaying a discovered ONVIF camera
 *
 * Story P5-2.3: Build Camera Discovery UI with Add Action
 *
 * Shows camera details (name, manufacturer, model, IP) and stream profiles.
 * Provides "Add" button to add camera to ArgusAI.
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Camera, CheckCircle, Loader2, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { IDiscoveredCameraDetails, IStreamProfile } from '@/types/discovery';
import type { ICamera } from '@/types/camera';

interface DiscoveredCameraCardProps {
  /** Camera details from ONVIF discovery */
  camera: IDiscoveredCameraDetails;
  /** List of existing cameras to check for duplicates */
  existingCameras?: ICamera[];
  /** Whether device details are loading */
  isLoadingDetails?: boolean;
  /** Error message if device query failed */
  detailsError?: string | null;
}

/**
 * Check if a discovered camera is already added to ArgusAI
 * Compares IP address and port from existing RTSP URLs
 */
function isAlreadyAdded(
  discoveredIp: string,
  discoveredPort: number,
  existingCameras: ICamera[]
): boolean {
  return existingCameras.some((cam) => {
    if (cam.rtsp_url) {
      try {
        const url = new URL(cam.rtsp_url);
        const hostname = url.hostname;
        // Compare IP and port
        return hostname === discoveredIp;
      } catch {
        return false;
      }
    }
    return false;
  });
}

/**
 * Get the best profile from available stream profiles
 * Returns the profile with highest resolution
 */
function getBestProfile(profiles: IStreamProfile[]): IStreamProfile | null {
  if (profiles.length === 0) return null;
  return profiles.reduce((best, current) => {
    const bestPixels = best.width * best.height;
    const currentPixels = current.width * current.height;
    return currentPixels > bestPixels ? current : best;
  });
}

/**
 * Card component for a discovered ONVIF camera
 */
export function DiscoveredCameraCard({
  camera,
  existingCameras = [],
  isLoadingDetails = false,
  detailsError,
}: DiscoveredCameraCardProps) {
  const router = useRouter();
  const [selectedProfileToken, setSelectedProfileToken] = useState<string | null>(null);
  const [showProfiles, setShowProfiles] = useState(false);

  const alreadyAdded = isAlreadyAdded(camera.ip_address, camera.port, existingCameras);
  const bestProfile = getBestProfile(camera.profiles);

  // Get selected profile or default to best/primary
  const selectedProfile = selectedProfileToken
    ? camera.profiles.find((p) => p.token === selectedProfileToken)
    : bestProfile;

  const rtspUrl = selectedProfile?.rtsp_url || camera.primary_rtsp_url;

  /**
   * Handle add camera click - navigate to new camera form with pre-populated data
   */
  const handleAddCamera = () => {
    const params = new URLSearchParams({
      rtsp_url: rtspUrl,
      name: camera.device_info.name || `${camera.device_info.manufacturer} ${camera.device_info.model}`,
    });
    router.push(`/cameras/new?${params.toString()}`);
  };

  return (
    <div className="border rounded-lg p-4 bg-card hover:border-primary/50 transition-colors">
      {/* Header with camera icon and name */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            <Camera className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium truncate">
              {camera.device_info.name || camera.device_info.model}
            </h3>
            <p className="text-sm text-muted-foreground">
              {camera.device_info.manufacturer}
            </p>
          </div>
        </div>

        {/* Already added badge */}
        {alreadyAdded && (
          <Badge variant="secondary" className="flex items-center gap-1 shrink-0">
            <CheckCircle className="h-3 w-3" />
            Already Added
          </Badge>
        )}
      </div>

      {/* Loading state for details */}
      {isLoadingDetails && (
        <div className="flex items-center gap-2 text-muted-foreground text-sm py-4">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading camera details...
        </div>
      )}

      {/* Error state */}
      {detailsError && (
        <div className="flex items-start gap-2 text-destructive text-sm py-2">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{detailsError}</span>
        </div>
      )}

      {/* Camera details */}
      {!isLoadingDetails && !detailsError && (
        <>
          {/* IP and model info */}
          <div className="space-y-1 text-sm mb-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">IP Address:</span>
              <span className="font-mono">{camera.ip_address}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Model:</span>
              <span className="truncate ml-2">{camera.device_info.model}</span>
            </div>
            {camera.device_info.firmware_version && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Firmware:</span>
                <span className="truncate ml-2">{camera.device_info.firmware_version}</span>
              </div>
            )}
          </div>

          {/* Best profile info */}
          {bestProfile && (
            <div className="mb-3">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="font-mono">
                  {bestProfile.resolution}
                </Badge>
                <Badge variant="outline" className="font-mono">
                  {bestProfile.fps} FPS
                </Badge>
                {bestProfile.encoding && (
                  <Badge variant="outline">{bestProfile.encoding}</Badge>
                )}
              </div>
            </div>
          )}

          {/* Profile selector (expandable) */}
          {camera.profiles.length > 1 && (
            <div className="mb-3">
              <button
                type="button"
                onClick={() => setShowProfiles(!showProfiles)}
                className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {showProfiles ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
                {camera.profiles.length} stream profiles available
              </button>

              {showProfiles && (
                <div className="mt-2">
                  <Select
                    value={selectedProfileToken || bestProfile?.token || ''}
                    onValueChange={setSelectedProfileToken}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select stream profile" />
                    </SelectTrigger>
                    <SelectContent>
                      {camera.profiles.map((profile) => (
                        <SelectItem key={profile.token} value={profile.token}>
                          <span className="flex items-center gap-2">
                            {profile.name} - {profile.resolution} @ {profile.fps}fps
                            {profile.encoding && ` (${profile.encoding})`}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          )}

          {/* Auth required indicator */}
          {camera.requires_auth && (
            <div className="flex items-center gap-2 text-amber-600 text-sm mb-3">
              <AlertCircle className="h-4 w-4" />
              <span>Credentials may be required</span>
            </div>
          )}

          {/* Add button */}
          <Button
            onClick={handleAddCamera}
            disabled={alreadyAdded}
            className="w-full"
            variant={alreadyAdded ? 'secondary' : 'default'}
          >
            <Plus className="h-4 w-4 mr-2" />
            {alreadyAdded ? 'Already Added' : 'Add Camera'}
          </Button>
        </>
      )}
    </div>
  );
}
