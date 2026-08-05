import type { RunTraceResponse } from '../../api/types'
import { STAGE_ORDER, getStageAvailability, type StageKey } from '../../lib/stageAvailability'
import { StageNode } from './StageNode'

interface StageTimelineProps {
  trace: RunTraceResponse
  selectedStage: StageKey
  onSelectStage: (stage: StageKey) => void
}

export function StageTimeline({ trace, selectedStage, onSelectStage }: StageTimelineProps) {
  const availability = getStageAvailability(trace)

  return (
    <div>
      {STAGE_ORDER.map((key, idx) => (
        <StageNode
          key={key}
          stageKey={key}
          availability={availability[key]}
          timeMs={trace.stage_timings_ms[key]}
          isSelected={selectedStage === key}
          onClick={() => onSelectStage(key)}
          isLast={idx === STAGE_ORDER.length - 1}
        />
      ))}
    </div>
  )
}
