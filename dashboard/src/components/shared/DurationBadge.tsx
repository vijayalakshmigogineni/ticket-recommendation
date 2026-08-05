import { durationTier, formatMs } from '../../lib/format'

const tierColors = {
  fast: 'bg-emerald-950 text-emerald-400 border-emerald-800',
  medium: 'bg-amber-950 text-amber-400 border-amber-800',
  slow: 'bg-red-950 text-red-400 border-red-800',
}

export function DurationBadge({ ms }: { ms: number }) {
  const tier = durationTier(ms)
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 font-mono text-xs ${tierColors[tier]}`}
    >
      {formatMs(ms)}
    </span>
  )
}
