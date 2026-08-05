import type { RunTraceResponse } from '../api/types'

export type StageKey =
  | 'incoming_email'
  | 'preprocessing'
  | 'customer_identification'
  | 'thread_detection'
  | 'embedding'
  | 'keyword_search'
  | 'ann_search'
  | 'fusion'
  | 'grouping'
  | 'context_building'
  | 'reranking'
  | 'decision'
  | 'recommendation'

export type StageStatus = 'ran' | 'skipped' | 'error'

export interface StageAvailability {
  status: StageStatus
  reason?: string
}

export const STAGE_LABELS: Record<StageKey, string> = {
  incoming_email: 'Incoming Email',
  preprocessing: 'Preprocessing',
  customer_identification: 'Customer Identification',
  thread_detection: 'Thread Detection',
  embedding: 'Email Embedding',
  keyword_search: 'Keyword Search',
  ann_search: 'ANN Search',
  fusion: 'Hybrid Retrieval',
  grouping: 'Interaction Grouping / Ticket Aggregation',
  context_building: 'Context Builder',
  reranking: 'Cross Encoder',
  decision: 'LLM Decision',
  recommendation: 'Recommendation',
}

export const STAGE_ORDER: StageKey[] = [
  'incoming_email',
  'preprocessing',
  'customer_identification',
  'thread_detection',
  'embedding',
  'keyword_search',
  'ann_search',
  'fusion',
  'grouping',
  'context_building',
  'reranking',
  'decision',
  'recommendation',
]

const UNKNOWN_CUSTOMER_REASON = "sender email didn't match any known customer inbox_email"
const AUTO_ATTACH_REASON = 'thread auto-attached to an existing open ticket -- no AI involved'
const RERANKER_BYPASSED_REASON =
  'experimental pipeline -- cross-encoder bypassed by design, top candidates taken directly from grouping final_score'

export function getStageAvailability(
  trace: RunTraceResponse,
): Record<StageKey, StageAvailability> {
  const ran: StageAvailability = { status: 'ran' }

  if (trace.path === 'unknown_customer') {
    return {
      incoming_email: ran,
      preprocessing: ran,
      customer_identification: { status: 'ran' },
      thread_detection: { status: 'skipped', reason: UNKNOWN_CUSTOMER_REASON },
      embedding: { status: 'skipped', reason: UNKNOWN_CUSTOMER_REASON },
      keyword_search: { status: 'skipped', reason: UNKNOWN_CUSTOMER_REASON },
      ann_search: { status: 'skipped', reason: UNKNOWN_CUSTOMER_REASON },
      fusion: { status: 'skipped', reason: UNKNOWN_CUSTOMER_REASON },
      grouping: { status: 'skipped', reason: UNKNOWN_CUSTOMER_REASON },
      context_building: { status: 'skipped', reason: UNKNOWN_CUSTOMER_REASON },
      reranking: { status: 'skipped', reason: UNKNOWN_CUSTOMER_REASON },
      decision: { status: 'skipped', reason: UNKNOWN_CUSTOMER_REASON },
      recommendation: ran,
    }
  }

  if (trace.path === 'auto_attach') {
    return {
      incoming_email: ran,
      preprocessing: ran,
      customer_identification: ran,
      thread_detection: ran,
      embedding: { status: 'skipped', reason: AUTO_ATTACH_REASON },
      keyword_search: { status: 'skipped', reason: AUTO_ATTACH_REASON },
      ann_search: { status: 'skipped', reason: AUTO_ATTACH_REASON },
      fusion: { status: 'skipped', reason: AUTO_ATTACH_REASON },
      grouping: { status: 'skipped', reason: AUTO_ATTACH_REASON },
      context_building: { status: 'skipped', reason: AUTO_ATTACH_REASON },
      reranking: { status: 'skipped', reason: AUTO_ATTACH_REASON },
      decision: { status: 'skipped', reason: AUTO_ATTACH_REASON },
      recommendation: ran,
    }
  }

  // ai_decision -- every stage ran, except reranking is intentionally
  // bypassed by design in the no_reranker experimental pipeline (not an
  // error and not a path-driven skip like the two cases above).
  return {
    incoming_email: ran,
    preprocessing: ran,
    customer_identification: ran,
    thread_detection: ran,
    embedding: ran,
    keyword_search: ran,
    ann_search: ran,
    fusion: ran,
    grouping: ran,
    context_building: ran,
    reranking:
      trace.pipeline_variant === 'no_reranker'
        ? { status: 'skipped', reason: RERANKER_BYPASSED_REASON }
        : ran,
    decision: ran,
    recommendation: ran,
  }
}
