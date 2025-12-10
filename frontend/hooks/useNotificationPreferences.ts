/**
 * Custom hook for managing notification preferences (Story P4-1.4)
 *
 * Fetches and updates notification preferences for the current push subscription.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient, ApiError } from '@/lib/api-client';
import type { INotificationPreferences, IUpdatePreferencesRequest } from '@/types/push';

interface UseNotificationPreferencesOptions {
  /**
   * Push subscription endpoint URL (required to identify subscription)
   */
  endpoint: string | null;
  /**
   * Whether to fetch automatically when endpoint is available
   */
  autoFetch?: boolean;
}

interface UseNotificationPreferencesReturn {
  /**
   * Current notification preferences
   */
  preferences: INotificationPreferences | null;
  /**
   * Loading state
   */
  loading: boolean;
  /**
   * Saving state (during update)
   */
  saving: boolean;
  /**
   * Error message if fetch/update failed
   */
  error: string | null;
  /**
   * Refresh preferences from server
   */
  refresh: () => Promise<void>;
  /**
   * Update preferences on server
   */
  updatePreferences: (updates: Partial<Omit<IUpdatePreferencesRequest, 'endpoint'>>) => Promise<boolean>;
}

/**
 * Hook to fetch and manage notification preferences
 * @param options Configuration options (endpoint, autoFetch)
 * @returns Preferences state, loading/error states, and update function
 */
export function useNotificationPreferences(
  options: UseNotificationPreferencesOptions
): UseNotificationPreferencesReturn {
  const { endpoint, autoFetch = true } = options;

  const [preferences, setPreferences] = useState<INotificationPreferences | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPreferences = useCallback(async () => {
    if (!endpoint) {
      setPreferences(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.push.getPreferences(endpoint);
      setPreferences(data);
    } catch (err) {
      console.error('Failed to fetch notification preferences:', err);
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load notification preferences');
      }
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  // Auto-fetch when endpoint becomes available
  useEffect(() => {
    if (autoFetch && endpoint) {
      fetchPreferences();
    }
  }, [autoFetch, endpoint, fetchPreferences]);

  const updatePreferences = useCallback(async (
    updates: Partial<Omit<IUpdatePreferencesRequest, 'endpoint'>>
  ): Promise<boolean> => {
    if (!endpoint || !preferences) {
      setError('No subscription endpoint available');
      return false;
    }

    setSaving(true);
    setError(null);

    try {
      // Merge current preferences with updates
      const updateRequest: IUpdatePreferencesRequest = {
        endpoint,
        enabled_cameras: updates.enabled_cameras !== undefined
          ? updates.enabled_cameras
          : preferences.enabled_cameras,
        enabled_object_types: updates.enabled_object_types !== undefined
          ? updates.enabled_object_types
          : preferences.enabled_object_types,
        quiet_hours_enabled: updates.quiet_hours_enabled !== undefined
          ? updates.quiet_hours_enabled
          : preferences.quiet_hours_enabled,
        quiet_hours_start: updates.quiet_hours_start !== undefined
          ? updates.quiet_hours_start
          : preferences.quiet_hours_start,
        quiet_hours_end: updates.quiet_hours_end !== undefined
          ? updates.quiet_hours_end
          : preferences.quiet_hours_end,
        timezone: updates.timezone !== undefined
          ? updates.timezone
          : preferences.timezone,
        sound_enabled: updates.sound_enabled !== undefined
          ? updates.sound_enabled
          : preferences.sound_enabled,
      };

      const data = await apiClient.push.updatePreferences(updateRequest);
      setPreferences(data);
      return true;
    } catch (err) {
      console.error('Failed to update notification preferences:', err);
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to save notification preferences');
      }
      return false;
    } finally {
      setSaving(false);
    }
  }, [endpoint, preferences]);

  return {
    preferences,
    loading,
    saving,
    error,
    refresh: fetchPreferences,
    updatePreferences,
  };
}
