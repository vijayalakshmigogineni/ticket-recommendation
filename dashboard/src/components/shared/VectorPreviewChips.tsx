export function VectorPreviewChips({ values, dimension }: { values: number[]; dimension?: number }) {
  return (
    <div>
      <div className="flex flex-wrap gap-1">
        {values.map((v, i) => (
          <span
            key={i}
            className="rounded border border-neutral-800 bg-neutral-900 px-1.5 py-0.5 font-mono text-[11px] text-neutral-400"
          >
            {v.toFixed(4)}
          </span>
        ))}
      </div>
      {dimension !== undefined && (
        <div className="mt-1 text-xs text-neutral-600">
          showing first {values.length} of {dimension} dimensions
        </div>
      )}
    </div>
  )
}
