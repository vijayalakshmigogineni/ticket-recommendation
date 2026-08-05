import { useMutation } from '@tanstack/react-query'
import { postRunCompare } from '../api/run'
import { useSetLastCompare } from './useLastCompare'

/** Long-running mutation -- runs both pipelines server-side (two LLM
 * decision calls back to back), so it takes roughly 2x as long as a single
 * useRunTrace call. Retries disabled for the same reason as useRunTrace. */
export function useRunCompare() {
  const setLastCompare = useSetLastCompare()

  return useMutation({
    mutationFn: postRunCompare,
    retry: false,
    onSuccess: (data) => {
      setLastCompare(data)
    },
  })
}
