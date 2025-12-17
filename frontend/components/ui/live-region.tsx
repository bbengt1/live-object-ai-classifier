/**
 * LiveRegion Component (Story P6-2.2)
 *
 * Provides accessible live regions for dynamic content announcements.
 * Uses aria-live to announce content changes to screen readers.
 *
 * Usage:
 * - polite: Non-urgent updates (default) - waits for user pause
 * - assertive: Urgent updates - interrupts immediately
 *
 * @example
 * <LiveRegion>Loading complete</LiveRegion>
 * <LiveRegion mode="assertive">Error occurred</LiveRegion>
 * <LiveRegion visuallyHidden>5 new events loaded</LiveRegion>
 */

'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface LiveRegionProps {
  /** Content to announce */
  children: React.ReactNode;
  /** Announcement priority: polite waits, assertive interrupts */
  mode?: 'polite' | 'assertive';
  /** Role for the region: status (default) or alert */
  role?: 'status' | 'alert';
  /** Hide content visually but keep accessible to screen readers */
  visuallyHidden?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Delay before announcing (ms) - helps prevent rapid updates */
  delay?: number;
}

/**
 * Accessible live region for screen reader announcements
 */
export function LiveRegion({
  children,
  mode = 'polite',
  role = 'status',
  visuallyHidden = false,
  className,
  delay = 0,
}: LiveRegionProps) {
  const [announcement, setAnnouncement] = React.useState<React.ReactNode>(children);
  const timeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  React.useEffect(() => {
    if (delay > 0) {
      // Clear any pending update
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      // Delay the announcement
      timeoutRef.current = setTimeout(() => {
        setAnnouncement(children);
      }, delay);
    } else {
      setAnnouncement(children);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [children, delay]);

  return (
    <div
      role={role}
      aria-live={mode}
      aria-atomic="true"
      className={cn(
        visuallyHidden && 'sr-only',
        className
      )}
    >
      {announcement}
    </div>
  );
}

/**
 * Visually hidden but accessible status announcer
 * Use for loading states, counts, and other dynamic updates
 */
export function StatusAnnouncer({
  children,
  delay = 100,
}: {
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <LiveRegion
      mode="polite"
      role="status"
      visuallyHidden
      delay={delay}
    >
      {children}
    </LiveRegion>
  );
}

export default LiveRegion;
