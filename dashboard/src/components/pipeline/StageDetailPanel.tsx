import type { RunTraceResponse } from '../../api/types'
import { getStageAvailability, STAGE_LABELS, type StageKey } from '../../lib/stageAvailability'
import { EmptyState } from '../shared/EmptyState'
import { TicketBadge } from '../shared/TicketBadge'
import { AnnSearchDetail } from './stages/AnnSearchDetail'
import { ContextBuilderDetail } from './stages/ContextBuilderDetail'
import { CrossEncoderDetail } from './stages/CrossEncoderDetail'
import { EmbeddingDetail } from './stages/EmbeddingDetail'
import { GroupingDetail } from './stages/GroupingDetail'
import { HybridRetrievalDetail } from './stages/HybridRetrievalDetail'
import { KeywordSearchDetail } from './stages/KeywordSearchDetail'
import { LlmDecisionDetail } from './stages/LlmDecisionDetail'
import { PreprocessingDetail } from './stages/PreprocessingDetail'

interface StageDetailPanelProps {
  trace: RunTraceResponse
  stage: StageKey
}

export function StageDetailPanel({ trace, stage }: StageDetailPanelProps) {
  const availability = getStageAvailability(trace)[stage]

  if (availability.status === 'skipped') {
    return <EmptyState message={`Skipped -- ${availability.reason}`} />
  }

  switch (stage) {
    case 'incoming_email':
      return (
        <div className="space-y-2 text-xs">
          <div>
            <span className="text-neutral-500">From: </span>
            <span className="text-neutral-200">{trace.customer?.inbox_email ?? '(unknown sender)'}</span>
          </div>
          <div>
            <span className="text-neutral-500">Subject: </span>
            <span className="text-neutral-200">{trace.preprocessing?.original_subject}</span>
          </div>
        </div>
      )

    case 'preprocessing':
      return trace.preprocessing ? (
        <PreprocessingDetail trace={trace.preprocessing} />
      ) : (
        <EmptyState message="No preprocessing data." />
      )

    case 'customer_identification':
      return (
        <div className="text-xs">
          {trace.customer ? (
            <p className="text-neutral-300">
              Matched customer: <span className="text-neutral-100">{trace.customer.name}</span> (
              {trace.customer.inbox_email})
            </p>
          ) : (
            <p className="text-neutral-400">No customer matched this sender address.</p>
          )}
        </div>
      )

    case 'thread_detection':
      return (
        <div className="text-xs">
          {trace.thread_detection?.matched ? (
            <div className="space-y-1">
              <p className="text-neutral-300">
                Matched on <span className="text-neutral-100">{trace.thread_detection.matched_on}</span>
              </p>
              {trace.thread_detection.ticket && <TicketBadge ticket={trace.thread_detection.ticket} />}
            </div>
          ) : (
            <p className="text-neutral-400">
              No existing thread found -- continuing to the AI pipeline.
            </p>
          )}
        </div>
      )

    case 'embedding':
      return trace.embedding ? (
        <EmbeddingDetail trace={trace.embedding} />
      ) : (
        <EmptyState message="No embedding data." />
      )

    case 'keyword_search':
      return trace.keyword_search ? (
        <KeywordSearchDetail trace={trace.keyword_search} />
      ) : (
        <EmptyState message="No keyword search data." />
      )

    case 'ann_search':
      return trace.ann_search ? (
        <AnnSearchDetail trace={trace.ann_search} />
      ) : (
        <EmptyState message="No ANN search data." />
      )

    case 'fusion':
      return trace.fusion ? (
        <HybridRetrievalDetail trace={trace.fusion} />
      ) : (
        <EmptyState message="No fusion data." />
      )

    case 'grouping':
      return trace.grouping ? (
        <GroupingDetail trace={trace.grouping} />
      ) : (
        <EmptyState message="No grouping data." />
      )

    case 'context_building':
      return trace.context_building ? (
        <ContextBuilderDetail trace={trace.context_building} />
      ) : (
        <EmptyState message="No context builder data." />
      )

    case 'reranking':
      return trace.reranking ? (
        <CrossEncoderDetail trace={trace.reranking} />
      ) : (
        <EmptyState message="No reranking data." />
      )

    case 'decision':
      return trace.decision ? (
        <LlmDecisionDetail trace={trace.decision} />
      ) : (
        <EmptyState message="No decision data." />
      )

    case 'recommendation':
      return (
        <div className="text-xs">
          <p className="mb-2 text-neutral-500">Path: {trace.path}</p>
          {trace.recommended_ticket_id ? (
            <p className="text-neutral-300">
              Recommended ticket ID:{' '}
              <span className="font-mono text-neutral-100">{trace.recommended_ticket_id}</span>
            </p>
          ) : (
            <p className="text-neutral-400">No ticket recommended.</p>
          )}
        </div>
      )

    default:
      return <EmptyState message={`No detail view for ${STAGE_LABELS[stage]}.`} />
  }
}
