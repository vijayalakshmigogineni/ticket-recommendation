import { getJson } from './client'
import type { InteractionDetailResponse, InteractionListResponse } from './types'

export interface ListInteractionsParams {
  ticket_id?: string
  customer_id?: string
  interaction_type?: string
  has_embedding?: boolean
  limit?: number
  offset?: number
}

export function listInteractions(params: ListInteractionsParams = {}, signal?: AbortSignal) {
  const search = new URLSearchParams()
  if (params.ticket_id) search.set('ticket_id', params.ticket_id)
  if (params.customer_id) search.set('customer_id', params.customer_id)
  if (params.interaction_type) search.set('interaction_type', params.interaction_type)
  if (params.has_embedding !== undefined) search.set('has_embedding', String(params.has_embedding))
  search.set('limit', String(params.limit ?? 50))
  search.set('offset', String(params.offset ?? 0))
  return getJson<InteractionListResponse>(`/api/interactions?${search.toString()}`, signal)
}

export function getInteraction(interactionId: string, topN = 10, signal?: AbortSignal) {
  return getJson<InteractionDetailResponse>(
    `/api/interactions/${interactionId}?top_n=${topN}`,
    signal,
  )
}
