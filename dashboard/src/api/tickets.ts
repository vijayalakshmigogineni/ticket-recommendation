import { getJson } from './client'
import type { TicketDetailResponse, TicketListResponse } from './types'

export interface ListTicketsParams {
  customer_id?: string
  status?: string
  limit?: number
  offset?: number
}

export function listTickets(params: ListTicketsParams = {}, signal?: AbortSignal) {
  const search = new URLSearchParams()
  if (params.customer_id) search.set('customer_id', params.customer_id)
  if (params.status) search.set('status', params.status)
  search.set('limit', String(params.limit ?? 50))
  search.set('offset', String(params.offset ?? 0))
  return getJson<TicketListResponse>(`/api/tickets?${search.toString()}`, signal)
}

export function getTicket(ticketId: string, signal?: AbortSignal) {
  return getJson<TicketDetailResponse>(`/api/tickets/${ticketId}`, signal)
}
