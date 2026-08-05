import { getJson } from './client'
import type { IndexInfoResponse, SystemSettingsResponse, SystemStatusResponse } from './types'

export function getSystemStatus(signal?: AbortSignal) {
  return getJson<SystemStatusResponse>('/api/system/status', signal)
}

export function getSystemSettings(signal?: AbortSignal) {
  return getJson<SystemSettingsResponse>('/api/system/settings', signal)
}

export function getIndexInfo(signal?: AbortSignal) {
  return getJson<IndexInfoResponse>('/api/system/index-info', signal)
}
