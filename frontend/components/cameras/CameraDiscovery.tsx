/**
 * CameraDiscovery - ONVIF camera discovery component
 *
 * Story P5-2.3: Build Camera Discovery UI with Add Action
 *
 * Provides "Discover Cameras" button, displays discovered cameras,
 * and allows adding them to ArgusAI with pre-populated RTSP URLs.
 */

'use client';

import { useState, useCallback } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Radar,
  RefreshCw,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  SearchX,
} from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { DiscoveredCameraCard } from './DiscoveredCameraCard';
import type { ICamera } from '@/types/camera';
import type {
  IDiscoveredDevice,
  IDiscoveredCameraDetails,
} from '@/types/discovery';

interface CameraDiscoveryProps {
  /** List of existing cameras for "Already Added" detection */
  existingCameras?: ICamera[];
  /** Optional callback when discovery completes */
  onDiscoveryComplete?: (deviceCount: number) => void;
}

interface DiscoveryState {
  devices: IDiscoveredDevice[];
  deviceDetails: Map<string, IDiscoveredCameraDetails>;
  deviceErrors: Map<string, string>;
  loadingDetails: Set<string>;
  duration?: number;
}

/**
 * Camera discovery component with scan button and results
 */
export function CameraDiscovery({
  existingCameras = [],
  onDiscoveryComplete,
}: CameraDiscoveryProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [discoveryState, setDiscoveryState] = useState<DiscoveryState>({
    devices: [],
    deviceDetails: new Map(),
    deviceErrors: new Map(),
    loadingDetails: new Set(),
    duration: undefined,
  });

  // Check if discovery is available (WSDiscovery installed)
  const { data: discoveryStatus } = useQuery({
    queryKey: ['discovery', 'status'],
    queryFn: () => apiClient.discovery.status(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  // Discovery scan mutation
  const discoverMutation = useMutation({
    mutationFn: () => apiClient.discovery.start(),
    onSuccess: async (data) => {
      setDiscoveryState((prev) => ({
        ...prev,
        devices: data.devices,
        duration: data.duration_ms,
        deviceDetails: new Map(),
        deviceErrors: new Map(),
        loadingDetails: new Set(),
      }));

      // Auto-expand results if any devices found
      if (data.devices.length > 0) {
        setIsExpanded(true);
        // Fetch details for each discovered device
        for (const device of data.devices) {
          fetchDeviceDetails(device.endpoint_url);
        }
      }

      onDiscoveryComplete?.(data.device_count);
    },
  });

  // Fetch device details for a single device
  const fetchDeviceDetails = useCallback(async (endpointUrl: string) => {
    // Mark as loading
    setDiscoveryState((prev) => ({
      ...prev,
      loadingDetails: new Set(prev.loadingDetails).add(endpointUrl),
    }));

    try {
      const result = await apiClient.discovery.getDeviceDetails(endpointUrl);

      setDiscoveryState((prev) => {
        const newLoadingDetails = new Set(prev.loadingDetails);
        newLoadingDetails.delete(endpointUrl);

        if (result.status === 'success' && result.device) {
          const newDeviceDetails = new Map(prev.deviceDetails);
          newDeviceDetails.set(endpointUrl, result.device);
          return {
            ...prev,
            loadingDetails: newLoadingDetails,
            deviceDetails: newDeviceDetails,
          };
        } else {
          const newDeviceErrors = new Map(prev.deviceErrors);
          newDeviceErrors.set(
            endpointUrl,
            result.error_message || 'Failed to get device details'
          );
          return {
            ...prev,
            loadingDetails: newLoadingDetails,
            deviceErrors: newDeviceErrors,
          };
        }
      });
    } catch (error) {
      setDiscoveryState((prev) => {
        const newLoadingDetails = new Set(prev.loadingDetails);
        newLoadingDetails.delete(endpointUrl);
        const newDeviceErrors = new Map(prev.deviceErrors);
        newDeviceErrors.set(
          endpointUrl,
          error instanceof Error ? error.message : 'Failed to get device details'
        );
        return {
          ...prev,
          loadingDetails: newLoadingDetails,
          deviceErrors: newDeviceErrors,
        };
      });
    }
  }, []);

  // Handle discover button click
  const handleDiscover = () => {
    setIsExpanded(true);
    discoverMutation.mutate();
  };

  // Handle retry button click
  const handleRetry = () => {
    setDiscoveryState({
      devices: [],
      deviceDetails: new Map(),
      deviceErrors: new Map(),
      loadingDetails: new Set(),
      duration: undefined,
    });
    discoverMutation.mutate();
  };

  const isScanning = discoverMutation.isPending;
  const hasResults = discoveryState.devices.length > 0;
  const hasError = discoverMutation.isError;
  const discoveryUnavailable = discoveryStatus && !discoveryStatus.available;

  return (
    <div className="border rounded-lg bg-card">
      {/* Header with discover button */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            <Radar className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-medium">ONVIF Camera Discovery</h3>
            <p className="text-sm text-muted-foreground">
              Scan your network for ONVIF-compatible cameras
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Toggle button for results */}
          {hasResults && !isScanning && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              <span className="ml-1">{discoveryState.devices.length} found</span>
            </Button>
          )}

          {/* Discover/Retry button */}
          <Button
            onClick={hasResults ? handleRetry : handleDiscover}
            disabled={isScanning || discoveryUnavailable}
            variant={hasResults ? 'outline' : 'default'}
          >
            {isScanning ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Scanning...
              </>
            ) : hasResults ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Rescan
              </>
            ) : (
              <>
                <Radar className="h-4 w-4 mr-2" />
                Discover Cameras
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Discovery unavailable warning */}
      {discoveryUnavailable && (
        <div className="px-4 pb-4">
          <div className="flex items-start gap-2 p-3 rounded-md bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200">
            <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Camera Discovery Unavailable</p>
              <p className="text-sm mt-1">
                {discoveryStatus?.message || 'WSDiscovery package not installed on server.'}
              </p>
              <p className="text-sm mt-1">
                You can still add cameras manually using their RTSP URLs.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Scanning indicator */}
      {isScanning && (
        <div className="px-4 pb-4">
          <div className="flex items-center gap-3 p-4 rounded-md bg-muted/50">
            <RefreshCw className="h-5 w-5 animate-spin text-primary" />
            <div>
              <p className="font-medium">Scanning network for cameras...</p>
              <p className="text-sm text-muted-foreground">
                This may take up to 10 seconds
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Error state */}
      {hasError && !isScanning && (
        <div className="px-4 pb-4">
          <div className="flex items-start gap-2 p-3 rounded-md bg-destructive/10 text-destructive">
            <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Discovery Failed</p>
              <p className="text-sm mt-1">
                {discoverMutation.error instanceof Error
                  ? discoverMutation.error.message
                  : 'An error occurred during network scan.'}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRetry}
                className="mt-2"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry Scan
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isScanning && !hasError && discoveryState.duration !== undefined && !hasResults && (
        <div className="px-4 pb-4">
          <div className="flex flex-col items-center justify-center p-6 text-center">
            <SearchX className="h-12 w-12 text-muted-foreground mb-3" />
            <h4 className="font-medium mb-1">No ONVIF Cameras Found</h4>
            <p className="text-sm text-muted-foreground mb-3 max-w-md">
              No ONVIF-compatible cameras were discovered on your network.
              This could be because:
            </p>
            <ul className="text-sm text-muted-foreground text-left list-disc list-inside mb-4 space-y-1">
              <li>Your cameras don&apos;t support ONVIF</li>
              <li>Cameras are on a different network/VLAN</li>
              <li>Firewall blocking multicast discovery</li>
              <li>Cameras are powered off or disconnected</li>
            </ul>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleRetry}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/cameras/new">Add Manually</Link>
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Discovery results */}
      {isExpanded && hasResults && !isScanning && (
        <div className="px-4 pb-4 border-t">
          {/* Results info */}
          <div className="flex items-center gap-2 py-3 text-sm text-muted-foreground">
            <Info className="h-4 w-4" />
            <span>
              Found {discoveryState.devices.length} camera
              {discoveryState.devices.length !== 1 ? 's' : ''} in{' '}
              {((discoveryState.duration || 0) / 1000).toFixed(1)}s
            </span>
          </div>

          {/* Camera cards grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {discoveryState.devices.map((device) => {
              const details = discoveryState.deviceDetails.get(device.endpoint_url);
              const error = discoveryState.deviceErrors.get(device.endpoint_url);
              const isLoading = discoveryState.loadingDetails.has(device.endpoint_url);

              // If we have details, show the detailed card
              if (details) {
                return (
                  <DiscoveredCameraCard
                    key={device.endpoint_url}
                    camera={details}
                    existingCameras={existingCameras}
                    isLoadingDetails={false}
                    detailsError={null}
                  />
                );
              }

              // Show placeholder card while loading or on error
              return (
                <DiscoveredCameraPlaceholder
                  key={device.endpoint_url}
                  device={device}
                  isLoading={isLoading}
                  error={error}
                  onRetry={() => fetchDeviceDetails(device.endpoint_url)}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Placeholder card for discovered device while loading details
 */
function DiscoveredCameraPlaceholder({
  device,
  isLoading,
  error,
  onRetry,
}: {
  device: IDiscoveredDevice;
  isLoading: boolean;
  error?: string;
  onRetry: () => void;
}) {
  // Extract IP from endpoint URL
  let ipAddress = 'Unknown';
  try {
    const url = new URL(device.endpoint_url);
    ipAddress = url.hostname;
  } catch {
    // Keep default
  }

  return (
    <div className="border rounded-lg p-4 bg-card">
      <div className="flex items-start gap-3 mb-3">
        <div className="p-2 rounded-lg bg-muted text-muted-foreground">
          <Radar className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medium truncate">ONVIF Camera</h3>
          <p className="text-sm text-muted-foreground font-mono">{ipAddress}</p>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-muted-foreground text-sm py-4">
          <RefreshCw className="h-4 w-4 animate-spin" />
          Loading camera details...
        </div>
      )}

      {error && (
        <div className="space-y-2">
          <div className="flex items-start gap-2 text-destructive text-sm">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span className="line-clamp-2">{error}</span>
          </div>
          <Button variant="outline" size="sm" onClick={onRetry} className="w-full">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      )}
    </div>
  );
}
