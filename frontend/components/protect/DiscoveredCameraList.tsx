/**
 * Discovered Camera List Component
 * Story P2-2.2: Build Discovered Camera List UI with Enable/Disable
 *
 * Displays all cameras discovered from a connected UniFi Protect controller with:
 * - Header with camera count and refresh button
 * - Loading state with skeleton cards
 * - Empty state for no cameras / disconnected controller
 * - Responsive grid layout (1 column mobile, 2 columns tablet/desktop)
 * - Sorted list: enabled cameras first, then alphabetical by name
 *
 * AC1: "Discovered Cameras (N found)" section with camera list
 * AC3: Sorted list with enabled cameras first
 * AC10: Empty states for no cameras / disconnected
 * AC11: Loading state with skeleton cards
 * AC12: Responsive layout
 */

'use client';

import { useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Camera, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { apiClient, type ProtectDiscoveredCamera } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { DiscoveredCameraCard } from './DiscoveredCameraCard';

export interface DiscoveredCameraListProps {
  controllerId: string;
  isControllerConnected: boolean;
}

/**
 * Sort cameras: enabled first, then alphabetical by name (AC3)
 */
function sortCameras(cameras: ProtectDiscoveredCamera[]): ProtectDiscoveredCamera[] {
  return [...cameras].sort((a, b) => {
    // Enabled cameras first
    if (a.is_enabled_for_ai !== b.is_enabled_for_ai) {
      return a.is_enabled_for_ai ? -1 : 1;
    }
    // Then alphabetical by name
    return a.name.localeCompare(b.name);
  });
}

/**
 * Skeleton placeholder for loading state (AC11)
 */
function CameraCardSkeleton() {
  return (
    <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
      <div className="flex items-center gap-3">
        <Skeleton className="h-4 w-4 rounded" />
        <Skeleton className="h-8 w-8 rounded-full" />
        <div className="flex flex-col gap-1">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Skeleton className="h-2.5 w-2.5 rounded-full" />
        <Skeleton className="h-8 w-20" />
      </div>
    </div>
  );
}

export function DiscoveredCameraList({
  controllerId,
  isControllerConnected,
}: DiscoveredCameraListProps) {
  const queryClient = useQueryClient();

  // Fetch discovered cameras with 60-second stale time (matching backend cache)
  const camerasQuery = useQuery({
    queryKey: ['protect-cameras', controllerId],
    queryFn: () => apiClient.protect.discoverCameras(controllerId),
    enabled: isControllerConnected && !!controllerId,
    staleTime: 60 * 1000, // 60 seconds to match backend cache
    refetchOnWindowFocus: false,
  });

  // Enable camera mutation with optimistic update (AC8)
  const enableMutation = useMutation({
    mutationFn: (cameraId: string) =>
      apiClient.protect.enableCamera(controllerId, cameraId),
    onMutate: async (cameraId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['protect-cameras', controllerId] });

      // Snapshot previous value
      const previousCameras = queryClient.getQueryData(['protect-cameras', controllerId]);

      // Optimistic update
      queryClient.setQueryData(
        ['protect-cameras', controllerId],
        (old: { data: ProtectDiscoveredCamera[]; meta: unknown } | undefined) => {
          if (!old) return old;
          return {
            ...old,
            data: old.data.map((cam) =>
              cam.protect_camera_id === cameraId
                ? { ...cam, is_enabled_for_ai: true }
                : cam
            ),
          };
        }
      );

      return { previousCameras };
    },
    onError: (_err, _cameraId, context) => {
      // Rollback on error (AC8)
      if (context?.previousCameras) {
        queryClient.setQueryData(['protect-cameras', controllerId], context.previousCameras);
      }
      toast.error('Failed to enable camera');
    },
    onSuccess: () => {
      toast.success('Camera enabled'); // AC9
    },
    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['protect-cameras', controllerId] });
    },
  });

  // Disable camera mutation with optimistic update (AC8)
  const disableMutation = useMutation({
    mutationFn: (cameraId: string) =>
      apiClient.protect.disableCamera(controllerId, cameraId),
    onMutate: async (cameraId) => {
      await queryClient.cancelQueries({ queryKey: ['protect-cameras', controllerId] });

      const previousCameras = queryClient.getQueryData(['protect-cameras', controllerId]);

      queryClient.setQueryData(
        ['protect-cameras', controllerId],
        (old: { data: ProtectDiscoveredCamera[]; meta: unknown } | undefined) => {
          if (!old) return old;
          return {
            ...old,
            data: old.data.map((cam) =>
              cam.protect_camera_id === cameraId
                ? { ...cam, is_enabled_for_ai: false }
                : cam
            ),
          };
        }
      );

      return { previousCameras };
    },
    onError: (_err, _cameraId, context) => {
      if (context?.previousCameras) {
        queryClient.setQueryData(['protect-cameras', controllerId], context.previousCameras);
      }
      toast.error('Failed to disable camera');
    },
    onSuccess: () => {
      toast.success('Camera disabled'); // AC9
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['protect-cameras', controllerId] });
    },
  });

  // Handle toggle enable/disable
  const handleToggleEnabled = (cameraId: string, enabled: boolean) => {
    if (enabled) {
      enableMutation.mutate(cameraId);
    } else {
      disableMutation.mutate(cameraId);
    }
  };

  // Handle refresh button click
  const handleRefresh = () => {
    // Force refresh bypasses backend cache
    queryClient.invalidateQueries({ queryKey: ['protect-cameras', controllerId] });
    toast.info('Refreshing camera list...');
  };

  // Sort cameras (AC3)
  const sortedCameras = useMemo(() => {
    if (!camerasQuery.data?.data) return [];
    return sortCameras(camerasQuery.data.data);
  }, [camerasQuery.data?.data]);

  const cameraCount = camerasQuery.data?.meta?.count ?? 0;
  const isLoading = camerasQuery.isLoading;
  const isRefetching = camerasQuery.isRefetching;

  // Disconnected state (AC10)
  if (!isControllerConnected) {
    return (
      <div className="mt-6 pt-6 border-t">
        <h3 className="text-lg font-semibold mb-4">Discovered Cameras</h3>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Camera className="h-12 w-12 text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground">
            Connect your controller to discover cameras
          </p>
        </div>
      </div>
    );
  }

  // Loading state (AC11)
  if (isLoading) {
    return (
      <div className="mt-6 pt-6 border-t">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Discovered Cameras</h3>
          <Button variant="outline" size="sm" disabled>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Loading...
          </Button>
        </div>
        {/* Skeleton cards (AC11) - 3 placeholder cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <CameraCardSkeleton />
          <CameraCardSkeleton />
          <CameraCardSkeleton />
        </div>
      </div>
    );
  }

  // Empty state - no cameras found (AC10)
  if (sortedCameras.length === 0) {
    return (
      <div className="mt-6 pt-6 border-t">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Discovered Cameras (0 found)</h3>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefetching}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Camera className="h-12 w-12 text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground">
            No cameras found. Check your Protect controller.
          </p>
        </div>
      </div>
    );
  }

  // Populated state with camera list
  return (
    <div className="mt-6 pt-6 border-t">
      {/* Header with count and refresh button (AC1) */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">
          Discovered Cameras ({cameraCount} found)
        </h3>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefetching}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Camera grid - responsive layout (AC12) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {sortedCameras.map((camera) => (
          <DiscoveredCameraCard
            key={camera.protect_camera_id}
            camera={camera}
            onToggleEnabled={handleToggleEnabled}
            isToggling={
              enableMutation.isPending || disableMutation.isPending
            }
          />
        ))}
      </div>
    </div>
  );
}
