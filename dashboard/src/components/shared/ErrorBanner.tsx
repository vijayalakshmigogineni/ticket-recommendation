import { ApiError } from '../../api/client'
import { JsonViewer } from './JsonViewer'

interface ErrorBannerProps {
  error: unknown
  onRetry?: () => void
}

export function ErrorBanner({ error, onRetry }: ErrorBannerProps) {
  const message = error instanceof Error ? error.message : 'Something went wrong'
  const body = error instanceof ApiError ? error.body : undefined

  return (
    <div className="rounded-lg border border-red-800 bg-red-950/40 p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-red-300">{message}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="rounded border border-red-700 px-2 py-1 text-xs text-red-300 hover:bg-red-900"
          >
            Retry
          </button>
        )}
      </div>
      {body !== undefined && body !== null && (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-red-400">Raw error detail</summary>
          <div className="mt-1">
            <JsonViewer data={body} />
          </div>
        </details>
      )}
    </div>
  )
}
