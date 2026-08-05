import { useQuery } from '@tanstack/react-query'
import { getSystemStatus } from '../api/system'
import { queryKeys } from '../api/queryKeys'
import { ErrorBanner } from '../components/shared/ErrorBanner'
import { LoadingSkeleton } from '../components/shared/LoadingSkeleton'
import { StatTile } from '../components/shared/StatTile'

export function DashboardHome() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: ({ signal }) => getSystemStatus(signal),
  })

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold text-neutral-100">Dashboard Home</h1>

      {isLoading && <LoadingSkeleton shape="tile" count={8} />}
      {isError && <ErrorBanner error={error} onRetry={() => refetch()} />}

      {data && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatTile
            label="Pipeline Status"
            value={data.database.connected && data.ollama.reachable ? 'Healthy' : 'Degraded'}
            status={data.database.connected && data.ollama.reachable ? 'ok' : 'error'}
          />
          <StatTile label="Embedding Model" value={data.embedding_model} />
          <StatTile label="Reranker" value={data.reranker_model} sublabel={data.reranker_device} />
          <StatTile label="LLM" value={data.llm_model} />
          <StatTile
            label="Database"
            value={data.database.connected ? 'Connected' : 'Unreachable'}
            status={data.database.connected ? 'ok' : 'error'}
            sublabel={data.database.error ?? undefined}
          />
          <StatTile
            label="Ollama"
            value={data.ollama.reachable ? 'Reachable' : 'Unreachable'}
            status={data.ollama.reachable ? 'ok' : 'error'}
            sublabel={data.ollama.host}
          />
          <StatTile label="Tickets" value={data.counts.tickets} />
          <StatTile label="Interactions" value={data.counts.interactions} />
          <StatTile
            label="Indexed Embeddings"
            value={data.counts.indexed_embeddings}
            sublabel={`of ${data.counts.interactions} interactions`}
          />
          <StatTile label="Customers" value={data.counts.customers} />
        </div>
      )}
    </div>
  )
}
