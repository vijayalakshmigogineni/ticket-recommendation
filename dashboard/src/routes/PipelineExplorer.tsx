import { useState } from 'react'
import { StageDetailPanel } from '../components/pipeline/StageDetailPanel'
import { StageTimeline } from '../components/pipeline/StageTimeline'
import { EmailInputForm } from '../components/playground/EmailInputForm'
import { EmptyState } from '../components/shared/EmptyState'
import { ErrorBanner } from '../components/shared/ErrorBanner'
import { useLastRun } from '../hooks/useLastRun'
import { useRunTrace } from '../hooks/useRunTrace'
import type { StageKey } from '../lib/stageAvailability'

export function PipelineExplorer() {
  const lastRun = useLastRun()
  const runMutation = useRunTrace()
  const [selectedStage, setSelectedStage] = useState<StageKey>('incoming_email')

  const trace = runMutation.data ?? lastRun

  return (
    <div>
      <h1 className="mb-1 text-lg font-semibold text-neutral-100">Pipeline Explorer</h1>
      <p className="mb-4 text-xs text-neutral-500">
        Every stage of the last run, in order. Click a stage to see its input/output/timing.
      </p>

      {runMutation.isError && <ErrorBanner error={runMutation.error} />}

      {!trace ? (
        <EmptyState
          message="No run yet in this session -- run one below to populate the explorer."
          action={
            <div className="w-full max-w-xl text-left">
              <EmailInputForm
                onSubmit={(req) => runMutation.mutate(req)}
                isSubmitting={runMutation.isPending}
              />
            </div>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
          <div>
            <StageTimeline
              trace={trace}
              selectedStage={selectedStage}
              onSelectStage={setSelectedStage}
            />
          </div>
          <div className="rounded border border-neutral-800 bg-neutral-900 p-4">
            <StageDetailPanel trace={trace} stage={selectedStage} />
          </div>
        </div>
      )}
    </div>
  )
}
