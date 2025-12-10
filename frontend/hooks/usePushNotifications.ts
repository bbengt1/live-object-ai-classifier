/**
 * Push Notifications Hook (Story P4-1.2)
 *
 * Custom hook for managing Web Push notification subscriptions.
 * Handles:
 * - Permission state management
 * - Push subscription lifecycle
 * - VAPID key fetching
 * - Browser API interactions
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient, ApiError } from '@/lib/api-client';
import type { PushNotificationStatus } from '@/types/push';

interface UsePushNotificationsReturn {
  /**
   * Current status of push notifications
   */
  status: PushNotificationStatus;
  /**
   * Whether push notifications are currently subscribed
   */
  isSubscribed: boolean;
  /**
   * Current notification permission state
   */
  permission: NotificationPermission | 'unsupported';
  /**
   * Error message if something went wrong
   */
  error: string | null;
  /**
   * Whether an operation is in progress
   */
  isLoading: boolean;
  /**
   * Device/browser info for display
   */
  deviceInfo: string | null;
  /**
   * Subscription endpoint (truncated) for display
   */
  subscriptionEndpoint: string | null;
  /**
   * Request notification permission and subscribe
   */
  subscribe: () => Promise<boolean>;
  /**
   * Unsubscribe from push notifications
   */
  unsubscribe: () => Promise<boolean>;
  /**
   * Send a test notification
   */
  sendTestNotification: () => Promise<boolean>;
  /**
   * Check if Push API is supported
   */
  isPushSupported: boolean;
  /**
   * Check if service worker is registered
   */
  hasServiceWorker: boolean;
}

/**
 * Convert URL-safe base64 string to Uint8Array for applicationServerKey
 */
function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray.buffer;
}

/**
 * Get browser/device info for display
 */
function getDeviceInfo(): string {
  const ua = navigator.userAgent;

  // Detect browser
  let browser = 'Unknown Browser';
  if (ua.includes('Firefox')) {
    browser = 'Firefox';
  } else if (ua.includes('Edg/')) {
    browser = 'Edge';
  } else if (ua.includes('Chrome')) {
    browser = 'Chrome';
  } else if (ua.includes('Safari')) {
    browser = 'Safari';
  }

  // Detect platform
  let platform = 'Unknown';
  if (ua.includes('Windows')) {
    platform = 'Windows';
  } else if (ua.includes('Mac')) {
    platform = 'macOS';
  } else if (ua.includes('Linux')) {
    platform = 'Linux';
  } else if (ua.includes('iPhone') || ua.includes('iPad')) {
    platform = 'iOS';
  } else if (ua.includes('Android')) {
    platform = 'Android';
  }

  return `${browser} on ${platform}`;
}

/**
 * Hook for managing push notification subscriptions
 */
export function usePushNotifications(): UsePushNotificationsReturn {
  const [status, setStatus] = useState<PushNotificationStatus>('loading');
  const [permission, setPermission] = useState<NotificationPermission | 'unsupported'>('default');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [deviceInfo, setDeviceInfo] = useState<string | null>(null);
  const [subscriptionEndpoint, setSubscriptionEndpoint] = useState<string | null>(null);
  const [currentSubscription, setCurrentSubscription] = useState<PushSubscription | null>(null);

  // Check browser support
  const isPushSupported = typeof window !== 'undefined' &&
    'Notification' in window &&
    'serviceWorker' in navigator &&
    'PushManager' in window;

  const hasServiceWorker = typeof navigator !== 'undefined' &&
    'serviceWorker' in navigator;

  /**
   * Initialize and check current state
   */
  const checkStatus = useCallback(async () => {
    // Check if push is supported
    if (!isPushSupported) {
      setStatus('unsupported');
      setPermission('unsupported');
      return;
    }

    // Check notification permission
    const currentPermission = Notification.permission;
    setPermission(currentPermission);

    if (currentPermission === 'denied') {
      setStatus('permission-denied');
      return;
    }

    // Check if service worker is registered
    try {
      const registration = await navigator.serviceWorker.ready;

      // Check for existing subscription
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        setCurrentSubscription(subscription);
        setSubscriptionEndpoint(subscription.endpoint);
        setDeviceInfo(getDeviceInfo());
        setStatus('subscribed');
      } else {
        setStatus('unsubscribed');
      }
    } catch (err) {
      // Service worker not registered yet - that's OK for now (P4-1.5 will add it)
      console.warn('Service worker not ready:', err);
      setStatus('no-service-worker');
    }
  }, [isPushSupported]);

  // Run initial check
  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  /**
   * Request permission and subscribe to push notifications
   */
  const subscribe = useCallback(async (): Promise<boolean> => {
    if (!isPushSupported) {
      setError('Push notifications are not supported in this browser');
      return false;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Request notification permission if not granted
      if (Notification.permission !== 'granted') {
        const result = await Notification.requestPermission();
        setPermission(result);

        if (result === 'denied') {
          setStatus('permission-denied');
          setError('Notification permission was denied. Please enable notifications in your browser settings.');
          return false;
        }

        if (result !== 'granted') {
          setError('Notification permission was not granted');
          return false;
        }
      }

      // Get service worker registration
      let registration: ServiceWorkerRegistration;
      try {
        registration = await navigator.serviceWorker.ready;
      } catch {
        setStatus('no-service-worker');
        setError('Service worker is not registered. Push notifications require a service worker.');
        return false;
      }

      // Get VAPID public key from backend
      const { public_key: vapidPublicKey } = await apiClient.push.getVapidPublicKey();

      // Subscribe to push
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
      });

      // Extract keys from subscription
      const subscriptionJson = subscription.toJSON();
      if (!subscriptionJson.keys) {
        throw new Error('Failed to get subscription keys');
      }

      // Send subscription to backend
      await apiClient.push.subscribe({
        endpoint: subscription.endpoint,
        keys: {
          p256dh: subscriptionJson.keys.p256dh!,
          auth: subscriptionJson.keys.auth!,
        },
        user_agent: navigator.userAgent,
      });

      // Update state
      setCurrentSubscription(subscription);
      setSubscriptionEndpoint(subscription.endpoint);
      setDeviceInfo(getDeviceInfo());
      setStatus('subscribed');

      return true;
    } catch (err) {
      console.error('Error subscribing to push:', err);

      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to subscribe to push notifications');
      }

      setStatus('error');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [isPushSupported]);

  /**
   * Unsubscribe from push notifications
   */
  const unsubscribe = useCallback(async (): Promise<boolean> => {
    setIsLoading(true);
    setError(null);

    try {
      if (currentSubscription) {
        // Unsubscribe from browser
        await currentSubscription.unsubscribe();

        // Remove from backend
        try {
          await apiClient.push.unsubscribe(currentSubscription.endpoint);
        } catch (err) {
          // Ignore 404 errors - subscription may already be removed
          if (err instanceof ApiError && err.statusCode !== 404) {
            throw err;
          }
        }
      }

      // Update state
      setCurrentSubscription(null);
      setSubscriptionEndpoint(null);
      setDeviceInfo(null);
      setStatus('unsubscribed');

      return true;
    } catch (err) {
      console.error('Error unsubscribing from push:', err);

      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to unsubscribe from push notifications');
      }

      return false;
    } finally {
      setIsLoading(false);
    }
  }, [currentSubscription]);

  /**
   * Send a test notification
   */
  const sendTestNotification = useCallback(async (): Promise<boolean> => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await apiClient.push.sendTest();

      if (!result.success && result.results?.length === 0) {
        setError('No subscriptions found. Enable notifications first.');
        return false;
      }

      return result.success;
    } catch (err) {
      console.error('Error sending test notification:', err);

      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to send test notification');
      }

      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    status,
    isSubscribed: status === 'subscribed',
    permission,
    error,
    isLoading,
    deviceInfo,
    subscriptionEndpoint,
    subscribe,
    unsubscribe,
    sendTestNotification,
    isPushSupported,
    hasServiceWorker,
  };
}
