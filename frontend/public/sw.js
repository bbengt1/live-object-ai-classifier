/**
 * Service Worker for Push Notifications (Story P4-1.3)
 *
 * Handles:
 * - Push events: Display rich notifications with thumbnails, actions, and deep links
 * - Notification click: Navigate to event details or handle actions
 * - Notification close: Optional analytics tracking
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API
 */

// Service worker version for cache busting
const SW_VERSION = '1.0.0';

/**
 * Handle incoming push notifications
 * Displays rich notification with thumbnail, actions, and deep link data
 */
self.addEventListener('push', (event) => {
  console.log('[SW] Push event received');

  // Default notification options if payload parsing fails
  const defaultOptions = {
    title: 'Live Object AI',
    body: 'New event detected',
    icon: '/icons/notification-192.svg',
    badge: '/icons/badge-72.svg',
  };

  let notificationData = defaultOptions;

  try {
    if (event.data) {
      const payload = event.data.json();
      console.log('[SW] Push payload:', payload);
      notificationData = payload;
    }
  } catch (err) {
    console.error('[SW] Error parsing push data:', err);
    // Fall back to text if JSON parsing fails
    try {
      notificationData.body = event.data?.text() || defaultOptions.body;
    } catch {
      // Use default
    }
  }

  const { title, ...options } = notificationData;

  // Build notification options
  const notificationOptions = {
    body: options.body || '',
    icon: options.icon || '/icons/notification-192.svg',
    badge: options.badge || '/icons/badge-72.svg',
    // Image: Large thumbnail (displayed below body in supported browsers)
    ...(options.image && { image: options.image }),
    // Tag: Used for notification collapse/replacement
    ...(options.tag && { tag: options.tag }),
    // Renotify: Alert again even if same tag (for updates)
    renotify: options.renotify ?? true,
    // Require interaction: Keep notification visible until user interacts
    requireInteraction: options.requireInteraction ?? false,
    // Actions: Buttons displayed on notification
    actions: options.actions || [
      { action: 'view', title: 'View', icon: '/icons/view-24.svg' },
      { action: 'dismiss', title: 'Dismiss', icon: '/icons/dismiss-24.svg' },
    ],
    // Data: Custom data passed to click handler (event_id, url, etc.)
    data: options.data || {},
    // Silent: Don't vibrate/sound (false by default)
    silent: options.silent ?? false,
    // Timestamp: When the event occurred
    ...(options.timestamp && { timestamp: options.timestamp }),
  };

  console.log('[SW] Showing notification:', title, notificationOptions);

  event.waitUntil(
    self.registration.showNotification(title || 'Live Object AI', notificationOptions)
  );
});

/**
 * Handle notification click events
 * Opens the app and navigates to the event details page
 */
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification click:', event.action, event.notification.data);

  // Always close the notification
  event.notification.close();

  // Handle dismiss action - just close, no navigation
  if (event.action === 'dismiss') {
    console.log('[SW] Notification dismissed by user');
    // Could track dismissal analytics here if needed
    return;
  }

  // For 'view' action or body click, navigate to the URL
  const url = event.notification.data?.url || '/';
  const fullUrl = new URL(url, self.location.origin).href;

  console.log('[SW] Opening URL:', fullUrl);

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Check if app is already open in a tab
      for (const client of clientList) {
        // Check if this is our app (same origin)
        if (client.url.startsWith(self.location.origin)) {
          console.log('[SW] Found existing client, navigating and focusing');
          // Navigate to the event URL
          client.navigate(fullUrl);
          // Focus the tab
          return client.focus();
        }
      }

      // No existing tab found, open a new one
      console.log('[SW] No existing client, opening new window');
      return clients.openWindow(fullUrl);
    })
  );
});

/**
 * Handle notification close events (user dismissed without clicking)
 * Useful for analytics tracking
 */
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification closed:', event.notification.data);
  // Could track close analytics here if needed
  // For example, send to analytics endpoint
});

/**
 * Service worker install event
 * Called when a new service worker is first installed
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Service worker installing, version:', SW_VERSION);
  // Skip waiting to activate immediately
  self.skipWaiting();
});

/**
 * Service worker activate event
 * Called when the service worker becomes active
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Service worker activating, version:', SW_VERSION);
  // Take control of all clients immediately
  event.waitUntil(clients.claim());
});

/**
 * Handle messages from the main app
 * Can be used for communication between app and service worker
 */
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  if (event.data?.type === 'GET_VERSION') {
    event.ports[0]?.postMessage({ version: SW_VERSION });
  }
});
