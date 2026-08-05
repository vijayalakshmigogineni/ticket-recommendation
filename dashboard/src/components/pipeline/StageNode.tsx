import { DurationBadge } from '../shared/DurationBadge'
import { StageStatusPill } from '../shared/StageStatusPill'
import type { StageAvailability, StageKey } from '../../lib/stageAvailability'
import { STAGE_LABELS } from '../../lib/stageAvailability'

interface StageNodeProps {
  stageKey: StageKey
  availability: StageAvailability
  timeMs?: number
  isSelected: boolean
  onClick: () => void
  isLast: boolean
}

export function StageNode({ stageKey, availability, timeMs, isSelected, onClick, isLast }: StageNodeProps) {
  return (
    <div className="flex">
      <div className="flex flex-col items-center">
        <div
          className={`h-2.5 w-2.5 rounded-full ${
            availability.status === 'ran'
              ? 'bg-emerald-500'
              : availability.status === 'error'
                ? 'bg-red-500'
                : 'bg-neutral-700'
          }`}
        />
        {!isLast && <div className="w-px flex-1 bg-neutral-800" />}
      </div>
      <button
        type="button"
        onClick={onClick}
        className={`mb-3 ml-3 flex-1 rounded border px-3 py-2 text-left text-xs ${
          isSelected
            ? 'border-neutral-600 bg-neutral-800'
            : 'border-neutral-800 bg-neutral-900 hover:bg-neutral-900/70'
        }`}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-neutral-200">{STAGE_LABELS[stageKey]}</span>
          <StageStatusPill status={availability.status} reason={availability.reason} />
        </div>
        <div className="mt-1 flex items-center justify-between">
          {availability.reason && (
            <span className="truncate text-[11px] text-neutral-600">{availability.reason}</span>
          )}
          {timeMs !== undefined && <DurationBadge ms={timeMs} />}
        </div>
      </button>
    </div>
  )
}
