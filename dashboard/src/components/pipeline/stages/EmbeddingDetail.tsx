import type { EmbeddingTrace } from '../../../api/types'
import { formatScore } from '../../../lib/format'
import { VectorPreviewChips } from '../../shared/VectorPreviewChips'

export function EmbeddingDetail({ trace }: { trace: EmbeddingTrace }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-4 gap-3 text-xs">
        <div>
          <div className="text-neutral-500">Model</div>
          <div className="text-neutral-200">{trace.model}</div>
        </div>
        <div>
          <div className="text-neutral-500">Dimension</div>
          <div className="text-neutral-200">{trace.dimension}</div>
        </div>
        <div>
          <div className="text-neutral-500">Vector Norm</div>
          <div className="text-neutral-200">{formatScore(trace.norm)}</div>
        </div>
        <div>
          <div className="text-neutral-500">Min / Max</div>
          <div className="text-neutral-200">
            {formatScore(trace.min)} / {formatScore(trace.max)}
          </div>
        </div>
      </div>
      <div>
        <div className="mb-1 text-xs font-medium text-neutral-500">Embedding Preview</div>
        <VectorPreviewChips values={trace.preview_first_20} dimension={trace.dimension} />
      </div>
    </div>
  )
}
