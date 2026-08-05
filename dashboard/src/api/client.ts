const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// /api/run and /api/search/vector can legitimately take minutes (local LLM +
// embedding inference) -- default timeout is generous, not the usual few
// seconds a naive fetch wrapper would impose.
const DEFAULT_TIMEOUT_MS = 200_000

export class ApiError extends Error {
  status: number
  body: unknown

  constructor(status: number, message: string, body: unknown) {
    super(message)
    this.status = status
    this.body = body
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST'
  body?: unknown
  timeoutMs?: number
  signal?: AbortSignal
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, timeoutMs = DEFAULT_TIMEOUT_MS, signal } = options

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  if (signal) {
    signal.addEventListener('abort', () => controller.abort())
  }

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })

    let payload: unknown = null
    const text = await response.text()
    if (text) {
      try {
        payload = JSON.parse(text)
      } catch {
        payload = text
      }
    }

    if (!response.ok) {
      const message =
        payload && typeof payload === 'object' && 'detail' in payload
          ? String((payload as { detail: unknown }).detail)
          : `Request failed with status ${response.status}`
      throw new ApiError(response.status, message, payload)
    }

    return payload as T
  } catch (err) {
    if (err instanceof ApiError) throw err
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(0, `Request timed out after ${timeoutMs}ms`, null)
    }
    throw new ApiError(0, err instanceof Error ? err.message : 'Network error', null)
  } finally {
    clearTimeout(timeoutId)
  }
}

export function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  return apiFetch<T>(path, { method: 'GET', signal })
}

export function postJson<T>(path: string, body: unknown, timeoutMs?: number): Promise<T> {
  return apiFetch<T>(path, { method: 'POST', body, timeoutMs })
}
