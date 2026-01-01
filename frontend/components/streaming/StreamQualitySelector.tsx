/**
 * StreamQualitySelector Component (Story P16-2.3)
 * Provides quality selection dropdown for live stream player
 * Uses shadcn/ui Popover with quality level options
 */

'use client';

import { useState } from 'react';
import { Settings2, Check, WifiLow, Wifi, Signal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import type { StreamQuality, IStreamQualityOption } from '@/types/camera';
import { cn } from '@/lib/utils';

interface StreamQualitySelectorProps {
  /**
   * Current quality level
   */
  currentQuality: StreamQuality;
  /**
   * Available quality options from stream info (optional)
   */
  qualityOptions?: IStreamQualityOption[];
  /**
   * Callback when quality changes
   */
  onQualityChange: (quality: StreamQuality) => void;
}

/**
 * Default quality options if not provided by API
 */
const DEFAULT_QUALITY_OPTIONS: IStreamQualityOption[] = [
  { id: 'low', label: 'Low', resolution: '640x360', fps: 5 },
  { id: 'medium', label: 'Medium', resolution: '1280x720', fps: 10 },
  { id: 'high', label: 'High', resolution: '1920x1080', fps: 15 },
];

/**
 * Quality configuration for display
 */
const QUALITY_CONFIG: Record<StreamQuality, {
  icon: typeof WifiLow;
  color: string;
  description: string;
}> = {
  low: {
    icon: WifiLow,
    color: 'text-gray-400',
    description: 'Lower bandwidth, suitable for slow connections',
  },
  medium: {
    icon: Wifi,
    color: 'text-blue-400',
    description: 'Balanced quality and bandwidth',
  },
  high: {
    icon: Signal,
    color: 'text-green-400',
    description: 'Best quality, requires fast connection',
  },
};

/**
 * StreamQualitySelector - Popover dropdown for quality selection
 */
export function StreamQualitySelector({
  currentQuality,
  qualityOptions,
  onQualityChange,
}: StreamQualitySelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const options = qualityOptions || DEFAULT_QUALITY_OPTIONS;
  const currentConfig = QUALITY_CONFIG[currentQuality];
  const CurrentIcon = currentConfig.icon;

  const handleSelect = (quality: StreamQuality) => {
    onQualityChange(quality);
    setIsOpen(false);
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 px-2 text-white hover:bg-white/20 gap-1"
          title="Stream quality"
        >
          <CurrentIcon className={cn('h-4 w-4', currentConfig.color)} />
          <span className="text-xs capitalize">{currentQuality}</span>
          <Settings2 className="h-3 w-3 opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-64 p-2"
        align="start"
        side="top"
        sideOffset={8}
      >
        <div className="space-y-1">
          <div className="px-2 py-1.5 text-sm font-medium text-muted-foreground">
            Stream Quality
          </div>
          {options.map((option) => {
            const config = QUALITY_CONFIG[option.id];
            const Icon = config.icon;
            const isSelected = option.id === currentQuality;

            return (
              <button
                key={option.id}
                onClick={() => handleSelect(option.id)}
                className={cn(
                  'w-full flex items-center gap-3 px-2 py-2 rounded-md text-left transition-colors',
                  isSelected
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-muted'
                )}
              >
                <Icon className={cn('h-4 w-4 shrink-0', config.color)} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{option.label}</span>
                    <span className="text-xs text-muted-foreground">
                      {option.resolution}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {option.fps} FPS
                  </div>
                </div>
                {isSelected && (
                  <Check className="h-4 w-4 shrink-0 text-primary" />
                )}
              </button>
            );
          })}
          <div className="px-2 pt-2 text-xs text-muted-foreground border-t mt-2">
            {currentConfig.description}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
