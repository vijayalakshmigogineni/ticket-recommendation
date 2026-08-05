import type { InteractionSummary } from '../../api/types'
import { formatDateTime } from '../../lib/format'

interface InteractionTableProps {
  interactions: InteractionSummary[]
  onSelect: (interactionId: string) => void
  selectedId?: string
}

export function InteractionTable({ interactions, onSelect, selectedId }: InteractionTableProps) {
  if (interactions.length === 0) {
    return <p className="text-xs text-neutral-500">No interactions.</p>
  }

  return (
    <div className="overflow-x-auto rounded border border-neutral-800">
      <table className="w-full text-left text-xs">
        <thead className="bg-neutral-900 text-neutral-500">
          <tr>
            <th className="px-2 py-1 font-medium">Type</th>
            <th className="px-2 py-1 font-medium">Sender</th>
            <th className="px-2 py-1 font-medium">Preview</th>
            <th className="px-2 py-1 font-medium">Embedded</th>
            <th className="px-2 py-1 font-medium">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-800">
          {interactions.map((i) => (
            <tr
              key={i.id}
              onClick={() => onSelect(i.id)}
              className={`cursor-pointer hover:bg-neutral-900/60 ${
                selectedId === i.id ? 'bg-neutral-900' : ''
              }`}
            >
              <td className="px-2 py-1 text-neutral-400">{i.interaction_type}</td>
              <td className="px-2 py-1 text-neutral-400">{i.sender_email}</td>
              <td className="max-w-md truncate px-2 py-1 text-neutral-300">
                {i.clean_content_preview}
              </td>
              <td className="px-2 py-1">
                {i.has_embedding ? (
                  <span className="text-emerald-400">yes</span>
                ) : (
                  <span className="text-neutral-600">no</span>
                )}
              </td>
              <td className="px-2 py-1 text-neutral-500">{formatDateTime(i.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
