/**
 * TanStack Query hooks for Activity Summaries (Story P4-4.4)
 *
 * Provides hooks for fetching recent activity summaries for the dashboard.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient, RecentSummariesResponse, RecentSummaryItem } from '@/lib/api-client';

// Re-export types for convenience
export type { RecentSummariesResponse, RecentSummaryItem };

/**
 * Hook to fetch recent summaries (today and yesterday) for dashboard display.
 *
 * AC11: SummaryCard refreshes data every 5 minutes using TanStack Query
 *
 * @returns TanStack Query result with recent summaries
 */
export function useRecentSummaries() {
  return useQuery({
    queryKey: ['summaries', 'recent'],
    queryFn: async (): Promise<RecentSummariesResponse> => {
      return apiClient.summaries.recent();
    },
    refetchInterval: 5 * 60 * 1000, // 5 minutes (AC11)
    staleTime: 60 * 1000, // 1 minute
  });
}
