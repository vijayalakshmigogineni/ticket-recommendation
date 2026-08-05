// Hand-written TS interfaces mirroring api/schemas/*.py verbatim. Revisit
// openapi-typescript codegen later to keep these in lockstep automatically --
// not needed for this first pass.

export interface TicketRef {
  id: string
  subject: string
  category: string
  status: string
  customer_name: string
}

export interface CustomerRef {
  id: string
  name: string
  inbox_email: string
}

// --- system ---

export interface DatabaseStatus {
  connected: boolean
  error: string | null
}

export interface OllamaStatus {
  host: string
  reachable: boolean
  error: string | null
}

export interface SystemCounts {
  customers: number
  tickets: number
  interactions: number
  indexed_embeddings: number
}

export interface SystemStatusResponse {
  embedding_model: string
  llm_model: string
  reranker_model: string
  reranker_device: string
  database: DatabaseStatus
  ollama: OllamaStatus
  counts: SystemCounts
}

export interface OllamaConfigOut {
  host: string
  embedding_model: string
  llm_model: string
  request_timeout_s: number
}

export interface RetrievalConfigOut {
  keyword_top_n: number
  ann_top_n: number
  fusion_top_n: number
  rrf_k: number
}

export interface AggregationConfigOut {
  top_m_candidates: number
  top_k_for_avg: number
  weight_max: number
  weight_topk_avg: number
  weight_recency: number
  recency_half_life_days: number
}

export interface ContextBuilderConfigOut {
  neighbors_before: number
  neighbors_after: number
  max_matched_interactions_per_ticket: number
}

export interface RerankerConfigOut {
  model_name: string
  device: string
  top_k: number
}

export interface DecisionConfigOut {
  model: string
  temperature: number
  timeout_s: number
}

export interface ThreadDetectionConfigOut {
  enabled: boolean
}

export interface SystemSettingsResponse {
  ollama: OllamaConfigOut
  embedding_dimension: number
  retrieval: RetrievalConfigOut
  aggregation: AggregationConfigOut
  context_builder: ContextBuilderConfigOut
  reranker: RerankerConfigOut
  decision: DecisionConfigOut
  thread_detection: ThreadDetectionConfigOut
  database_url_display: string
}

export interface IndexInfoResponse {
  index_name: string
  table_name: string
  method: string
  distance_metric: string
  size_bytes: number
  size_pretty: string
  rows_indexed: number
  m: number | null
  ef_construction: number | null
  params_source: 'reloptions' | 'assumed_pgvector_default'
}

// --- customers / tickets ---

export interface CustomerListItem {
  id: string
  name: string
  inbox_email: string
  ticket_count: number
}

export interface CustomerListResponse {
  items: CustomerListItem[]
}

export interface TicketSummary {
  id: string
  customer_id: string
  customer_name: string
  subject: string
  category: string
  status: string
  created_at: string
  closed_at: string | null
  interaction_count: number
}

export interface TicketListResponse {
  items: TicketSummary[]
  total: number
}

// --- interactions ---

export interface InteractionSummary {
  id: string
  ticket_id: string | null
  customer_id: string | null
  interaction_type: string
  sender_email: string
  clean_content_preview: string
  message_id: string
  conversation_id: string | null
  created_at: string
  has_embedding: boolean
  embedding_model: string | null
}

export interface TicketDetailResponse {
  ticket: TicketSummary
  interactions: InteractionSummary[]
}

export interface InteractionListResponse {
  items: InteractionSummary[]
  total: number
}

export interface EmbeddingStats {
  model: string | null
  dimension: number
  norm: number
  min: number
  max: number
  preview_first_20: number[]
}

export interface InteractionDetail {
  id: string
  ticket: TicketRef | null
  customer_id: string | null
  interaction_type: string
  sender_email: string
  raw_content: string
  clean_content: string
  message_id: string
  conversation_id: string | null
  in_reply_to: string | null
  reference_message_ids: string[]
  extra_metadata: Record<string, unknown>
  created_at: string
  embedding_stats: EmbeddingStats | null
}

export interface NeighborHit {
  interaction: InteractionSummary
  ticket: TicketRef | null
  score: number
}

export interface InteractionDetailResponse {
  interaction: InteractionDetail
  nearest_neighbors: NeighborHit[]
}

// --- vector search ---

export interface VectorSearchRequest {
  text: string
  customer_id?: string | null
  top_n?: number
}

export interface VectorSearchHit {
  interaction_id: string
  ticket: TicketRef | null
  score: number
  clean_content_preview: string
}

export interface VectorSearchResponse {
  model: string
  dimension: number
  embedding_time_ms: number
  search_time_ms: number
  total_time_ms: number
  query_vector_preview: number[]
  hits: VectorSearchHit[]
}

// --- evaluation ---

export interface CategoryBreakdown {
  category: string
  clear_correct: number
  clear_total: number
  recall20_correct: number
  recall20_total: number
  recall3_correct: number
  recall3_total: number
  avg_confidence_correct: number | null
}

export interface HardCaseResult {
  key: string
  correct: boolean
  actual_ticket_key: string | null
  confidence: number | null
}

export interface EvalQueryResult {
  key: string
  category: string
  difficulty: string
  expected_ticket_keys: string[] | null
  actual_ticket_key: string | null
  correct: boolean
  recall20: boolean | null
  recall3: boolean | null
  path: string
  confidence: number | null
  explanation: string | null
  elapsed_s: number
}

export interface EvalRunSummary {
  generated_at: string | null
  source_file: string
  total_queries: number
  clear_correct: number
  clear_total: number
  recall20_correct: number
  recall20_total: number
  recall3_correct: number
  recall3_total: number
  hard_correct: number
  hard_total: number
  categories: CategoryBreakdown[]
}

export interface EvalRunDetail extends EvalRunSummary {
  hard_cases: HardCaseResult[]
  failed_clear_keys: string[]
  results: EvalQueryResult[]
}

export interface EvaluationStatusResponse {
  implemented: boolean
  message: string | null
  latest: EvalRunDetail | null
  history: EvalRunSummary[]
}

// --- A/B benchmark (with vs. without the cross-encoder reranker) ---

export interface ABQueryResult extends EvalQueryResult {
  timings_ms: Record<string, number>
  total_time_ms: number
}

export interface ABPipelineRun {
  summary: EvalRunSummary
  results: ABQueryResult[]
}

export interface ABComparisonSummary {
  n_queries: number
  ticket_selection_changed_count: number
  ticket_selection_changed_keys: string[]
  avg_cross_encoder_ms: number
  avg_total_time_s_with_reranker: number
  avg_total_time_s_no_reranker: number
  clear_accuracy_with_reranker: number | null
  clear_accuracy_no_reranker: number | null
  recall3_with_reranker: number | null
  recall3_no_reranker: number | null
  validation_pass_count: number
  validation_total: number
  validation_failures: Record<string, unknown>[]
}

export interface ABBenchmarkResponse {
  implemented: boolean
  message: string | null
  generated_at: string | null
  source_file: string | null
  warmup_performed: boolean | null
  with_reranker: ABPipelineRun | null
  no_reranker: ABPipelineRun | null
  comparison: ABComparisonSummary | null
}

// --- run (traced pipeline) ---

export interface RunRequest {
  subject: string
  body: string
  sender_email: string
  message_id?: string | null
  conversation_id?: string | null
  in_reply_to?: string | null
  reference_message_ids?: string[]
  now?: string | null
}

export interface ScoredInteractionRef {
  interaction_id: string
  ticket: TicketRef | null
  score: number
  preview: string
}

export interface PreprocessingTrace {
  original_subject: string
  original_body: string
  clean_body: string
  embedding_text: string
  time_ms: number
}

export interface ThreadDetectionTrace {
  enabled: boolean
  matched: boolean
  matched_on: string | null
  ticket: TicketRef | null
  matched_interaction_id: string | null
  time_ms: number
}

export interface EmbeddingTrace {
  model: string
  dimension: number
  time_ms: number
  norm: number
  min: number
  max: number
  preview_first_20: number[]
}

export interface KeywordSearchTrace {
  top_n: number
  time_ms: number
  hits: ScoredInteractionRef[]
}

export interface AnnSearchTrace {
  top_n: number
  time_ms: number
  hits: ScoredInteractionRef[]
}

export interface FusedHitOut {
  interaction_id: string
  ticket: TicketRef | null
  preview: string
  fused_score: number
  keyword_score: number | null
  ann_score: number | null
}

export interface FusionTrace {
  rrf_k: number
  fusion_top_n: number
  time_ms: number
  hits: FusedHitOut[]
}

export interface MatchedInteractionOut {
  interaction_id: string
  match_score: number
  preview: string
}

export interface TicketCandidateOut {
  ticket: TicketRef
  max_score: number
  topk_avg: number
  recency_score: number
  final_score: number
  matched_interactions: MatchedInteractionOut[]
}

export interface GroupingTrace {
  time_ms: number
  candidates: TicketCandidateOut[]
}

export interface TicketContextOut {
  ticket: TicketRef
  text: string
  char_count: number
}

export interface ContextBuildingTrace {
  time_ms: number
  contexts: TicketContextOut[]
}

export interface RerankedOut {
  ticket: TicketRef
  rerank_score: number
}

export interface RerankingTrace {
  model_name: string
  time_ms: number
  scores: RerankedOut[]
}

export interface DecisionTrace {
  model: string
  time_ms: number
  system_prompt: string
  user_prompt: string | null
  should_attach: boolean
  ticket: TicketRef | null
  confidence: number
  explanation: string
}

export type PipelinePath = 'unknown_customer' | 'auto_attach' | 'ai_decision'

export type PipelineVariant = 'with_reranker' | 'no_reranker'

export interface RunTraceResponse {
  path: PipelinePath
  total_time_ms: number
  recommended_ticket_id: string | null
  customer: CustomerRef | null
  preprocessing: PreprocessingTrace | null
  thread_detection: ThreadDetectionTrace | null
  embedding: EmbeddingTrace | null
  keyword_search: KeywordSearchTrace | null
  ann_search: AnnSearchTrace | null
  fusion: FusionTrace | null
  grouping: GroupingTrace | null
  context_building: ContextBuildingTrace | null
  reranking: RerankingTrace | null
  decision: DecisionTrace | null
  stage_timings_ms: Record<string, number>
  pipeline_variant: PipelineVariant
}

// --- run compare (experimental: with vs. without the cross-encoder) ---

export interface RunCompareResponse {
  with_reranker: RunTraceResponse
  no_reranker: RunTraceResponse
}

// --- feedback ---

export type ManagerDecision = 'accepted' | 'rejected'

export interface RecordFeedbackRequest {
  customer_id: string
  sender_email: string
  subject: string
  body: string
  should_attach: boolean
  recommended_ticket_id: string | null
  confidence: number
  explanation: string
  manager_decision: ManagerDecision
  corrected_ticket_id?: string | null
  notes?: string | null
}

export interface FeedbackRecord {
  id: string
  customer: CustomerRef
  sender_email: string
  subject: string
  body: string
  should_attach: boolean
  recommended_ticket: TicketRef | null
  confidence: number
  explanation: string
  manager_decision: ManagerDecision
  corrected_ticket: TicketRef | null
  notes: string | null
  created_at: string
}

export interface FeedbackListResponse {
  items: FeedbackRecord[]
  total: number
}
