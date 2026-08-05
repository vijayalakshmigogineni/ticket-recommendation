import { useMutation } from '@tanstack/react-query'
import { postRun } from '../api/run'
import { useSetLastRun } from './useLastRun'

/** Long-running, LLM-bound mutation -- retries disabled on purpose (re-firing
 * a 60-180s call automatically on transient failure is undesirable; the user
 * can just click run again). On success, writes the trace into the shared
 * query cache so the Pipeline Explorer and Metrics pages can read it without
 * a second call.
 */
export function useRunTrace() {
  const setLastRun = useSetLastRun()

  return useMutation({
    mutationFn: postRun,
    retry: false,
    onSuccess: (data) => {
      setLastRun(data)
    },
  })
}
