import { useQuery } from '@tanstack/react-query'
import { getIndexInfo, getSystemSettings } from '../api/system'
import { queryKeys } from '../api/queryKeys'
import { ErrorBanner } from '../components/shared/ErrorBanner'
import { JsonViewer } from '../components/shared/JsonViewer'
import { LoadingSkeleton } from '../components/shared/LoadingSkeleton'
import { StatTile } from '../components/shared/StatTile'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <h2 className="mb-2 text-sm font-semibold text-neutral-300">{title}</h2>
      {children}
    </section>
  )
}

export function SettingsPage() {
  const settingsQuery = useQuery({
    queryKey: queryKeys.systemSettings,
    queryFn: ({ signal }) => getSystemSettings(signal),
  })
  const indexInfoQuery = useQuery({
    queryKey: queryKeys.indexInfo,
    queryFn: ({ signal }) => getIndexInfo(signal),
  })

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold text-neutral-100">Settings</h1>
      <p className="mb-4 text-xs text-neutral-500">
        Read-only. Change values in config/recommender_config.yaml and restart the API to take
        effect.
      </p>

      {settingsQuery.isLoading && <LoadingSkeleton count={4} />}
      {settingsQuery.isError && (
        <ErrorBanner error={settingsQuery.error} onRetry={() => settingsQuery.refetch()} />
      )}

      {settingsQuery.data && (
        <>
          <Section title="Models">
            <div className="grid grid-cols-3 gap-3">
              <StatTile
                label="Embedding Model"
                value={settingsQuery.data.ollama.embedding_model}
                sublabel={`${settingsQuery.data.embedding_dimension} dims`}
              />
              <StatTile label="LLM (Decision)" value={settingsQuery.data.decision.model} />
              <StatTile label="Reranker" value={settingsQuery.data.reranker.model_name} sublabel={settingsQuery.data.reranker.device} />
            </div>
          </Section>

          <Section title="Database">
            <p className="font-mono text-xs text-neutral-400">
              {settingsQuery.data.database_url_display}
            </p>
          </Section>

          <Section title="Retrieval">
            <JsonViewer data={settingsQuery.data.retrieval} />
          </Section>
          <Section title="Aggregation">
            <JsonViewer data={settingsQuery.data.aggregation} />
          </Section>
          <Section title="Context Builder">
            <JsonViewer data={settingsQuery.data.context_builder} />
          </Section>
          <Section title="Reranker">
            <JsonViewer data={settingsQuery.data.reranker} />
          </Section>
          <Section title="Decision">
            <JsonViewer data={settingsQuery.data.decision} />
          </Section>
          <Section title="Thread Detection">
            <JsonViewer data={settingsQuery.data.thread_detection} />
          </Section>
        </>
      )}

      <Section title="Index Health (HNSW)">
        {indexInfoQuery.isLoading && <LoadingSkeleton count={1} />}
        {indexInfoQuery.isError && (
          <ErrorBanner error={indexInfoQuery.error} onRetry={() => indexInfoQuery.refetch()} />
        )}
        {indexInfoQuery.data && (
          <div className="grid grid-cols-3 gap-3 md:grid-cols-4">
            <StatTile label="Index" value={indexInfoQuery.data.index_name} />
            <StatTile label="Method" value={indexInfoQuery.data.method.toUpperCase()} />
            <StatTile label="Distance Metric" value={indexInfoQuery.data.distance_metric} />
            <StatTile label="Size" value={indexInfoQuery.data.size_pretty} />
            <StatTile label="Rows Indexed" value={indexInfoQuery.data.rows_indexed} />
            <StatTile label="m" value={indexInfoQuery.data.m ?? '—'} />
            <StatTile label="ef_construction" value={indexInfoQuery.data.ef_construction ?? '—'} />
            <StatTile
              label="Params Source"
              value={indexInfoQuery.data.params_source === 'reloptions' ? 'explicit' : 'assumed default'}
            />
          </div>
        )}
      </Section>
    </div>
  )
}
