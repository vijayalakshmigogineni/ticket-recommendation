import { useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../api/queryKeys'
import type { RunCompareResponse } from '../api/types'

/** Reads the last with/without-reranker comparison run written to the shared
 * query cache by useRunCompare. Mirrors useLastRun.ts so the Pipeline
 * Comparison page survives navigation/refresh the same way the Pipeline
 * Explorer does. */
export function useLastCompare(): RunCompareResponse | undefined {
  const queryClient = useQueryClient()
  return queryClient.getQueryData<RunCompareResponse>(queryKeys.lastCompare)
}

export function useSetLastCompare() {
  const queryClient = useQueryClient()
  return (data: RunCompareResponse) => queryClient.setQueryData(queryKeys.lastCompare, data)
}
