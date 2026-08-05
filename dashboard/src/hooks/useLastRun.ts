import { useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../api/queryKeys'
import type { RunTraceResponse } from '../api/types'

/** Reads the last pipeline run written to the shared query cache by the
 * Playground's run mutation. Lets the Pipeline Explorer / Metrics pages be
 * entered directly (bookmark, refresh) and show an empty state if nothing's
 * been run yet, without ever re-firing the (potentially minutes-long) call.
 */
export function useLastRun(): RunTraceResponse | undefined {
  const queryClient = useQueryClient()
  return queryClient.getQueryData<RunTraceResponse>(queryKeys.lastRun)
}

export function useSetLastRun() {
  const queryClient = useQueryClient()
  return (data: RunTraceResponse) => queryClient.setQueryData(queryKeys.lastRun, data)
}
