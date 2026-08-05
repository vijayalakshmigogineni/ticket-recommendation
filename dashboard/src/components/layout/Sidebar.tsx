import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: 'Home', end: true },
  { to: '/playground', label: 'Playground' },
  { to: '/pipeline', label: 'Pipeline Explorer' },
  { to: '/pipeline-comparison', label: 'Reranker A/B Comparison' },
  { to: '/ann-inspector', label: 'ANN Inspector' },
  { to: '/dataset', label: 'Dataset Explorer' },
  { to: '/metrics', label: 'Metrics' },
  { to: '/evaluation', label: 'Evaluation' },
  { to: '/ab-benchmark', label: 'Reranker A/B Benchmark' },
  { to: '/settings', label: 'Settings' },
]

export function Sidebar() {
  return (
    <nav className="w-56 shrink-0 border-r border-neutral-800 bg-neutral-950 p-3">
      <div className="mb-4 px-2 text-sm font-semibold text-neutral-200">
        Recommender Debug Dashboard
      </div>
      <ul className="space-y-1">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block rounded px-2 py-1.5 text-sm ${
                  isActive
                    ? 'bg-neutral-800 text-neutral-100'
                    : 'text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200'
                }`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
