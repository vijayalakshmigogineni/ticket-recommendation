import type { ReactNode } from 'react'

interface EmptyStateProps {
  message: string
  action?: ReactNode
}

export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-neutral-800 p-8 text-center">
      <p className="text-sm text-neutral-500">{message}</p>
      {action}
    </div>
  )
}
