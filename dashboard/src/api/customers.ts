import { getJson, postJson } from './client'
import type { CustomerListItem, CustomerListResponse } from './types'

export function listCustomers(signal?: AbortSignal) {
  return getJson<CustomerListResponse>('/api/customers', signal)
}

export interface CreateCustomerRequest {
  name: string
  inbox_email: string
}

export function createCustomer(request: CreateCustomerRequest) {
  return postJson<CustomerListItem>('/api/customers', request)
}
