import { EmailInputForm } from '../components/playground/EmailInputForm'
import { RecentFeedbackList } from '../components/playground/RecentFeedbackList'
import { RecommendationResultCard } from '../components/playground/RecommendationResultCard'
import { ErrorBanner } from '../components/shared/ErrorBanner'
import { useRunTrace } from '../hooks/useRunTrace'

export function Playground() {
  const runMutation = useRunTrace()

  return (
    <div>
      <h1 className="mb-1 text-lg font-semibold text-neutral-100">Recommendation Playground</h1>
      <p className="mb-4 text-xs text-neutral-500">
        Run any email through the full pipeline. Embedding + LLM decision are local inference and
        can take up to a couple of minutes.
      </p>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <EmailInputForm onSubmit={(req) => runMutation.mutate(req)} isSubmitting={runMutation.isPending} />

        <div>
          {runMutation.isPending && (
            <p className="text-xs text-neutral-500">Running pipeline…</p>
          )}
          {runMutation.isError && <ErrorBanner error={runMutation.error} />}
          {runMutation.data && <RecommendationResultCard result={runMutation.data} />}
          {!runMutation.data && !runMutation.isPending && !runMutation.isError && (
            <p className="text-xs text-neutral-600">
              Fill in the form and run a recommendation to see the result here.
            </p>
          )}
        </div>
      </div>

      <div className="mt-8">
        <RecentFeedbackList />
      </div>
    </div>
  )
}
