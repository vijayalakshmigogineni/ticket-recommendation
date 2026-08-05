import type { StageStatus } from '../../lib/stageAvailability'

const styles: Record<StageStatus, string> = {
  ran: 'bg-emerald-950 text-emerald-400 border-emerald-800',
  skipped: 'bg-neutral-800 text-neutral-400 border-neutral-700',
  error: 'bg-red-950 text-red-400 border-red-800',
}

const labels: Record<StageStatus, string> = {
  ran: 'ran',
  skipped: 'skipped',
  error: 'error',
}

export function StageStatusPill({ status, reason }: { status: StageStatus; reason?: string }) {
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 text-xs ${styles[status]}`}
      title={reason}
    >
      {labels[status]}
    </span>
  )
}
