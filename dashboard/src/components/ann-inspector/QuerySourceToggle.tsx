export type QuerySource = 'existing' | 'typed'

interface QuerySourceToggleProps {
  value: QuerySource
  onChange: (value: QuerySource) => void
}

export function QuerySourceToggle({ value, onChange }: QuerySourceToggleProps) {
  return (
    <div className="inline-flex rounded border border-neutral-800 text-xs">
      <button
        type="button"
        onClick={() => onChange('existing')}
        className={`px-3 py-1.5 ${value === 'existing' ? 'bg-neutral-800 text-neutral-100' : 'text-neutral-400'}`}
      >
        Existing interaction
      </button>
      <button
        type="button"
        onClick={() => onChange('typed')}
        className={`px-3 py-1.5 ${value === 'typed' ? 'bg-neutral-800 text-neutral-100' : 'text-neutral-400'}`}
      >
        Type new query
      </button>
    </div>
  )
}
