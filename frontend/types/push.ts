/**
 * Push Notification Types (Story P4-1.2)
 *
 * Types for Web Push subscription management API
 */

/**
 * Response from GET /api/v1/push/vapid-public-key
 */
export interface IVapidPublicKeyResponse {
  public_key: string;
}

/**
 * Browser push subscription keys
 */
export interface IPushSubscriptionKeys {
  p256dh: string;
  auth: string;
}

/**
 * Request body for POST /api/v1/push/subscribe
 */
export interface IPushSubscribeRequest {
  endpoint: string;
  keys: IPushSubscriptionKeys;
  user_agent?: string;
}

/**
 * Response from POST /api/v1/push/subscribe
 */
export interface IPushSubscriptionResponse {
  id: string;
  endpoint: string;
  created_at: string;
}

/**
 * Request body for DELETE /api/v1/push/subscribe
 */
export interface IPushUnsubscribeRequest {
  endpoint: string;
}

/**
 * Single subscription item in list response
 */
export interface IPushSubscriptionListItem {
  id: string;
  user_id: string | null;
  endpoint: string;
  user_agent: string | null;
  created_at: string | null;
  last_used_at: string | null;
}

/**
 * Response from GET /api/v1/push/subscriptions
 */
export interface IPushSubscriptionsListResponse {
  subscriptions: IPushSubscriptionListItem[];
  total: number;
}

/**
 * Response from POST /api/v1/push/test
 */
export interface IPushTestResponse {
  success: boolean;
  message: string;
  results?: Array<{
    subscription_id: string;
    success: boolean;
    error?: string;
  }>;
}

/**
 * Permission state for Notification API
 */
export type NotificationPermissionState = 'granted' | 'denied' | 'default';

/**
 * Push notification status for UI
 */
export type PushNotificationStatus =
  | 'loading'
  | 'unsupported'
  | 'no-service-worker'
  | 'permission-denied'
  | 'subscribed'
  | 'unsubscribed'
  | 'error';

/**
 * Notification preferences for a push subscription (Story P4-1.4)
 */
export interface INotificationPreferences {
  id: string;
  subscription_id: string;
  enabled_cameras: string[] | null;  // null = all cameras
  enabled_object_types: string[] | null;  // null = all types
  quiet_hours_enabled: boolean;
  quiet_hours_start: string | null;  // "HH:MM"
  quiet_hours_end: string | null;    // "HH:MM"
  timezone: string;
  sound_enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * Request body for POST /api/v1/push/preferences (get preferences)
 */
export interface IGetPreferencesRequest {
  endpoint: string;
}

/**
 * Request body for PUT /api/v1/push/preferences (update preferences)
 */
export interface IUpdatePreferencesRequest {
  endpoint: string;
  enabled_cameras?: string[] | null;
  enabled_object_types?: string[] | null;
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  timezone: string;
  sound_enabled: boolean;
}

/**
 * Valid object types for filtering
 */
export const OBJECT_TYPES = [
  { value: 'person', label: 'Person' },
  { value: 'vehicle', label: 'Vehicle' },
  { value: 'package', label: 'Package' },
  { value: 'animal', label: 'Animal' },
] as const;

/**
 * Common timezones for dropdown
 */
export const COMMON_TIMEZONES = [
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'Eastern Time (US)' },
  { value: 'America/Chicago', label: 'Central Time (US)' },
  { value: 'America/Denver', label: 'Mountain Time (US)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (US)' },
  { value: 'America/Phoenix', label: 'Arizona' },
  { value: 'America/Anchorage', label: 'Alaska' },
  { value: 'Pacific/Honolulu', label: 'Hawaii' },
  { value: 'Europe/London', label: 'London (UK)' },
  { value: 'Europe/Paris', label: 'Paris (CET)' },
  { value: 'Europe/Berlin', label: 'Berlin (CET)' },
  { value: 'Asia/Tokyo', label: 'Tokyo' },
  { value: 'Asia/Shanghai', label: 'Shanghai' },
  { value: 'Asia/Singapore', label: 'Singapore' },
  { value: 'Australia/Sydney', label: 'Sydney' },
] as const;
