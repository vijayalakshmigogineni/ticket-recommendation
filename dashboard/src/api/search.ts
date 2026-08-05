import { postJson } from './client'
import type { VectorSearchRequest, VectorSearchResponse } from './types'

export function postVectorSearch(request: VectorSearchRequest) {
  return postJson<VectorSearchResponse>('/api/search/vector', request, 200_000)
}
