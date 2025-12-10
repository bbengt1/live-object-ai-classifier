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
