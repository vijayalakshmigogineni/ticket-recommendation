import { JsonView, allExpanded, darkStyles } from 'react-json-view-lite'
import 'react-json-view-lite/dist/index.css'

export function JsonViewer({ data }: { data: unknown }) {
  if (data === null || data === undefined) {
    return <span className="text-xs text-neutral-600">null</span>
  }
  return (
    <div className="rounded border border-neutral-800 bg-neutral-950 p-2 text-xs">
      <JsonView data={data as object} shouldExpandNode={allExpanded} style={darkStyles} />
    </div>
  )
}
