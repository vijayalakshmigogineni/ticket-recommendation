import { getJson, postJson } from './client'
import type { FeedbackListResponse, FeedbackRecord, RecordFeedbackRequest } from './types'

export function recordFeedback(request: RecordFeedbackRequest) {
  return postJson<FeedbackRecord>('/api/feedback', request)
}

export interface ListFeedbackParams {
  customer_id?: string
  limit?: number
}

export function listFeedback(params: ListFeedbackParams = {}, signal?: AbortSignal) {
  const search = new URLSearchParams()
  if (params.customer_id) search.set('customer_id', params.customer_id)
  search.set('limit', String(params.limit ?? 20))
  return getJson<FeedbackListResponse>(`/api/feedback?${search.toString()}`, signal)
}
