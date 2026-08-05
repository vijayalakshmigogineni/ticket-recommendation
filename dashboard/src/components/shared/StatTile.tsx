interface StatTileProps {
  label: string
  value: string | number
  sublabel?: string
  status?: 'ok' | 'warn' | 'error' | 'neutral'
}

const statusColors: Record<NonNullable<StatTileProps['status']>, string> = {
  ok: 'text-emerald-400',
  warn: 'text-amber-400',
  error: 'text-red-400',
  neutral: 'text-neutral-100',
}

export function StatTile({ label, value, sublabel, status = 'neutral' }: StatTileProps) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${statusColors[status]}`}>{value}</div>
      {sublabel && <div className="mt-0.5 text-xs text-neutral-500">{sublabel}</div>}
    </div>
  )
}
