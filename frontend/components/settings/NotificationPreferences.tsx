/**
 * Notification Preferences Component (Story P4-1.4)
 *
 * Features:
 * - Per-camera notification toggles
 * - Object type filters (person, vehicle, package, animal)
 * - Quiet hours configuration with timezone
 * - Sound enable/disable
 */

'use client';

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import {
  Camera,
  Clock,
  Volume2,
  VolumeX,
  User,
  Car,
  Package,
  Dog,
  Loader2,
  RefreshCw,
  Globe,
} from 'lucide-react';

import { useNotificationPreferences } from '@/hooks/useNotificationPreferences';
import { useCameras } from '@/hooks/useCameras';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { OBJECT_TYPES, COMMON_TIMEZONES } from '@/types/push';

interface NotificationPreferencesProps {
  /**
   * Push subscription endpoint URL
   */
  endpoint: string | null;
  /**
   * Whether the user is subscribed to push notifications
   */
  isSubscribed: boolean;
}

/**
 * Object type icons mapping
 */
const ObjectTypeIcons: Record<string, React.ElementType> = {
  person: User,
  vehicle: Car,
  package: Package,
  animal: Dog,
};

/**
 * Notification Preferences Component
 */
export function NotificationPreferences({ endpoint, isSubscribed }: NotificationPreferencesProps) {
  const {
    preferences,
    loading,
    saving,
    error,
    refresh,
    updatePreferences,
  } = useNotificationPreferences({ endpoint, autoFetch: isSubscribed });

  const { cameras, loading: camerasLoading } = useCameras({ autoFetch: isSubscribed });

  // Local state for form inputs
  const [quietHoursStart, setQuietHoursStart] = useState('22:00');
  const [quietHoursEnd, setQuietHoursEnd] = useState('07:00');

  // Sync local state with preferences when loaded
  useEffect(() => {
    if (preferences) {
      if (preferences.quiet_hours_start) {
        setQuietHoursStart(preferences.quiet_hours_start);
      }
      if (preferences.quiet_hours_end) {
        setQuietHoursEnd(preferences.quiet_hours_end);
      }
    }
  }, [preferences]);

  // Don't render if not subscribed
  if (!isSubscribed) {
    return null;
  }

  // Loading state
  if (loading && !preferences) {
    return (
      <Card className="mt-4">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">Loading preferences...</span>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error && !preferences) {
    return (
      <Card className="mt-4">
        <CardContent className="py-6">
          <div className="text-center">
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="outline" size="sm" className="mt-2" onClick={refresh}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!preferences) {
    return null;
  }

  // Handlers
  const handleCameraToggle = async (cameraId: string, enabled: boolean) => {
    const currentCameras = preferences.enabled_cameras;
    let newCameras: string[] | null;

    if (enabled) {
      // Enable camera: if currently null (all), switch to explicit list minus this one inverted
      if (currentCameras === null) {
        // All cameras are enabled, so enabling one doesn't change anything
        return;
      }
      // Add to list
      newCameras = [...currentCameras, cameraId];
      // If all cameras are now enabled, set to null
      if (cameras.length > 0 && newCameras.length >= cameras.length) {
        newCameras = null;
      }
    } else {
      // Disable camera
      if (currentCameras === null) {
        // Switch from "all" to explicit list minus this camera
        newCameras = cameras.map(c => c.id).filter(id => id !== cameraId);
      } else {
        // Remove from list
        newCameras = currentCameras.filter(id => id !== cameraId);
      }
    }

    const success = await updatePreferences({ enabled_cameras: newCameras });
    if (success) {
      toast.success(`Camera notifications ${enabled ? 'enabled' : 'disabled'}`);
    } else {
      toast.error('Failed to update camera setting');
    }
  };

  const handleObjectTypeToggle = async (objectType: string, enabled: boolean) => {
    const currentTypes = preferences.enabled_object_types;
    let newTypes: string[] | null;

    if (enabled) {
      if (currentTypes === null) {
        return; // Already all enabled
      }
      newTypes = [...currentTypes, objectType];
      // If all types now enabled, set to null
      if (newTypes.length >= OBJECT_TYPES.length) {
        newTypes = null;
      }
    } else {
      if (currentTypes === null) {
        // Switch from "all" to explicit list minus this type
        newTypes = OBJECT_TYPES.map(t => t.value).filter(t => t !== objectType);
      } else {
        newTypes = currentTypes.filter(t => t !== objectType);
      }
    }

    const success = await updatePreferences({ enabled_object_types: newTypes });
    if (success) {
      toast.success(`${objectType} notifications ${enabled ? 'enabled' : 'disabled'}`);
    } else {
      toast.error('Failed to update object type setting');
    }
  };

  const handleQuietHoursToggle = async (enabled: boolean) => {
    const success = await updatePreferences({
      quiet_hours_enabled: enabled,
      quiet_hours_start: enabled ? quietHoursStart : null,
      quiet_hours_end: enabled ? quietHoursEnd : null,
    });
    if (success) {
      toast.success(`Quiet hours ${enabled ? 'enabled' : 'disabled'}`);
    } else {
      toast.error('Failed to update quiet hours');
    }
  };

  const handleQuietHoursTimeChange = async (start: string, end: string) => {
    setQuietHoursStart(start);
    setQuietHoursEnd(end);

    if (preferences.quiet_hours_enabled) {
      const success = await updatePreferences({
        quiet_hours_start: start,
        quiet_hours_end: end,
      });
      if (!success) {
        toast.error('Failed to update quiet hours');
      }
    }
  };

  const handleTimezoneChange = async (timezone: string) => {
    const success = await updatePreferences({ timezone });
    if (success) {
      toast.success('Timezone updated');
    } else {
      toast.error('Failed to update timezone');
    }
  };

  const handleSoundToggle = async (enabled: boolean) => {
    const success = await updatePreferences({ sound_enabled: enabled });
    if (success) {
      toast.success(`Notification sound ${enabled ? 'enabled' : 'disabled'}`);
    } else {
      toast.error('Failed to update sound setting');
    }
  };

  const isCameraEnabled = (cameraId: string) => {
    return preferences.enabled_cameras === null || preferences.enabled_cameras.includes(cameraId);
  };

  const isObjectTypeEnabled = (objectType: string) => {
    return preferences.enabled_object_types === null || preferences.enabled_object_types.includes(objectType);
  };

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="text-lg">Notification Preferences</CardTitle>
        <CardDescription>
          Customize which notifications you receive and when
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Camera Filters */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Camera className="h-4 w-4 text-muted-foreground" />
            <Label className="text-sm font-medium">Cameras</Label>
          </div>
          <p className="text-xs text-muted-foreground">
            Select which cameras can send you notifications
          </p>
          <div className="space-y-2 rounded-lg border p-3">
            {camerasLoading ? (
              <div className="flex items-center py-2">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">Loading cameras...</span>
              </div>
            ) : cameras.length === 0 ? (
              <p className="text-sm text-muted-foreground py-2">No cameras configured</p>
            ) : (
              cameras.map((camera) => (
                <div key={camera.id} className="flex items-center justify-between py-1">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id={`camera-${camera.id}`}
                      checked={isCameraEnabled(camera.id)}
                      onCheckedChange={(checked) => handleCameraToggle(camera.id, !!checked)}
                      disabled={saving}
                    />
                    <Label htmlFor={`camera-${camera.id}`} className="text-sm cursor-pointer">
                      {camera.name}
                    </Label>
                  </div>
                  {camera.source_type && (
                    <span className="text-xs text-muted-foreground capitalize">
                      {camera.source_type}
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Object Type Filters */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-muted-foreground" />
            <Label className="text-sm font-medium">Detection Types</Label>
          </div>
          <p className="text-xs text-muted-foreground">
            Select which detection types trigger notifications
          </p>
          <div className="grid grid-cols-2 gap-2 rounded-lg border p-3">
            {OBJECT_TYPES.map((type) => {
              const Icon = ObjectTypeIcons[type.value] || User;
              return (
                <div key={type.value} className="flex items-center gap-2">
                  <Checkbox
                    id={`type-${type.value}`}
                    checked={isObjectTypeEnabled(type.value)}
                    onCheckedChange={(checked) => handleObjectTypeToggle(type.value, !!checked)}
                    disabled={saving}
                  />
                  <Label htmlFor={`type-${type.value}`} className="flex items-center gap-1.5 text-sm cursor-pointer">
                    <Icon className="h-4 w-4" />
                    {type.label}
                  </Label>
                </div>
              );
            })}
          </div>
        </div>

        {/* Quiet Hours */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <Label className="text-sm font-medium">Quiet Hours</Label>
            </div>
            <Switch
              checked={preferences.quiet_hours_enabled}
              onCheckedChange={handleQuietHoursToggle}
              disabled={saving}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Pause notifications during specified hours
          </p>
          {preferences.quiet_hours_enabled && (
            <div className="space-y-3 rounded-lg border p-3">
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <Label htmlFor="quiet-start" className="text-xs text-muted-foreground">
                    Start
                  </Label>
                  <Input
                    id="quiet-start"
                    type="time"
                    value={quietHoursStart}
                    onChange={(e) => handleQuietHoursTimeChange(e.target.value, quietHoursEnd)}
                    className="mt-1"
                    disabled={saving}
                  />
                </div>
                <div className="flex-1">
                  <Label htmlFor="quiet-end" className="text-xs text-muted-foreground">
                    End
                  </Label>
                  <Input
                    id="quiet-end"
                    type="time"
                    value={quietHoursEnd}
                    onChange={(e) => handleQuietHoursTimeChange(quietHoursStart, e.target.value)}
                    className="mt-1"
                    disabled={saving}
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="timezone" className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Globe className="h-3 w-3" />
                  Timezone
                </Label>
                <Select
                  value={preferences.timezone}
                  onValueChange={handleTimezoneChange}
                  disabled={saving}
                >
                  <SelectTrigger id="timezone" className="mt-1">
                    <SelectValue placeholder="Select timezone" />
                  </SelectTrigger>
                  <SelectContent>
                    {COMMON_TIMEZONES.map((tz) => (
                      <SelectItem key={tz.value} value={tz.value}>
                        {tz.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
        </div>

        {/* Sound Toggle */}
        <div className="flex items-center justify-between rounded-lg border p-3">
          <div className="flex items-center gap-2">
            {preferences.sound_enabled ? (
              <Volume2 className="h-4 w-4 text-muted-foreground" />
            ) : (
              <VolumeX className="h-4 w-4 text-muted-foreground" />
            )}
            <div>
              <Label className="text-sm font-medium">Notification Sound</Label>
              <p className="text-xs text-muted-foreground">
                Play a sound when notifications arrive
              </p>
            </div>
          </div>
          <Switch
            checked={preferences.sound_enabled}
            onCheckedChange={handleSoundToggle}
            disabled={saving}
          />
        </div>

        {/* Saving indicator */}
        {saving && (
          <div className="flex items-center justify-center text-sm text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Saving...
          </div>
        )}

        {/* Error display */}
        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}
      </CardContent>
    </Card>
  );
}
