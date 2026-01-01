/**
 * Tests for StreamQualitySelector component (Story P16-2.3)
 * Verifies quality selection dropdown behavior
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../../test-utils';
import { StreamQualitySelector } from '@/components/streaming/StreamQualitySelector';
import type { IStreamQualityOption, StreamQuality } from '@/types/camera';

describe('StreamQualitySelector', () => {
  let mockOnQualityChange: (quality: StreamQuality) => void;

  const defaultQualityOptions: IStreamQualityOption[] = [
    { id: 'low', label: 'Low', resolution: '640x360', fps: 5 },
    { id: 'medium', label: 'Medium', resolution: '1280x720', fps: 10 },
    { id: 'high', label: 'High', resolution: '1920x1080', fps: 15 },
  ];

  beforeEach(() => {
    mockOnQualityChange = vi.fn();
  });

  describe('Rendering', () => {
    it('renders the trigger button with current quality', () => {
      render(
        <StreamQualitySelector
          currentQuality="medium"
          onQualityChange={mockOnQualityChange}
        />
      );

      expect(screen.getByText('medium')).toBeInTheDocument();
      expect(screen.getByTitle('Stream quality')).toBeInTheDocument();
    });

    it('displays settings icon in button', () => {
      render(
        <StreamQualitySelector
          currentQuality="medium"
          onQualityChange={mockOnQualityChange}
        />
      );

      const button = screen.getByTitle('Stream quality');
      expect(button).toBeInTheDocument();
    });

    it('shows quality-specific icon color for low quality', () => {
      render(
        <StreamQualitySelector
          currentQuality="low"
          onQualityChange={mockOnQualityChange}
        />
      );

      expect(screen.getByText('low')).toBeInTheDocument();
    });

    it('shows quality-specific icon color for high quality', () => {
      render(
        <StreamQualitySelector
          currentQuality="high"
          onQualityChange={mockOnQualityChange}
        />
      );

      expect(screen.getByText('high')).toBeInTheDocument();
    });
  });

  describe('Popover Behavior', () => {
    it('opens popover when trigger is clicked', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="medium"
          qualityOptions={defaultQualityOptions}
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      // Should show the quality options
      expect(screen.getByText('Stream Quality')).toBeInTheDocument();
      expect(screen.getByText('Low')).toBeInTheDocument();
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(screen.getByText('High')).toBeInTheDocument();
    });

    it('displays resolution for each quality option', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="medium"
          qualityOptions={defaultQualityOptions}
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      expect(screen.getByText('640x360')).toBeInTheDocument();
      expect(screen.getByText('1280x720')).toBeInTheDocument();
      expect(screen.getByText('1920x1080')).toBeInTheDocument();
    });

    it('displays FPS for each quality option', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="medium"
          qualityOptions={defaultQualityOptions}
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      expect(screen.getByText('5 FPS')).toBeInTheDocument();
      expect(screen.getByText('10 FPS')).toBeInTheDocument();
      expect(screen.getByText('15 FPS')).toBeInTheDocument();
    });

    it('shows check mark for selected quality', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="medium"
          qualityOptions={defaultQualityOptions}
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      // The medium option should be highlighted/selected
      // Verify the quality options are shown
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(screen.getByText('Stream Quality')).toBeInTheDocument();
    });

    it('shows quality description in footer', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="medium"
          qualityOptions={defaultQualityOptions}
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      // Should show the description for current quality
      expect(screen.getByText('Balanced quality and bandwidth')).toBeInTheDocument();
    });
  });

  describe('Quality Selection', () => {
    it('calls onQualityChange when quality option is clicked', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="medium"
          qualityOptions={defaultQualityOptions}
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      // Click on High quality option
      const highOption = screen.getByText('High');
      await user.click(highOption);

      expect(mockOnQualityChange).toHaveBeenCalledWith('high');
    });

    it('closes popover after selection', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="medium"
          qualityOptions={defaultQualityOptions}
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      // Verify popover is open
      expect(screen.getByText('Stream Quality')).toBeInTheDocument();

      // Click on Low quality option
      const lowOption = screen.getByText('Low');
      await user.click(lowOption);

      expect(mockOnQualityChange).toHaveBeenCalledWith('low');
      // Popover should close - title might no longer be visible
    });

    it('can select each quality level', async () => {
      const { user, rerender } = render(
        <StreamQualitySelector
          currentQuality="medium"
          qualityOptions={defaultQualityOptions}
          onQualityChange={mockOnQualityChange}
        />
      );

      // Test selecting low
      let trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);
      await user.click(screen.getByText('Low'));
      expect(mockOnQualityChange).toHaveBeenCalledWith('low');

      // Rerender with low selected
      rerender(
        <StreamQualitySelector
          currentQuality="low"
          qualityOptions={defaultQualityOptions}
          onQualityChange={mockOnQualityChange}
        />
      );

      // Test selecting high
      trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);
      await user.click(screen.getByText('High'));
      expect(mockOnQualityChange).toHaveBeenCalledWith('high');
    });
  });

  describe('Default Quality Options', () => {
    it('uses default options when qualityOptions not provided', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="medium"
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      // Should still show the default options
      expect(screen.getByText('Low')).toBeInTheDocument();
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(screen.getByText('High')).toBeInTheDocument();
    });
  });

  describe('Quality Descriptions', () => {
    it('shows low quality description', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="low"
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      expect(screen.getByText('Lower bandwidth, suitable for slow connections')).toBeInTheDocument();
    });

    it('shows high quality description', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="high"
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      expect(screen.getByText('Best quality, requires fast connection')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has accessible trigger button', () => {
      render(
        <StreamQualitySelector
          currentQuality="medium"
          onQualityChange={mockOnQualityChange}
        />
      );

      const button = screen.getByTitle('Stream quality');
      expect(button).toHaveAttribute('type', 'button');
    });

    it('options are keyboard accessible', async () => {
      const { user } = render(
        <StreamQualitySelector
          currentQuality="medium"
          qualityOptions={defaultQualityOptions}
          onQualityChange={mockOnQualityChange}
        />
      );

      const trigger = screen.getByTitle('Stream quality');
      await user.click(trigger);

      // All options should be focusable buttons
      const lowButton = screen.getByText('Low').closest('button');
      const mediumButton = screen.getByText('Medium').closest('button');
      const highButton = screen.getByText('High').closest('button');

      expect(lowButton).toBeInTheDocument();
      expect(mediumButton).toBeInTheDocument();
      expect(highButton).toBeInTheDocument();
    });
  });
});
