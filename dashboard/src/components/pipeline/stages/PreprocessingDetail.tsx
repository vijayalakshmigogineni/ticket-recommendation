import type { PreprocessingTrace } from '../../../api/types'

export function PreprocessingDetail({ trace }: { trace: PreprocessingTrace }) {
  return (
    <div className="space-y-3">
      <div>
        <div className="mb-1 text-xs font-medium text-neutral-500">Original Subject</div>
        <p className="rounded border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-300">
          {trace.original_subject}
        </p>
      </div>
      <div>
        <div className="mb-1 text-xs font-medium text-neutral-500">Original Body</div>
        <p className="whitespace-pre-wrap rounded border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-300">
          {trace.original_body}
        </p>
      </div>
      <div className="text-center text-neutral-700">↓</div>
      <div>
        <div className="mb-1 text-xs font-medium text-neutral-500">Cleaned Body</div>
        <p className="whitespace-pre-wrap rounded border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-300">
          {trace.clean_body}
        </p>
      </div>
      <div className="text-center text-neutral-700">↓</div>
      <div>
        <div className="mb-1 text-xs font-medium text-neutral-500">
          Embedding Text (what actually gets embedded -- subject + cleaned body)
        </div>
        <p className="whitespace-pre-wrap rounded border border-neutral-800 bg-neutral-950 p-2 text-xs text-neutral-300">
          {trace.embedding_text}
        </p>
      </div>
    </div>
  )
}
