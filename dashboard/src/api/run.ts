import { postJson } from './client'
import type { RunCompareResponse, RunRequest, RunTraceResponse } from './types'

export function postRun(request: RunRequest) {
  // Generous explicit timeout: LLM decision alone can take up to the
  // backend's configured decision.timeout_s (180s default) on local hardware.
  return postJson<RunTraceResponse>('/api/run', request, 200_000)
}

export function postRunCompare(request: RunRequest) {
  // Runs both pipelines sequentially server-side (two LLM decision calls) --
  // double the single-run timeout budget.
  return postJson<RunCompareResponse>('/api/run/compare', request, 400_000)
}
