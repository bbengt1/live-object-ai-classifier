/**
 * Frame Sampling Strategy Selector Component
 * Story P8-2.5: Radio button group for selecting frame sampling strategy
 */

'use client';

import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';

export type FrameSamplingStrategy = 'uniform' | 'adaptive' | 'hybrid';

interface FrameSamplingStrategySelectorProps {
  value: FrameSamplingStrategy;
  onChange: (value: FrameSamplingStrategy) => void;
  disabled?: boolean;
}

interface StrategyOption {
  value: FrameSamplingStrategy;
  label: string;
  description: string;
  recommended: string;
}

const STRATEGY_OPTIONS: StrategyOption[] = [
  {
    value: 'uniform',
    label: 'Uniform',
    description: 'Fixed interval extraction. Predictable, consistent frames.',
    recommended: 'Best for static cameras or scenes with steady activity.',
  },
  {
    value: 'adaptive',
    label: 'Adaptive',
    description: 'Content-aware selection. Skips redundant frames, captures key moments.',
    recommended: 'Best for busy areas with varying activity levels.',
  },
  {
    value: 'hybrid',
    label: 'Hybrid',
    description: 'Extracts extra candidates then filters adaptively. Balanced approach.',
    recommended: 'Best for varied content where you want the best of both.',
  },
];

export function FrameSamplingStrategySelector({
  value,
  onChange,
  disabled = false,
}: FrameSamplingStrategySelectorProps) {
  return (
    <div className="space-y-3">
      <Label>Frame Sampling Strategy</Label>
      <RadioGroup
        value={value}
        onValueChange={(val) => onChange(val as FrameSamplingStrategy)}
        disabled={disabled}
        className="space-y-3"
      >
        {STRATEGY_OPTIONS.map((option) => (
          <label
            key={option.value}
            className={`flex items-start gap-3 cursor-pointer p-3 rounded-lg border hover:bg-accent ${
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            } ${value === option.value ? 'border-primary bg-accent/50' : ''}`}
          >
            <RadioGroupItem
              value={option.value}
              id={`strategy-${option.value}`}
              className="mt-0.5"
              disabled={disabled}
            />
            <div className="flex-1">
              <div className="font-medium text-sm">{option.label}</div>
              <div className="text-xs text-muted-foreground mt-1">
                {option.description}
              </div>
              <div className="text-xs text-muted-foreground/80 mt-0.5 italic">
                {option.recommended}
              </div>
            </div>
          </label>
        ))}
      </RadioGroup>
      <p className="text-xs text-muted-foreground">
        Controls how frames are selected from video clips for AI analysis.
        Adaptive and hybrid may improve accuracy by focusing on key moments.
      </p>
    </div>
  );
}
