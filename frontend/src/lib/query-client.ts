/**
 * Shared TanStack Query client with sensible defaults for the CMS
 * Fraud Detection dashboard.
 *
 * - staleTime 60s: data that just arrived is "fresh" for 1 minute —
 *   navigating between pages during that window returns instantly.
 * - gcTime 5min: unused cache entries survive for 5 minutes so
 *   back-navigation is always fast.
 * - refetchOnWindowFocus true: user returning to the tab gets fresh data.
 */

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000, // 60 seconds
      gcTime: 5 * 60_000, // 5 minutes
      refetchOnWindowFocus: true,
      retry: 1,
    },
  },
});
