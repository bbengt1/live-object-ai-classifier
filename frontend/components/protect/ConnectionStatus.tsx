/**
 * Connection Status Indicator Component
 * Story P2-1.3: Controller Configuration UI
 *
 * Displays connection status with visual indicators:
 * - Gray dot: Not configured
 * - Yellow dot + spinner: Connecting
 * - Green dot: Connected
 * - Red dot + tooltip: Connection error
 */

'use client';

import { Loader2 } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export type ConnectionStatusType = 'not_configured' | 'connecting' | 'connected' | 'error';

interface ConnectionStatusProps {
  status: ConnectionStatusType;
  errorMessage?: string;
  firmwareVersion?: string;
  cameraCount?: number;
}

const statusConfig = {
  not_configured: {
    dotColor: 'bg-gray-400',
    textColor: 'text-gray-500',
    label: 'Not configured',
  },
  connecting: {
    dotColor: 'bg-yellow-500',
    textColor: 'text-yellow-600',
    label: 'Connecting...',
  },
  connected: {
    dotColor: 'bg-green-500',
    textColor: 'text-green-600',
    label: 'Connected',
  },
  error: {
    dotColor: 'bg-red-500',
    textColor: 'text-red-600',
    label: 'Connection Error',
  },
};

export function ConnectionStatus({
  status,
  errorMessage,
  firmwareVersion,
  cameraCount,
}: ConnectionStatusProps) {
  const config = statusConfig[status];

  const StatusContent = (
    <div className="flex items-center gap-2">
      {/* Status Dot */}
      <div className="relative flex items-center justify-center">
        <span
          className={`h-3 w-3 rounded-full ${config.dotColor}`}
          aria-hidden="true"
        />
        {status === 'connecting' && (
          <Loader2 className="absolute h-5 w-5 animate-spin text-yellow-500" />
        )}
      </div>

      {/* Status Text */}
      <div className="flex flex-col">
        <span className={`text-sm font-medium ${config.textColor}`}>
          {config.label}
        </span>
        {status === 'connected' && firmwareVersion && (
          <span className="text-xs text-muted-foreground">
            Firmware: {firmwareVersion}
            {cameraCount !== undefined && ` • ${cameraCount} camera${cameraCount !== 1 ? 's' : ''}`}
          </span>
        )}
      </div>
    </div>
  );

  // ARIA live region for accessibility - announces status changes
  const AriaLiveRegion = (
    <span className="sr-only" role="status" aria-live="polite">
      {status === 'not_configured' && 'Controller not configured'}
      {status === 'connecting' && 'Connecting to controller'}
      {status === 'connected' && `Connected to controller${firmwareVersion ? `, firmware version ${firmwareVersion}` : ''}`}
      {status === 'error' && `Connection error: ${errorMessage || 'Unknown error'}`}
    </span>
  );

  // Wrap error status in tooltip to show error details
  if (status === 'error' && errorMessage) {
    return (
      <>
        {AriaLiveRegion}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="cursor-help">{StatusContent}</div>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs">
            <p className="text-sm">{errorMessage}</p>
          </TooltipContent>
        </Tooltip>
      </>
    );
  }

  return (
    <>
      {AriaLiveRegion}
      {StatusContent}
    </>
  );
}
