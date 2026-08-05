import type { ReactNode } from 'react'

export interface Column<T> {
  header: string
  render: (row: T, index: number) => ReactNode
  className?: string
}

interface ScoredResultsTableProps<T> {
  rows: T[]
  columns: Column<T>[]
  keyField: (row: T, index: number) => string
  emptyMessage?: string
}

export function ScoredResultsTable<T>({
  rows,
  columns,
  keyField,
  emptyMessage = 'No results.',
}: ScoredResultsTableProps<T>) {
  if (rows.length === 0) {
    return <p className="text-xs text-neutral-500">{emptyMessage}</p>
  }

  return (
    <div className="overflow-x-auto rounded border border-neutral-800">
      <table className="w-full text-left text-xs">
        <thead className="bg-neutral-900 text-neutral-500">
          <tr>
            <th className="px-2 py-1 font-medium">#</th>
            {columns.map((col) => (
              <th key={col.header} className="px-2 py-1 font-medium">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-800">
          {rows.map((row, i) => (
            <tr key={keyField(row, i)} className="hover:bg-neutral-900/60">
              <td className="px-2 py-1 text-neutral-600">{i + 1}</td>
              {columns.map((col) => (
                <td key={col.header} className={`px-2 py-1 align-top ${col.className ?? ''}`}>
                  {col.render(row, i)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
