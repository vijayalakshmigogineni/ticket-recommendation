import { getJson } from './client'
import type { ABBenchmarkResponse, EvaluationStatusResponse } from './types'

export function getEvaluationStatus(signal?: AbortSignal) {
  return getJson<EvaluationStatusResponse>('/api/evaluation/status', signal)
}

export function getAbBenchmarkStatus(signal?: AbortSignal) {
  return getJson<ABBenchmarkResponse>('/api/evaluation/ab-benchmark', signal)
}
