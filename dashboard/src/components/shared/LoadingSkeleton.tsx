interface LoadingSkeletonProps {
  shape?: 'tile' | 'table' | 'block'
  count?: number
}

export function LoadingSkeleton({ shape = 'block', count = 1 }: LoadingSkeletonProps) {
  const items = Array.from({ length: count })

  if (shape === 'tile') {
    return (
      <div className="grid grid-cols-4 gap-3">
        {items.map((_, i) => (
          <div key={i} className="h-20 animate-pulse rounded-lg bg-neutral-800" />
        ))}
      </div>
    )
  }

  if (shape === 'table') {
    return (
      <div className="space-y-2">
        {items.map((_, i) => (
          <div key={i} className="h-8 animate-pulse rounded bg-neutral-800" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {items.map((_, i) => (
        <div key={i} className="h-32 animate-pulse rounded-lg bg-neutral-800" />
      ))}
    </div>
  )
}
