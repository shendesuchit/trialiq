import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent, PointerEvent as ReactPointerEvent, ReactNode } from "react";
import "./App.css";
import {
  Activity, ArrowRight, BookOpen, CheckCircle2, ChevronDown, ChevronUp, CircleAlert, Copy, Cpu,
  Database, Download, FlaskConical, GitBranch, Info, LayoutDashboard, Mail, Maximize2, Menu, Minimize2, Network,
  RotateCcw, Search, ShieldCheck, Table2, TimerReset, Waypoints, X, ZoomIn, ZoomOut
} from "lucide-react";

type Page = "investigator" | "explorer" | "evidence" | "architecture";
type WorkspaceTab = "evidence" | "graph" | "execution";
type InvestigatorTab = "answer" | "studies" | "connections" | "evidence";
type ApiState = "checking" | "available" | "unavailable";
type RuntimeComponentHealth = {
  healthy?: boolean;
  status?: string;
  latency_ms?: number | null;
  provider?: string | null;
  model?: string | null;
  detail?: string | null;
};
type RuntimeReadiness = {
  status?: string;
  service?: string;
  components?: Record<string, RuntimeComponentHealth>;
};
type ExecutionMode = "baseline" | "agentic";

type TrialQuestionSuggestion = {
  kind: string;
  label: string;
  question: string;
};
type TrialCatalogItem = {
  nct_id: string;
  brief_title?: string | null;
  official_title?: string | null;
  overall_status?: string | null;
  related_trial_count: number;
  related_trial_count_capped?: boolean;
  has_graph_neighbors: boolean;
  relationship_types: string[];
  suggested_questions: TrialQuestionSuggestion[];
};
type TrialCatalogResponse = {
  query: string;
  limit: number;
  offset: number;
  total_count: number;
  has_more: boolean;
  trials: TrialCatalogItem[];
};

type Source = {
  source_table?: string | null;
  source_key?: string | null;
  source_id?: string | number | null;
  source_database?: string | null;
  source_schema?: string | null;
  source_nct_id?: string | null;
};
type Validation = { valid?: boolean; errors?: string[]; warnings?: string[] };
type LineageRecord = {
  collection: string;
  record_index: number;
  nct_id?: string | null;
  source_table?: string | null;
  source_key?: string | null;
  source_id?: string | number | null;
  provenance_version?: string | null;
  pipeline_run_id?: string | null;
  source_database?: string | null;
  source_schema?: string | null;
  source_nct_id?: string | null;
  extracted_at_utc?: string | null;
  transformed_at_utc?: string | null;
  transformation_version?: string | null;
};
type LineageResponse = {
  status?: string;
  nct_id?: string;
  source_count?: number;
  records?: LineageRecord[];
  validation?: Validation;
  limitations?: string[];
};
type AgentValidation = {
  status?: string;
  can_synthesize?: boolean;
  errors?: string[];
  warnings?: string[];
};
type GraphEvidence = {
  found?: boolean; nct_id?: string; trial?: Record<string, unknown> | null;
  conditions?: Record<string, unknown>[]; interventions?: Record<string, unknown>[];
  sponsors?: Record<string, unknown>[]; facilities?: Record<string, unknown>[];
  designs?: Record<string, unknown>[]; eligibilities?: Record<string, unknown>[];
};
type StageTrace = {
  stage?: string;
  status?: string;
  duration_ms?: number;
  details?: Record<string, unknown>;
};
type RelatedTrialPathEvidence = {
  source_nct_id?: string;
  relationship_type?: string;
  entity?: Record<string, unknown>;
  entity_id?: string | null;
};
type RelatedTrialMetrics = {
  shared_condition_count?: number;
  shared_intervention_count?: number;
  shared_sponsor_count?: number;
  total_shared_entity_count?: number;
  evidence_path_count?: number;
  entity_ids?: string[];
  start_date_difference_days?: number | null;
  start_date_comparison?: string | null;
  completion_date_difference_days?: number | null;
  completion_date_comparison?: string | null;
  anchor_duration_days?: number | null;
  related_duration_days?: number | null;
  duration_difference_days?: number | null;
  duration_comparison?: string | null;
  anchor_enrollment?: number | null;
  related_enrollment?: number | null;
  enrollment_difference?: number | null;
  enrollment_comparison?: string | null;
};
type RelatedTrialMatch = {
  nct_id: string;
  trial: Record<string, unknown>;
  discovery_hop: number;
  connected_via: RelatedTrialPathEvidence[];
  metrics?: RelatedTrialMetrics | null;
};
type HumanReviewCandidate = {
  nct_id: string;
  title?: string | null;
  overall_status?: string | null;
  phase?: string | null;
  enrollment?: number | null;
  connection_types?: string[];
  shared_entities?: string[];
  evidence_path_count?: number;
  discovery_hop?: number;
  suggested?: boolean;
};
type HumanReviewCheckpoint = {
  checkpoint_id: string;
  required: boolean;
  threshold: number;
  candidate_count: number;
  suggested_nct_ids?: string[];
  allow_select_all?: boolean;
  candidates: HumanReviewCandidate[];
};
type HumanReviewSelectionMode = "SELECTED" | "ALL";
type HumanReviewSelection = {
  checkpoint_id: string;
  mode: HumanReviewSelectionMode;
  selected_nct_ids: string[];
};
type HumanReviewDecision = {
  checkpoint_id: string;
  mode: HumanReviewSelectionMode;
  threshold: number;
  discovered_candidate_count: number;
  selected_candidate_count: number;
  selected_nct_ids: string[];
};
type ReportSection = "ANSWER" | "STUDIES" | "CONNECTIONS" | "EVIDENCE" | "TECHNICAL_DETAILS";
type RelatedTrialAggregateMetrics = {
  related_trial_count?: number;
  unique_shared_entity_count?: number;
  evidence_path_count?: number;
  condition_linked_trial_count?: number;
  intervention_linked_trial_count?: number;
  sponsor_linked_trial_count?: number;
  multi_factor_trial_count?: number;
  completion_comparable_trial_count?: number;
  duration_comparable_trial_count?: number;
  enrollment_comparable_trial_count?: number;
};
type RelatedTrialResponse = {
  status?: string;
  seed_nct_id?: string;
  anchor_trial?: Record<string, unknown> | null;
  max_hops?: number;
  per_hop_limit?: number;
  limit?: number;
  relationship_types?: string[];
  overall_statuses?: string[];
  matches?: RelatedTrialMatch[];
  metrics?: RelatedTrialAggregateMetrics;
  validation?: Validation;
};
type GraphRelationship = "HAS_CONDITION" | "HAS_INTERVENTION" | "SPONSORED_BY";
type GraphNodeType = "trial" | "condition" | "intervention" | "sponsor";
type GraphViewNode = {
  id: string;
  type: GraphNodeType;
  label: string;
  hop: number;
  metadata?: Record<string, unknown>;
  provenance_keys?: string[];
};
type GraphViewEdge = {
  id: string;
  source: string;
  target: string;
  relationship: GraphRelationship;
  hop: number;
  evidence_keys?: string[];
};
type GraphViewResponse = {
  status?: string;
  seed_node?: string | null;
  nodes?: GraphViewNode[];
  edges?: GraphViewEdge[];
  max_hops?: number;
  per_hop_limit?: number;
  limit?: number;
  match_count?: number;
  truncated?: boolean;
  related_status?: string | null;
  validation?: Validation;
  limitations?: string[];
};
type GraphSelection = { kind: "node"; id: string } | { kind: "edge"; id: string } | null;
type GraphFilter = "ALL" | GraphRelationship;
type GraphDisplayMode = "network" | "table";
type GraphConnectionRow = {
  studyId: string;
  studyLabel: string;
  whyConnected: string;
  sharedEntity: string;
  depth: number;
  depthLabel: string;
  pathNodeIds: string[];
  pathEdgeIds: string[];
};
type GroundedAnswer = {
  status?: string;
  question?: string;
  answer?: string;
  limitations?: string[];
  sources?: Source[];
  graph_response?: { status?: string; nct_id?: string; evidence?: GraphEvidence; validation?: Validation } | null;
  condition_search_response?: unknown;
  entity_search_response?: unknown;
  shared_entity_response?: unknown;
  related_trial_response?: RelatedTrialResponse | null;
};
type RetrievalResult = {
  status?: string;
  tool_name?: string;
  transport?: string;
  errors?: string[];
  warnings?: string[];
  graph_response?: GroundedAnswer["graph_response"];
  condition_search_response?: unknown;
  entity_search_response?: unknown;
  shared_entity_response?: unknown;
  related_trial_response?: RelatedTrialResponse | null;
};
type GenerationMetadata = {
  method?: "LLM" | "DETERMINISTIC";
  grounded?: boolean;
  provider?: string | null;
  model?: string | null;
  source_count?: number;
  attempted_providers?: string[];
  failover_reason?: string | null;
  error_category?: string | null;
  latency_ms?: number | null;
  degraded?: boolean;
  grounding_errors?: string[];
  rejected_claim_count?: number;
};
type StructuredFinding = {
  statement: string;
  evidence_ids: string[];
};
type StructuredSynthesis = {
  headline: string;
  summary: string;
  key_findings: StructuredFinding[];
};
type AgentRunResult = {
  run_id?: string;
  status?: string;
  answer: GroundedAnswer;
  retrieval?: RetrievalResult;
  validation?: AgentValidation;
  generation?: GenerationMetadata | null;
  structured_synthesis?: StructuredSynthesis | null;
  human_review_decision?: HumanReviewDecision | null;
  trace?: StageTrace[];
};
type AgentHumanReviewRun = {
  run_id: string;
  status: "REVIEW_REQUIRED";
  retrieval: RetrievalResult;
  human_review: HumanReviewCheckpoint;
  trace?: StageTrace[];
};
type AgentQueryResponse = AgentRunResult | AgentHumanReviewRun;
type UiResult = GroundedAnswer & {
  execution_mode?: ExecutionMode;
  run_id?: string;
  run_status?: string;
  retrieval?: RetrievalResult;
  agent_validation?: AgentValidation;
  generation?: GenerationMetadata | null;
  structured_synthesis?: StructuredSynthesis | null;
  human_review_decision?: HumanReviewDecision | null;
  trace?: StageTrace[];
  [key: string]: unknown;
};

const API_BASE_URL = "http://127.0.0.1:8000";
const collections = ["conditions", "interventions", "sponsors", "facilities", "designs", "eligibilities"] as const;

const primaryNavItems = [
  { id: "investigator" as Page, label: "Investigator", description: "Ask clinical trial questions", icon: LayoutDashboard },
  { id: "explorer" as Page, label: "Study lookup", description: "Open one study record", icon: FlaskConical },
  { id: "evidence" as Page, label: "Evidence review", description: "Sources, connections & workflow", icon: ShieldCheck },
];
const technicalNavItems = [
  { id: "architecture" as Page, label: "System details", description: "Architecture & runtime", icon: Waypoints },
];
const navItems = [...primaryNavItems, ...technicalNavItems];

function text(value: unknown, fallback = "Not available") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}
function normalizeNctId(value: string) { return value.trim().toUpperCase(); }
function collectionLabel(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, " ");
}
function getEvidence(result: UiResult | null): GraphEvidence | undefined {
  return result?.graph_response?.evidence;
}
function getValidation(result: UiResult | null): Validation {
  const candidate = result?.graph_response?.validation;
  if (candidate && typeof candidate === "object") {
    return {
      valid: "valid" in candidate ? Boolean(candidate.valid) : undefined,
      errors: Array.isArray(candidate.errors) ? candidate.errors.map(String) : [],
      warnings: Array.isArray(candidate.warnings) ? candidate.warnings.map(String) : [],
    };
  }
  return { errors: [], warnings: [] };
}
function getTrace(result: UiResult | null): StageTrace[] {
  const trace = result?.trace;
  return Array.isArray(trace) ? trace : [];
}
function getTransport(result: UiResult | null) {
  return result?.retrieval?.transport ?? "Not reported";
}
function getToolName(result: UiResult | null) {
  return result?.retrieval?.tool_name ?? "Not reported";
}
function getRelatedTrialResponse(result: UiResult | null): RelatedTrialResponse | null {
  return result?.related_trial_response ?? result?.retrieval?.related_trial_response ?? null;
}
function isHumanReviewRun(payload: AgentQueryResponse): payload is AgentHumanReviewRun {
  return payload.status === "REVIEW_REQUIRED" && "human_review" in payload;
}
function humanStatusLabel(value: string | null | undefined) {
  if (!value) return "Not reported";
  return value.split("_").map((part) => part.charAt(0) + part.slice(1).toLowerCase()).join(" ");
}
function clinicalStatusClass(value: string | null | undefined) {
  const status = (value ?? "").toUpperCase();
  if (status === "COMPLETED") return "clinical-status-completed";
  if (["RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"].includes(status)) return "clinical-status-active";
  if (["TERMINATED", "WITHDRAWN", "SUSPENDED"].includes(status)) return "clinical-status-stopped";
  return "clinical-status-neutral";
}
function formatDuration(durationMs: number | undefined) {
  if (durationMs === undefined || !Number.isFinite(durationMs)) return "Not reported";
  return durationMs >= 1000 ? `${(durationMs / 1000).toFixed(2)} s` : `${durationMs.toFixed(2)} ms`;
}
const TRACE_DETAIL_LABELS: Record<string, string> = {
  intent: "Intent",
  source: "Source",
  provider: "Provider",
  model: "Model",
  anchor_nct_id: "Study of interest",
  relationship_types: "Relationships",
  overall_statuses: "Status filters",
  tool_name: "Tool",
  transport: "Transport",
  match_count: "Matches",
  related_trial_count: "Related trials",
  shared_entity_count: "Shared entities",
  evidence_path_count: "Evidence paths",
  comparison_metric_count: "Comparisons",
  can_synthesize: "Can synthesize",
  warning_count: "Warnings",
  error_count: "Errors",
  source_count: "Sources",
  limitation_count: "Data notes",
  generation_method: "Method",
  generation_provider: "Provider",
  generation_model: "Model",
  generation_degraded: "Degraded",
  attempted_providers: "Attempted providers",
  failover_reason: "Failover reason",
  error_category: "Error category",
  llm_latency_ms: "LLM latency",
  validated_claim_count: "Validated findings",
  rejected_claim_count: "Rejected findings",
  grounding_error_count: "Grounding errors",
  grounding_errors: "Grounding validation",
};
function traceDetailEntries(stage: StageTrace): Array<[string, string]> {
  const details = stage.details ?? {};
  return Object.entries(TRACE_DETAIL_LABELS).flatMap(([key, label]) => {
    const value = details[key];
    if (value === null || value === undefined || value === "") return [];
    if (key === "llm_latency_ms" && typeof value === "number") return [[label, formatDuration(value)]];
    if (typeof value === "boolean") return [[label, value ? "Yes" : "No"]];
    if (typeof value === "string" || typeof value === "number") return [[label, String(value)]];
    return [];
  });
}
function renderInlineMarkdown(value: string): ReactNode[] {
  return value.split(/(\*\*[^*]+\*\*)/g).map((part, index) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={index}>{part.slice(2, -2)}</strong>
      : <span key={index}>{part}</span>
  );
}
function MarkdownAnswer({ content }: { content: string }) {
  const blocks: ReactNode[] = [];
  let items: string[] = [];
  const flush = () => {
    if (!items.length) return;
    blocks.push(<ul className="answer-list" key={`list-${blocks.length}`}>{items.map((item, i) => <li key={i}>{renderInlineMarkdown(item)}</li>)}</ul>);
    items = [];
  };
  content.replace(/\r\n/g, "\n").split("\n").forEach((line, index) => {
    const value = line.trim();
    const bullet = value.match(/^[-*]\s+(.*)$/);
    const heading = value.match(/^#{1,3}\s+(.*)$/);
    if (bullet) { items.push(bullet[1]); return; }
    flush();
    if (!value) return;
    if (heading) blocks.push(<h4 className="answer-heading" key={index}>{renderInlineMarkdown(heading[1])}</h4>);
    else blocks.push(<p className="answer-paragraph" key={index}>{renderInlineMarkdown(value)}</p>);
  });
  flush();
  return <div className="markdown-answer">{blocks}</div>;
}

function RuntimeHealthIcon({
  label,
  icon,
  component,
  state,
  showModel = false,
}: {
  label: string;
  icon: ReactNode;
  component?: RuntimeComponentHealth;
  state?: ApiState;
  showModel?: boolean;
}) {
  const checking = state === "checking";
  const healthy = component?.healthy === true || (label === "API" && state === "available");
  const unavailable = component?.healthy === false || state === "unavailable";
  const statusClass = checking ? "checking" : healthy ? "healthy" : unavailable ? "unavailable" : "unknown";
  const detail = showModel && healthy
    ? [component?.provider, component?.model].filter(Boolean).join(" · ") || "Provider ready"
    : checking ? "Checking startup status" : healthy ? "Healthy" : unavailable ? component?.detail || "Unavailable" : "Not reported";
  const accessibleLabel = `${label}: ${detail}`;

  return <div className={`runtime-health-icon health-${statusClass}`} tabIndex={0} aria-label={accessibleLabel}>
    <span className="runtime-health-glyph">{icon}</span>
    <span className="runtime-health-indicator"/>
    <div className="runtime-health-tooltip" role="tooltip"><strong>{label}</strong><span>{detail}</span></div>
  </div>;
}

function CompactModeSelector({ mode, onChange, disabled }: { mode: ExecutionMode; onChange: (mode: ExecutionMode) => void; disabled: boolean }) {
  return <div className="compact-mode-selector" role="group" aria-label="Investigation approach">
    <button type="button" className={mode === "agentic" ? "active" : ""} aria-pressed={mode === "agentic"} disabled={disabled} onClick={() => onChange("agentic")} title="Guided investigation coordinates TrialIQ's evidence search, comparison, checks, and summary steps.">Guided</button>
    <button type="button" className={mode === "baseline" ? "active" : ""} aria-pressed={mode === "baseline"} disabled={disabled} onClick={() => onChange("baseline")} title="Direct query uses TrialIQ's standard deterministic query path.">Direct</button>
  </div>;
}

function ClinicalStudySelector({
  trials, search, onSearch, selected, onSelect, onClearSelection, onQuestion, catalogLoading, catalogError,
}: {
  trials: TrialCatalogItem[];
  search: string;
  onSearch: (value: string) => void;
  selected: TrialCatalogItem | null;
  onSelect: (nctId: string) => void;
  onClearSelection: () => void;
  onQuestion: (question: string) => void;
  catalogLoading: boolean;
  catalogError: string;
}) {
  const normalizedSearch = search.trim().toUpperCase();
  const rankedTrials = [...trials].sort((left, right) => {
    const leftNct = left.nct_id.toUpperCase();
    const rightNct = right.nct_id.toUpperCase();
    const leftRank = normalizedSearch && leftNct === normalizedSearch ? 0 : normalizedSearch && leftNct.startsWith(normalizedSearch) ? 1 : 2;
    const rightRank = normalizedSearch && rightNct === normalizedSearch ? 0 : normalizedSearch && rightNct.startsWith(normalizedSearch) ? 1 : 2;
    return leftRank - rightRank || left.nct_id.localeCompare(right.nct_id);
  });
  const suggestedTrials = rankedTrials.filter((trial) => trial.has_graph_neighbors).slice(0, 4);
  const displayedTrials = normalizedSearch ? rankedTrials.slice(0, 8) : (suggestedTrials.length ? suggestedTrials : rankedTrials.slice(0, 4));
  const exactMatch = normalizedSearch ? rankedTrials.find((trial) => trial.nct_id.toUpperCase() === normalizedSearch) : undefined;
  const title = selected?.brief_title || selected?.official_title || "Selected study";
  const questions = selected?.suggested_questions ?? [];
  const selectTrial = (nctId: string) => {
    onSelect(nctId);
    onSearch("");
  };

  return <div className="clinical-study-selector">
    {selected ? <>
      <div className="clinical-study-summary clinical-study-summary-selected">
        <div>
          <span>Study of interest</span>
          <strong>{selected.nct_id}</strong>
          <p title={title}>{title}</p>
        </div>
        <div className="clinical-study-summary-actions">
          <div className="clinical-study-tags">
            {selected.overall_status && <span>{selected.overall_status}</span>}
            <span>{selected.has_graph_neighbors ? `${selected.related_trial_count}${selected.related_trial_count_capped ? "+" : ""} connected stud${selected.related_trial_count === 1 && !selected.related_trial_count_capped ? "y" : "ies"}` : "No connected studies loaded"}</span>
          </div>
          <button type="button" className="clinical-change-study" onClick={onClearSelection}>Change study</button>
        </div>
      </div>
      {!!questions.length && <div className="clinical-question-prompts"><span>Suggested questions</span><div>{questions.slice(0, 3).map((item) => <button type="button" key={item.kind} onClick={() => onQuestion(item.question)} title={item.question}>{item.label}</button>)}</div></div>}
    </> : <>
      <label className="clinical-study-search clinical-study-search-single"><Search size={15}/><span className="sr-only">Search loaded studies</span><input
        value={search}
        onChange={(event) => onSearch(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && exactMatch) {
            event.preventDefault();
            selectTrial(exactMatch.nct_id);
          }
        }}
        placeholder="Search by NCT ID or study title"
        autoComplete="off"
      /></label>
      <div className="clinical-study-results" aria-live="polite">
        <div className="clinical-study-results-heading"><span>{normalizedSearch ? "Matching studies" : "Suggested studies"}</span>{catalogLoading && <small>Searching…</small>}</div>
        {!catalogLoading && !displayedTrials.length ? <div className="clinical-study-no-results">{normalizedSearch ? "No loaded studies match this search." : "No suggested studies are available."}</div> :
          <div className="clinical-study-result-list">{displayedTrials.map((trial) => <button type="button" key={trial.nct_id} className="clinical-study-result" onClick={() => selectTrial(trial.nct_id)}>
            <span className="clinical-study-result-id">{trial.nct_id}</span>
            <span className="clinical-study-result-title">{trial.brief_title || trial.official_title || "Untitled study"}</span>
            <span className="clinical-study-result-meta">{[trial.overall_status, trial.has_graph_neighbors ? `${trial.related_trial_count}${trial.related_trial_count_capped ? "+" : ""} connected studies` : null].filter(Boolean).join(" · ")}</span>
          </button>)}</div>}
      </div>
    </>}
    {catalogError && <div className="clinical-study-error">{catalogError}</div>}
  </div>;
}

function QuerySummaryStrip({ question, anchorNctId, mode, loading, onEdit, onRunAgain }: { question: string; anchorNctId?: string | null; mode: ExecutionMode; loading: boolean; onEdit: () => void; onRunAgain: () => void }) {
  return <div className="query-summary-strip">
    <div className="query-summary-copy">
      <div className="query-summary-meta"><span>{anchorNctId ? `Study of interest · ${anchorNctId}` : "Clinical trial investigation"}</span><span>·</span><strong>{mode === "agentic" ? "Guided investigation" : "Direct query"}</strong></div>
      <p title={question}>{question}</p>
    </div>
    <div className="query-summary-actions"><button type="button" onClick={onEdit}>Edit question</button><button type="button" className="primary-button compact-run" disabled={loading} onClick={onRunAgain}>{loading ? "Running…" : "Run again"}</button></div>
  </div>;
}

function HumanReviewModal({ run, question, continuing, error, onEdit, onContinue }: {
  run: AgentHumanReviewRun;
  question: string;
  continuing: boolean;
  error: string;
  onEdit: () => void;
  onContinue: (selection: HumanReviewSelection) => void;
}) {
  const checkpoint = run.human_review;
  const suggestedIds = checkpoint.suggested_nct_ids?.length
    ? checkpoint.suggested_nct_ids
    : checkpoint.candidates.filter((candidate) => candidate.suggested).map((candidate) => candidate.nct_id);
  const [selectedIds, setSelectedIds] = useState<string[]>(suggestedIds);
  const [candidateSearch, setCandidateSearch] = useState("");
  const selectAllRef = useRef<HTMLInputElement>(null);
  const normalizedSearch = candidateSearch.trim().toLowerCase();
  const visibleCandidates = normalizedSearch
    ? checkpoint.candidates.filter((candidate) => [
        candidate.nct_id, candidate.title, candidate.overall_status, candidate.phase,
        ...(candidate.connection_types ?? []), ...(candidate.shared_entities ?? []),
      ].filter(Boolean).some((value) => String(value).toLowerCase().includes(normalizedSearch)))
    : checkpoint.candidates;
  const visibleIds = visibleCandidates.map((candidate) => candidate.nct_id);
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((nctId) => selectedIds.includes(nctId));
  const someVisibleSelected = visibleIds.some((nctId) => selectedIds.includes(nctId)) && !allVisibleSelected;

  useEffect(() => {
    setSelectedIds(suggestedIds);
    setCandidateSearch("");
  }, [checkpoint.checkpoint_id]);

  useEffect(() => {
    if (selectAllRef.current) selectAllRef.current.indeterminate = someVisibleSelected;
  }, [someVisibleSelected]);

  useEffect(() => {
    document.body.classList.add("trialiq-modal-open");
    return () => document.body.classList.remove("trialiq-modal-open");
  }, []);

  const toggleCandidate = (nctId: string) => {
    setSelectedIds((current) => current.includes(nctId) ? current.filter((item) => item !== nctId) : [...current, nctId]);
  };
  const toggleVisible = () => setSelectedIds((current) => {
    if (allVisibleSelected) return current.filter((nctId) => !visibleIds.includes(nctId));
    return Array.from(new Set([...current, ...visibleIds]));
  });
  const selectedContract: HumanReviewSelection | null = selectedIds.length ? {
    checkpoint_id: checkpoint.checkpoint_id,
    mode: "SELECTED",
    selected_nct_ids: selectedIds,
  } : null;
  const allContract: HumanReviewSelection = {
    checkpoint_id: checkpoint.checkpoint_id,
    mode: "ALL",
    selected_nct_ids: [],
  };
  const friendlyConnection = (value: string) => value === "HAS_CONDITION" ? "Condition" : value === "HAS_INTERVENTION" ? "Intervention" : value === "SPONSORED_BY" ? "Sponsor" : value;

  return <div className="trialiq-modal-backdrop hitl-modal-backdrop" role="presentation">
    <section className="trialiq-modal hitl-review-panel" role="dialog" aria-modal="true" aria-labelledby="hitl-review-title">
      <header className="trialiq-modal-header hitl-review-heading">
        <div><span aria-label="Investigator checkpoint">Investigator input required</span><h2 id="hitl-review-title">Choose the studies to investigate in detail</h2><p>TrialIQ found a broad result set and paused before detailed analysis. Your selection defines the evidence set used for comparison, validation and the final answer.</p></div>
        <button type="button" className="icon-button modal-close-button" onClick={onEdit} disabled={continuing} aria-label="Return to the question"><X size={18}/></button>
      </header>
      <div className="hitl-progress" aria-label="Investigation progress">
        <span className="complete"><CheckCircle2 size={14}/> Question understood</span>
        <span className="complete"><CheckCircle2 size={14}/> Candidates discovered</span>
        <span className="current">3 Investigator review</span>
        <span>4 Detailed analysis</span>
        <span>5 Answer</span>
      </div>
      <div className="trialiq-modal-body hitl-modal-body">
        <div className="hitl-question-context"><span>Investigation</span><p>{question}</p></div>
        <div className="hitl-review-summary">
          <div><strong>{checkpoint.candidate_count}</strong><span>candidate studies discovered</span></div>
          <div><strong>{checkpoint.threshold}</strong><span>automatic-analysis threshold</span></div>
          <div><strong>{selectedIds.length}</strong><span>currently selected</span></div>
        </div>
        <div className="hitl-selection-toolbar">
          <label className="hitl-select-all"><input ref={selectAllRef} type="checkbox" checked={allVisibleSelected} onChange={toggleVisible} disabled={continuing || !visibleIds.length}/><span><strong>Select all shown studies</strong><small>{visibleIds.length === checkpoint.candidate_count ? `${checkpoint.candidate_count} candidates shown` : `${visibleIds.length} filtered candidates shown`}</small></span></label>
          <label className="hitl-candidate-search"><Search size={14}/><input value={candidateSearch} onChange={(event) => setCandidateSearch(event.target.value)} placeholder="Search candidates" disabled={continuing}/></label>
          {!!suggestedIds.length && <button type="button" className="secondary-button" disabled={continuing} onClick={() => setSelectedIds(suggestedIds)}>Use suggested {suggestedIds.length}</button>}
        </div>
        <div className="comparison-table-wrap hitl-candidate-table-wrap">
          <table className="comparison-table hitl-candidate-table">
            <thead><tr><th className="compare-select-column">Include</th><th>Study</th><th>Why connected</th><th>Status</th><th>Phase</th><th className="numeric-column">Enrollment</th></tr></thead>
            <tbody>{visibleCandidates.map((candidate) => {
              const selected = selectedIds.includes(candidate.nct_id);
              const whyConnected = [
                ...(candidate.connection_types ?? []).map(friendlyConnection),
                ...(candidate.shared_entities ?? []).slice(0, 2),
              ].filter(Boolean).join(" · ") || "Related evidence candidate";
              return <tr key={candidate.nct_id} className={selected ? "comparison-row-selected" : ""}>
                <td className="compare-select-cell"><input type="checkbox" checked={selected} disabled={continuing} aria-label={`Include ${candidate.nct_id} in detailed investigation`} onChange={() => toggleCandidate(candidate.nct_id)}/></td>
                <td><strong>{candidate.nct_id}</strong><span>{candidate.title || "Title not reported"}</span>{candidate.suggested && <small className="hitl-suggested-label">Suggested by TrialIQ</small>}</td>
                <td>{whyConnected}<span>{candidate.discovery_hop === 2 ? "2-step connection" : "Direct connection"}{candidate.evidence_path_count ? ` · ${candidate.evidence_path_count} supporting link${candidate.evidence_path_count === 1 ? "" : "s"}` : ""}</span></td>
                <td><span className={`clinical-status ${clinicalStatusClass(candidate.overall_status)}`}>{humanStatusLabel(candidate.overall_status)}</span></td>
                <td>{candidate.phase || "Not reported"}</td>
                <td className="numeric-column">{candidate.enrollment === null || candidate.enrollment === undefined ? "—" : candidate.enrollment.toLocaleString()}</td>
              </tr>;
            })}</tbody>
          </table>
          {!visibleCandidates.length && <div className="hitl-empty-filter"><Search size={18}/><strong>No candidates match this filter.</strong><span>Clear the search to review all discovered studies.</span></div>}
        </div>
        {error && <div className="graph-error" role="alert"><CircleAlert size={17}/><span>{error}</span></div>}
      </div>
      <footer className="trialiq-modal-footer hitl-review-actions">
        <div><strong>{selectedIds.length ? `${selectedIds.length} stud${selectedIds.length === 1 ? "y" : "ies"} ready for detailed analysis` : "No studies individually selected"}</strong><span>{selectedIds.length ? "Only the investigator-approved evidence set will drive Analyse selected." : "Analyse all remains available if you want the complete discovered set."}</span></div>
        <div>
          <button type="button" className="secondary-button" disabled={continuing || !selectedContract} onClick={() => selectedContract && onContinue(selectedContract)}>{continuing ? "Continuing…" : "Analyse selected"}</button>
          {checkpoint.allow_select_all !== false && <button type="button" className="primary-button" disabled={continuing} onClick={() => onContinue(allContract)}>{continuing ? "Continuing…" : "Analyse all"}</button>}
        </div>
      </footer>
    </section>
  </div>;
}

export default function App() {
  const [page, setPage] = useState<Page>("investigator");
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("evidence");
  const [investigatorTab, setInvestigatorTab] = useState<InvestigatorTab>("answer");
  const [queryExpanded, setQueryExpanded] = useState(true);
  const [lastSubmittedQuestion, setLastSubmittedQuestion] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [nctId, setNctId] = useState("");
  const [result, setResult] = useState<UiResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState("");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [runtimeReadiness, setRuntimeReadiness] = useState<RuntimeReadiness | null>(null);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("agentic");
  const [trialCatalog, setTrialCatalog] = useState<TrialCatalogItem[]>([]);
  const [catalogSearch, setCatalogSearch] = useState("");
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [selectedCatalogTrial, setSelectedCatalogTrial] = useState<TrialCatalogItem | null>(null);
  const [pendingHumanReview, setPendingHumanReview] = useState<AgentHumanReviewRun | null>(null);

  useEffect(() => {
    let active = true;
    async function refreshReadiness() {
      try {
        const response = await fetch(`${API_BASE_URL}/ready`);
        const payload = await response.json().catch(() => ({})) as RuntimeReadiness;
        if (!active) return;
        setRuntimeReadiness(payload);
        setApiState(payload.components?.api?.healthy === false ? "unavailable" : "available");
      } catch {
        if (!active) return;
        setRuntimeReadiness(null);
        setApiState("unavailable");
      }
    }
    void refreshReadiness();
    const interval = window.setInterval(() => void refreshReadiness(), 30000);
    return () => { active = false; window.clearInterval(interval); };
  }, []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setCatalogLoading(true);
      setCatalogError("");
      const params = new URLSearchParams({ limit: "100", offset: "0" });
      if (catalogSearch.trim()) params.set("query", catalogSearch.trim());

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/trials/catalog?${params.toString()}`, {
          signal: controller.signal,
        });
        const payload = await response.json().catch(() => ({})) as Partial<TrialCatalogResponse> & { detail?: unknown };
        if (!response.ok) {
          throw new Error(typeof payload.detail === "string" ? payload.detail : "The loaded-trial catalog could not be retrieved.");
        }
        if (!active) return;

        const trials = Array.isArray(payload.trials) ? payload.trials : [];
        setTrialCatalog(trials);
      } catch (error) {
        if (!active || (error instanceof DOMException && error.name === "AbortError")) return;
        setCatalogError(error instanceof Error ? error.message : "The loaded-trial catalog could not be retrieved.");
        setTrialCatalog([]);
      } finally {
        if (active) setCatalogLoading(false);
      }
    }, 250);

    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [catalogSearch]);

  useEffect(() => {
    if (!loading) { setElapsedSeconds(0); return; }
    const started = Date.now();
    const id = window.setInterval(() => setElapsedSeconds(Math.floor((Date.now() - started) / 1000)), 250);
    return () => window.clearInterval(id);
  }, [loading]);

  const evidence = getEvidence(result);
  const trial = evidence?.trial ?? null;
  const summary = useMemo(() => [
    ["Study status", text(trial?.overall_status)],
    ["Study type", text(trial?.study_type)],
    ["Phase", text(trial?.phase)],
    ["Enrollment", text(trial?.enrollment)],
  ], [trial]);
  const activeRelatedResponse = getRelatedTrialResponse(result);
  const activeAnchorNctId = activeRelatedResponse?.seed_nct_id ?? null;

  async function parseResponse(response: Response) {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = payload?.detail;
      throw new Error(typeof detail === "string" ? detail : detail?.answer ?? detail?.message ?? "The TrialIQ API request failed.");
    }
    return payload;
  }

  function presentAgentRunResult(payload: AgentRunResult, submittedQuestion: string) {
    setPendingHumanReview(null);
    const relatedResponse = payload.answer.related_trial_response;
    const anchorNctId = relatedResponse?.seed_nct_id;
    if (anchorNctId) {
      const catalogMatch = trialCatalog.find((trial) => trial.nct_id === anchorNctId);
      const anchorTrial = relatedResponse?.anchor_trial ?? {};
      const alignedTrial: TrialCatalogItem = catalogMatch ?? {
        nct_id: anchorNctId,
        brief_title: typeof anchorTrial.brief_title === "string" ? anchorTrial.brief_title : null,
        official_title: typeof anchorTrial.official_title === "string" ? anchorTrial.official_title : null,
        overall_status: typeof anchorTrial.overall_status === "string" ? anchorTrial.overall_status : null,
        related_trial_count: relatedResponse?.matches?.length ?? 0,
        has_graph_neighbors: Boolean(relatedResponse?.matches?.length),
        relationship_types: relatedResponse?.relationship_types ?? [],
        suggested_questions: [
          { kind: "related", label: "Find related studies", question: `Find studies related to ${anchorNctId} and explain the evidence connecting them.` },
          { kind: "evidence", label: "Show supporting evidence", question: `Show the supporting evidence for ${anchorNctId} and its connected studies.` },
        ],
      };
      setSelectedCatalogTrial(alignedTrial);
      setNctId(anchorNctId);
    }
    setResult({
      ...payload.answer,
      execution_mode: "agentic",
      question: text(payload.answer.question, submittedQuestion),
      run_id: payload.run_id,
      run_status: payload.status,
      retrieval: payload.retrieval,
      agent_validation: payload.validation,
      generation: payload.generation,
      structured_synthesis: payload.structured_synthesis,
      human_review_decision: payload.human_review_decision,
      trace: payload.trace ?? [],
    });
    setLastSubmittedQuestion(submittedQuestion);
    setInvestigatorTab("answer");
    setQueryExpanded(false);
  }

  async function requestAgent() {
    setApiError(""); setLoading(true);
    try {
      const submittedQuestion = question.trim();
      const response = await fetch(`${API_BASE_URL}/api/v1/query/agent`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: submittedQuestion, limit: 20 }),
      });
      const payload = await parseResponse(response) as AgentQueryResponse;
      if (isHumanReviewRun(payload)) {
        setPendingHumanReview(payload);
        setResult(null);
        setLastSubmittedQuestion(submittedQuestion);
        setQueryExpanded(false);
        setInvestigatorTab("answer");
        return;
      }
      presentAgentRunResult(payload, submittedQuestion);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "The agent request failed.");
    } finally { setLoading(false); }
  }

  async function continueHumanReview(selection: HumanReviewSelection) {
    if (!pendingHumanReview) return;
    setApiError(""); setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/query/agent/continue`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: pendingHumanReview.run_id, selection }),
      });
      const payload = await parseResponse(response) as AgentRunResult;
      if (!payload.answer) throw new Error("The continued investigation did not return a grounded answer.");
      presentAgentRunResult(payload, lastSubmittedQuestion || question.trim());
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "The paused investigation could not be resumed.");
    } finally { setLoading(false); }
  }

  async function requestBaseline() {
    setApiError(""); setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/query`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim(), mode: "standard", limit: 20 }),
      });
      const payload = await parseResponse(response) as GroundedAnswer;
      setPendingHumanReview(null);
      setResult({
        ...payload,
        execution_mode: "baseline",
        question: text(payload.question, question),
        run_id: response.headers.get("X-TrialIQ-Run-ID") ?? undefined,
        run_status: payload.status,
        trace: [],
      });
      setLastSubmittedQuestion(question.trim());
      setInvestigatorTab("answer");
      setQueryExpanded(false);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "The baseline request failed.");
    } finally { setLoading(false); }
  }

  async function requestOverview(id: string) {
    const normalized = normalizeNctId(id);
    setApiError(""); setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/trials/overview`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nct_id: normalized }),
      });
      const payload = await parseResponse(response) as GroundedAnswer;
      setPendingHumanReview(null);
      setResult({ ...payload, execution_mode: "baseline", question: text(payload.question, `Give me an overview of ${normalized}`) });
      setNctId(normalized);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "The overview request failed.");
    } finally { setLoading(false); }
  }

  function handleQuestionSubmit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) { setApiError("Enter an investigator question."); return; }
    if (executionMode === "agentic") void requestAgent();
    else void requestBaseline();
  }
  function changeExecutionMode(nextMode: ExecutionMode) {
    if (nextMode === executionMode || loading) return;
    setExecutionMode(nextMode);
    setPendingHumanReview(null);
    setResult(null);
    setApiError("");
    setWorkspaceTab("evidence");
    setInvestigatorTab("answer");
    setQueryExpanded(true);
  }
  function handleNctSubmit(event: FormEvent) {
    event.preventDefault();
    if (!/^NCT\d+$/i.test(nctId.trim())) { setApiError("NCT ID must start with NCT and contain digits after it."); return; }
    void requestOverview(nctId);
  }
  function handleCatalogTrialSelect(selectedNctId: string) {
    const selected = trialCatalog.find((trial) => trial.nct_id === selectedNctId)
      ?? (selectedCatalogTrial?.nct_id === selectedNctId ? selectedCatalogTrial : null);
    if (!selected) return;
    setSelectedCatalogTrial(selected);
    setCatalogSearch("");
    setNctId(selected.nct_id);
    setQuestion(selected.suggested_questions[0]?.question ?? `Give me an overview of ${selected.nct_id}`);
    setPendingHumanReview(null);
    setResult(null);
    setInvestigatorTab("answer");
    setQueryExpanded(true);
    setApiError("");
  }
  function handleCatalogTrialClear() {
    setSelectedCatalogTrial(null);
    setCatalogSearch("");
    setNctId("");
    setQuestion("");
    setPendingHumanReview(null);
    setResult(null);
    setInvestigatorTab("answer");
    setQueryExpanded(true);
    setApiError("");
  }
  function navigate(next: Page) { setPage(next); setSidebarOpen(false); }

  return <div className="app-frame">
    <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""} ${page === "investigator" ? "sidebar-investigation" : ""}`}>
      <div className="brand-block">
        <div className="brand-mark"><Network size={20}/></div>
        <div><div className="brand-name">TrialIQ</div><div className="brand-caption">Clinical Evidence Workspace · v0.1</div></div>
        <button type="button" className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close navigation"><X size={18}/></button>
      </div>
      <div className="workspace-label">Clinical trial workspace</div>
      <nav className="primary-nav" aria-label="Primary navigation">
        {primaryNavItems.map((item) => {
          const Icon = item.icon;
          return <button type="button" key={item.id} title={item.description} aria-current={page === item.id ? "page" : undefined}
            className={`nav-item ${page === item.id ? "nav-item-active" : ""}`} onClick={() => navigate(item.id)}>
            <Icon size={18}/><span><strong>{item.label}</strong><small>{item.description}</small></span>
          </button>;
        })}
      </nav>
      <details className="technical-nav-group">
        <summary><span>Technical</span><ChevronDown size={14}/></summary>
        <div>{technicalNavItems.map((item) => {
          const Icon = item.icon;
          return <button type="button" key={item.id} title={item.description} aria-current={page === item.id ? "page" : undefined}
            className={`nav-item ${page === item.id ? "nav-item-active" : ""}`} onClick={() => navigate(item.id)}>
            <Icon size={18}/><span><strong>{item.label}</strong><small>{item.description}</small></span>
          </button>;
        })}</div>
      </details>

      <div className="sidebar-bottom">
        <div className="runtime-strip-label"><span>Runtime</span><small>System health</small></div>
        <div className="developer-health-strip" aria-label="Developer runtime status">
          <RuntimeHealthIcon label="API" icon={<Activity size={15}/>} state={apiState} component={runtimeReadiness?.components?.api}/>
          <RuntimeHealthIcon label="Neo4j" icon={<Database size={15}/>} state={apiState === "checking" ? "checking" : undefined} component={runtimeReadiness?.components?.neo4j}/>
          <RuntimeHealthIcon label="MCP" icon={<Network size={15}/>} state={apiState === "checking" ? "checking" : undefined} component={runtimeReadiness?.components?.mcp}/>
          <RuntimeHealthIcon label="LLM" icon={<Cpu size={15}/>} state={apiState === "checking" ? "checking" : undefined} component={runtimeReadiness?.components?.llm} showModel/>
        </div>
        <div className="scope-note compact-scope-note" title="Evidence support tool. Verify clinically consequential conclusions against source records."><ShieldCheck size={15}/><span>Evidence support only</span></div>
      </div>
    </aside>
    {sidebarOpen && <button type="button" className="mobile-scrim" onClick={() => setSidebarOpen(false)} aria-label="Close navigation"/>}

    <main className="main-content">
      <header className="topbar">
        <button type="button" className="icon-button mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={20}/></button>
        <div className="breadcrumbs"><span>TrialIQ</span><span>/</span><strong>{navItems.find((item) => item.id === page)?.label}</strong></div>
        <div className="topbar-meta"><Activity size={14}/><span>Clinical trial evidence</span></div>
      </header>

      <div className={`page-content ${page === "investigator" && result && !queryExpanded ? "investigator-result-page" : ""}`}>
        {page === "investigator" && <>
          {(!result || queryExpanded) ? <>
            <section className="page-heading investigator-heading">
              <div className="eyebrow">CLINICAL TRIAL INVESTIGATION</div>
              <h1>Ask a clinical trial question.</h1>
              <p>Select a study of interest, ask your question in clinical language, and review the supporting evidence behind the result.</p>
            </section>

            <section className="panel investigator-composer">
              <div className="composer-heading">
                <div><div className="section-kicker"><BookOpen size={15}/> New investigation</div><h2>Study and question</h2></div>
              </div>
              <ClinicalStudySelector
                trials={trialCatalog}
                search={catalogSearch}
                onSearch={setCatalogSearch}
                selected={selectedCatalogTrial}
                onSelect={handleCatalogTrialSelect}
                onClearSelection={handleCatalogTrialClear}
                onQuestion={(nextQuestion) => setQuestion(nextQuestion)}
                catalogLoading={catalogLoading}
                catalogError={catalogError}
              />
              <form onSubmit={handleQuestionSubmit} className="query-form compact-query-form">
                <label htmlFor="investigator-question">Your question</label>
                <textarea id="investigator-question" aria-describedby="query-help" value={question} onChange={(e) => setQuestion(e.target.value)}
                  rows={3} placeholder="For example: Find completed studies connected through the same condition or intervention and compare their outcomes."/>
                <div className="composer-footer">
                  <div className="composer-options clinical-mode-row">
                    <div><span>Investigation approach</span><small id="query-help">{executionMode === "agentic" ? "Guided: TrialIQ searches, compares, checks evidence, then prepares the result." : "Direct: TrialIQ uses the standard deterministic query path."}</small></div>
                    <CompactModeSelector mode={executionMode} onChange={changeExecutionMode} disabled={loading}/>
                  </div>
                  <button type="submit" className="primary-button" disabled={loading || !question.trim()}>{loading ? "Investigating…" : "Investigate"} <ArrowRight size={16}/></button>
                </div>
              </form>
            </section>
          </> : <div className="investigator-session-shell">
            <QuerySummaryStrip
              question={lastSubmittedQuestion || text(result.question, question)}
              anchorNctId={activeAnchorNctId ?? selectedCatalogTrial?.nct_id}
              mode={result.execution_mode ?? executionMode}
              loading={loading}
              onEdit={() => setQueryExpanded(true)}
              onRunAgain={() => { if (executionMode === "agentic") void requestAgent(); else void requestBaseline(); }}
            />
            <InvestigatorResultWorkspace result={result} summary={summary} tab={investigatorTab} setTab={setInvestigatorTab}/>
          </div>}

          {loading && <ProcessingStatus elapsedSeconds={elapsedSeconds} mode={executionMode}/>}
          {result && queryExpanded && <InvestigatorResultWorkspace result={result} summary={summary} tab={investigatorTab} setTab={setInvestigatorTab}/>}
          {pendingHumanReview && !queryExpanded && <HumanReviewModal run={pendingHumanReview} question={lastSubmittedQuestion || question} continuing={loading} error={apiError} onContinue={continueHumanReview} onEdit={() => { setPendingHumanReview(null); setApiError(""); setQueryExpanded(true); }}/>}
        </>}

        {page === "explorer" && <>
          <section className="page-heading compact-heading">
            <div className="eyebrow">STUDY LOOKUP</div><h1>Study lookup</h1>
            <p>Open a ClinicalTrials.gov study and review the study information currently available to TrialIQ.</p>
          </section>
          <section className="panel lookup-panel">
            <form onSubmit={handleNctSubmit} className="query-form">
              <label htmlFor="nct-id">ClinicalTrials.gov identifier</label>
              <div className="inline-form"><input id="nct-id" value={nctId} onChange={(e) => setNctId(e.target.value)} placeholder="NCT03416088"/>
                <button type="submit" className="primary-button" disabled={loading}>{loading ? "Retrieving…" : "Get overview"} <ArrowRight size={16}/></button></div>
              <span className="helper-text">Choose a study in Investigator to populate this ID automatically, or enter any loaded NCT ID directly.</span>
            </form>
          </section>
          {loading && <ProcessingStatus elapsedSeconds={elapsedSeconds} explorer/>}
          {result ? <ResultPanel result={result} summary={summary}
            onStudies={() => { setWorkspaceTab("graph"); navigate("evidence"); }}
            onEvidence={() => { setWorkspaceTab("evidence"); navigate("evidence"); }}
            onConnections={() => { setWorkspaceTab("graph"); navigate("evidence"); }}/> : <EmptyState title="No trial loaded" message="Enter an NCT identifier to retrieve its overview."/>}
        </>}

        {page === "evidence" && <>
          <section className="page-heading compact-heading">
            <div className="eyebrow">SUPPORTING EVIDENCE</div><h1>Evidence review</h1>
            <p>Review the source records, study connections, and the steps TrialIQ used to prepare the latest result.</p>
          </section>
          {result ? <EvidenceWorkspace result={result} tab={workspaceTab} setTab={setWorkspaceTab}/> :
            <EmptyState title="No evidence loaded" message="Run an investigation or open a study first."/>}
        </>}

        {page === "architecture" && <>
          <section className="page-heading compact-heading">
            <div className="eyebrow">SYSTEM INTELLIGENCE</div><h1>Architecture & runtime</h1>
            <p>Explore TrialIQ's baseline and agentic execution paths, then inspect the components that actually participated in the latest run.</p>
          </section>
          <ArchitectureWorkspace result={result} defaultMode={executionMode}/>
        </>}

        {apiError && <div className="alert error-alert" role="alert"><CircleAlert size={18}/><span>{apiError}</span></div>}
      </div>
    </main>
  </div>;
}


type ArchitectureNode = {
  id: string;
  label: string;
  subtitle: string;
  description: string;
  detail?: string;
  status?: string;
};

type ArchitectureGroupItem = { kicker: string; title: string; description: string; tags?: string[] };
type ArchitectureGroupDefinition = {
  id: string;
  tone: "blue" | "violet" | "cyan" | "green" | "amber";
  icon: ReactNode;
  title: string;
  subtitle: string;
  items: ArchitectureGroupItem[];
};

function ArchitectureWorkspace({ result, defaultMode }: { result: UiResult | null; defaultMode: ExecutionMode }) {
  const [view, setView] = useState<"overview" | "journey" | "trust" | "technical" | "run">("overview");
  const [selected, setSelected] = useState<ArchitectureNode | null>(null);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({ experience: true });
  const resultMode = result?.execution_mode ?? defaultMode;
  const trace = result ? getTrace(result) : [];
  const traceByStage = (stage: string) => trace.find((item) => item.stage?.toLowerCase() === stage);
  const generation = result?.generation;

  const baselineNodes: ArchitectureNode[] = [
    { id: "baseline-query", label: "Investigator query", subtitle: "Natural language", description: "The investigator submits a bounded clinical-trial question through the React workspace.", status: resultMode === "baseline" && result ? "SUCCESS" : undefined },
    { id: "baseline-api", label: "FastAPI", subtitle: "POST /api/v1/query", description: "The standard query route executes the baseline workflow without agent/MCP orchestration.", detail: "mode: standard", status: resultMode === "baseline" && result ? "SUCCESS" : undefined },
    { id: "baseline-retrieval", label: "Deterministic retrieval", subtitle: "Allowlisted query path", description: "TrialIQ uses deterministic bounded retrieval rather than model-generated database queries.", status: resultMode === "baseline" && result ? text(result.run_status ?? result.status, "UNKNOWN") : undefined },
    { id: "baseline-graph", label: "Neo4j evidence", subtitle: "Bounded graph access", description: "Structured trial evidence is retrieved from the graph service. The browser never connects to Neo4j directly.", status: resultMode === "baseline" && result ? text(result.status) : undefined },
    { id: "baseline-validation", label: "Evidence validation", subtitle: "Technical checks", description: "Returned graph evidence is validated before it can be formatted as a grounded response.", status: resultMode === "baseline" && result ? (getValidation(result).valid === false ? "REVIEW" : "SUCCESS") : undefined },
    { id: "baseline-answer", label: "Grounded answer", subtitle: "Deterministic output", description: "The baseline answer is rendered from bounded validated evidence without the agentic runtime path.", status: resultMode === "baseline" && result ? text(result.status) : undefined },
  ];

  const agenticNodes: ArchitectureNode[] = [
    { id: "agent-query", label: "Investigator query", subtitle: "Natural language", description: "The same investigator question enters the agentic workflow.", status: resultMode === "agentic" && result ? "SUCCESS" : undefined },
    { id: "agent-supervisor", label: "Supervisor", subtitle: "Intent orchestration", description: "The Supervisor coordinates retrieval, validation, and synthesis while preserving typed workflow contracts.", status: resultMode === "agentic" && result ? "SUCCESS" : undefined },
    { id: "agent-retrieval", label: "Retrieval agent", subtitle: resultMode === "agentic" && result ? getToolName(result) : "Allowlisted tool selection", description: "The Retrieval Agent selects an allowlisted MCP capability from the validated query intent.", detail: traceByStage("retrieval")?.duration_ms !== undefined ? formatDuration(traceByStage("retrieval")?.duration_ms) : undefined, status: resultMode === "agentic" ? traceByStage("retrieval")?.status : undefined },
    { id: "agent-mcp", label: "FastMCP", subtitle: resultMode === "agentic" && result ? `${getTransport(result)} · ${getToolName(result)}` : "Typed tool transport", description: "MCP is the intended transport boundary between the agent workflow and deterministic retrieval tools.", status: resultMode === "agentic" ? traceByStage("retrieval")?.status : undefined },
    { id: "agent-graphrag", label: "GraphRAG / Neo4j", subtitle: "Bounded graph evidence", description: "Allowlisted graph tools retrieve trial evidence and bounded relationship paths without arbitrary LLM-generated Cypher.", status: resultMode === "agentic" ? traceByStage("retrieval")?.status : undefined },
    { id: "agent-validation", label: "Validation", subtitle: result?.agent_validation?.can_synthesize === true ? "Can synthesize" : "Evidence gate", description: "Validation decides whether the retrieved evidence is sufficient to pass to synthesis.", detail: traceByStage("validation")?.duration_ms !== undefined ? formatDuration(traceByStage("validation")?.duration_ms) : undefined, status: resultMode === "agentic" ? traceByStage("validation")?.status : undefined },
    { id: "agent-synthesis", label: "Synthesis", subtitle: generation?.method === "LLM" ? "LLM-grounded" : generation?.method === "DETERMINISTIC" ? "Deterministic formatter" : "Not executed", description: generation?.method === "LLM" ? "A configured language model composes the answer using only validated retrieved evidence." : "Some agentic response types are synthesized deterministically without an LLM.", detail: generation?.method === "LLM" ? [generation.provider, generation.model].filter(Boolean).join(" · ") : traceByStage("synthesis")?.duration_ms !== undefined ? formatDuration(traceByStage("synthesis")?.duration_ms) : undefined, status: resultMode === "agentic" ? traceByStage("synthesis")?.status : undefined },
    { id: "agent-answer", label: "Grounded answer", subtitle: generation?.method === "LLM" ? "AI synthesis + provenance" : "Evidence-grounded output", description: "The investigator receives the answer together with source references, limitations, and auditable runtime metadata.", status: resultMode === "agentic" && result ? text(result.run_status ?? result.status, "UNKNOWN") : undefined },
  ];

  const overviewGroups: ArchitectureGroupDefinition[] = [
    {
      id: "experience", tone: "blue", icon: <LayoutDashboard size={19}/>, title: "Experience — what the researcher sees",
      subtitle: "Ask questions, inspect answers, evidence, graph connections and runtime trace.",
      items: [
        { kicker: "Investigator", title: "Natural-language questions", description: "Researchers ask questions without needing SQL, Cypher, or knowledge of the source schema.", tags: ["React", "Vite"] },
        { kicker: "Evidence workspace", title: "Answer + source evidence", description: "Grounded answers are shown together with provenance records, validation warnings, and limitations." },
        { kicker: "Graph explorer", title: "Related-trial relationships", description: "Users can see trials connected through shared Conditions, Interventions, and Sponsors." },
      ],
    },
    {
      id: "intelligence", tone: "violet", icon: <GitBranch size={19}/>, title: "Intelligence — how the question is handled",
      subtitle: "A deterministic baseline or an agentic path using MCP and approved tools.",
      items: [
        { kicker: "Baseline", title: "Deterministic query path", description: "A predictable reference path for direct clinical-trial retrieval." },
        { kicker: "Agentic", title: "Agent plans the task", description: "The workflow interprets intent, extracts key entities, and chooses approved retrieval capabilities." },
        { kicker: "MCP", title: "Governed tool boundary", description: "The agent uses MCP rather than receiving unrestricted direct database access.", tags: ["No silent fallback", "Allowlisted tools"] },
      ],
    },
    {
      id: "evidence-graph", tone: "cyan", icon: <Network size={19}/>, title: "Evidence & Graph — how related trials are discovered",
      subtitle: "Bounded Neo4j traversal plus source lineage and validation.",
      items: [
        { kicker: "GraphRAG", title: "Bounded graph traversal", description: "Deterministic, allowlisted Cypher discovers related trials through shared entities.", tags: ["1–2 hops", "No arbitrary Cypher"] },
        { kicker: "Lineage", title: "Source-level provenance", description: "Source table, source key, and source ID explain where retrieved facts came from." },
        { kicker: "Validation", title: "Grounding checks", description: "Consistency checks happen before synthesis; warnings and limitations stay visible." },
      ],
    },
    {
      id: "data-foundation", tone: "amber", icon: <Database size={19}/>, title: "Data Foundation — where the evidence comes from",
      subtitle: "AACT / ClinicalTrials.gov → structured source → canonical graph.",
      items: [
        { kicker: "Source", title: "AACT / ClinicalTrials.gov", description: "Structured clinical-trial records provide the source evidence used by TrialIQ." },
        { kicker: "Structured store", title: "PostgreSQL / AACT", description: "Normalized source tables preserve identifiers and row-level evidence." },
        { kicker: "Knowledge graph", title: "Neo4j canonical entities", description: "Trials connect to shared Conditions, Interventions, and Sponsors for graph traversal.", tags: ["Canonical nodes", "Relationship provenance"] },
      ],
    },
  ];

  const technicalGroups: ArchitectureGroupDefinition[] = [
    { id: "tech-ui", tone: "blue", icon: <LayoutDashboard size={19}/>, title: "Frontend", subtitle: "React + Vite Investigator Console", items: [
      { kicker: "Module", title: "Investigator", description: "Natural-language research questions with baseline and agentic execution modes." },
      { kicker: "Module", title: "Evidence Workspace", description: "Answer, source evidence, GraphRAG, trace, and validation views." },
      { kicker: "Module", title: "Architecture & Runtime", description: "Explains the system and overlays metadata from the latest execution." },
    ]},
    { id: "tech-api", tone: "violet", icon: <Activity size={19}/>, title: "FastAPI application layer", subtitle: "Typed routes and service boundaries", items: [
      { kicker: "Query", title: "/api/v1/query", description: "Deterministic baseline question answering." },
      { kicker: "Agent", title: "/api/v1/query/agent", description: "Agentic execution with MCP as the intended transport." },
      { kicker: "Lineage", title: "/api/v1/lineage/trials/{nct_id}", description: "Flat provenance records plus validation and limitations." },
    ]},
    { id: "tech-graph", tone: "cyan", icon: <Network size={19}/>, title: "GraphRAG and Neo4j", subtitle: "Bounded related-trial discovery", items: [
      { kicker: "Traversal", title: "Bounded Cypher", description: "Allowlisted relationship types, explicit hop limits, and bounded result sizes." },
      { kicker: "Entities", title: "Canonical shared nodes", description: "Condition, Intervention, and Sponsor entities connect trials." },
      { kicker: "Safety", title: "No arbitrary LLM Cypher", description: "The language model does not author unrestricted database queries." },
    ]},
    { id: "tech-evidence", tone: "green", icon: <ShieldCheck size={19}/>, title: "Evidence, validation and synthesis", subtitle: "How retrieved data becomes an answer", items: [
      { kicker: "Provenance", title: "Lineage service", description: "Exposes source table, source key, source ID, and source NCT ID." },
      { kicker: "Quality", title: "Evidence validator", description: "Checks trial and entity consistency before synthesis." },
      { kicker: "Answer", title: "Grounded synthesis", description: "Produces human-readable answers from validated retrieval results." },
    ]},
    { id: "tech-data", tone: "amber", icon: <Database size={19}/>, title: "Data foundation", subtitle: "AACT / PostgreSQL → canonical graph", items: [
      { kicker: "Source", title: "AACT / ClinicalTrials.gov", description: "Structured clinical-trial source data." },
      { kicker: "Store", title: "PostgreSQL", description: "Source tables and row identifiers used for provenance." },
      { kicker: "Graph", title: "Neo4j", description: "Canonical graph used by bounded related-trial traversal." },
    ]},
  ];

  const activeNodes = resultMode === "baseline" ? baselineNodes : agenticNodes;
  const selectedNode = selected ?? activeNodes.find((node) => node.status) ?? activeNodes[0];
  const toggleGroup = (id: string) => setOpenGroups((current) => ({ ...current, [id]: !current[id] }));

  return <section className="panel architecture-panel architecture-explainer">
    <div className="architecture-explainer-header">
      <div>
        <div className="section-kicker"><Waypoints size={16}/> Architecture explainer</div>
        <h2>Ask a trial question. See the answer <em>and</em> the evidence.</h2>
        <p>Start with the simple story for non-technical audiences, then expand only the layer or runtime detail someone asks about.</p>
      </div>
      <div className="architecture-explainer-badges" aria-label="Core technologies">
        <span>React + Vite</span><span>FastAPI</span><span>MCP</span><span>Neo4j</span>
      </div>
    </div>

    <div className="architecture-story-tabs" role="tablist" aria-label="Architecture views">
      {([
        ["overview", "Overview"], ["journey", "How it works"], ["trust", "Trust & evidence"], ["technical", "Technical"], ["run", "Current run"],
      ] as const).map(([id, label]) => <button key={id} type="button" role="tab" aria-selected={view === id} className={view === id ? "active" : ""} onClick={() => { setView(id); setSelected(null); }}>{label}</button>)}
    </div>

    {view === "overview" && <div className="architecture-story-view">
      <div className="architecture-demo-question">
        <div><span>DEMO QUESTION</span><strong>Related-trial discovery</strong></div>
        <p>“Find trials related to NCT03416088. Explain the shared condition, intervention, or sponsor, and cite the available evidence.”</p>
      </div>
      <div className="architecture-section-heading"><div><h3>Four simple layers</h3><p>Click a layer to reveal only the level of detail you need.</p></div></div>
      <div className="architecture-accordion">
        {overviewGroups.map((group) => <ArchitectureCollapsibleGroup key={group.id} {...group} open={Boolean(openGroups[group.id])} onToggle={() => toggleGroup(group.id)}/>)}
      </div>
      <div className="architecture-presenter-tip"><Info size={17}/><div><strong>Presenter tip</strong><p>“The researcher sees one workspace. Underneath it, TrialIQ has a controlled AI layer, an evidence-and-graph layer, and a real clinical-trial data foundation.”</p></div></div>
    </div>}

    {view === "journey" && <div className="architecture-story-view">
      <div className="architecture-section-heading"><div><h3>How one question becomes an answer</h3><p>This is the cleanest view for a live demonstration because it hides implementation detail.</p></div></div>
      <div className="architecture-journey">
        {[
          ["1", "Ask", "The researcher asks a natural-language question or starts from an NCT identifier.", "User stays in control."],
          ["2", "Understand", "TrialIQ identifies intent and the evidence needed to answer the question.", "Baseline or agentic path."],
          ["3", "Retrieve", "MCP invokes approved tools. GraphRAG explores bounded relationships in Neo4j.", "No unrestricted database access."],
          ["4", "Validate", "Retrieved records and provenance are checked before the answer is synthesized.", "Warnings remain visible."],
          ["5", "Explain", "The user receives a grounded answer plus evidence, graph relationships, and execution trace.", "Answer + proof."],
        ].map(([number, title, description, note]) => <div className="architecture-journey-step" key={number}><span>{number}</span><h4>{title}</h4><p>{description}</p><small>{note}</small></div>)}
      </div>
      <div className="architecture-key-distinction"><CheckCircle2 size={20}/><div><strong>The important distinction</strong><p>TrialIQ does not ask an LLM to invent graph queries or infer relationships freely. Related-trial discovery comes from bounded, deterministic graph traversal over curated entities.</p></div></div>
    </div>}

    {view === "trust" && <div className="architecture-story-view">
      <div className="architecture-section-heading"><div><h3>Why the result is inspectable</h3><p>Three capabilities make TrialIQ different from a generic chatbot.</p></div></div>
      <div className="architecture-trust-grid">
        <div><span>01</span><h4>Evidence lineage</h4><p>Source keys, source IDs, and source tables connect retrieved facts back to AACT records.</p></div>
        <div><span>02</span><h4>Visible graph path</h4><p>Users can see which condition, intervention, or sponsor connects two trials.</p></div>
        <div><span>03</span><h4>Execution trace</h4><p>The workspace exposes transport, tool usage, retrieval, validation, and synthesis stages.</p></div>
      </div>
      <div className="architecture-lineage-trace">
        <ArchitectureTraceStep marker="A" title="AACT source record" detail="Example: conditions:NCT03416088:416354331"/>
        <ArchitectureTraceStep marker="G" title="Canonical graph relationship" detail="NCT03416088 → Retinal Microcirculation Disorder → NCT04214743"/>
        <ArchitectureTraceStep marker="V" title="Validation" detail="Checks identifiers, evidence consistency, and available provenance."/>
        <ArchitectureTraceStep marker="A" title="Grounded answer" detail="The explanation is constrained by retrieved evidence and visible limitations." last/>
      </div>
    </div>}

    {view === "technical" && <div className="architecture-story-view">
      <div className="architecture-section-heading"><div><h3>Technical architecture</h3><p>Open this view only when someone wants implementation detail.</p></div></div>
      <div className="architecture-accordion">
        {technicalGroups.map((group) => <ArchitectureCollapsibleGroup key={group.id} {...group} open={Boolean(openGroups[group.id])} onToggle={() => toggleGroup(group.id)}/>)}
      </div>
    </div>}

    {view === "run" && <div className="architecture-story-view">
      {result ? <div className="architecture-current-run">
        <div className="current-run-heading">
          <div><span>Latest execution</span><strong>{resultMode === "agentic" ? "Agentic workflow" : "Baseline workflow"}</strong></div>
          <div className="current-run-meta">
            {result.run_id && <code>{result.run_id}</code>}
            <span className={`run-state run-state-${text(result.run_status ?? result.status, "UNKNOWN").toLowerCase().replace(/_/g, "-")}`}>{text(result.run_status ?? result.status, "UNKNOWN")}</span>
          </div>
        </div>
        <ArchitectureLane title={resultMode === "agentic" ? "Agentic runtime" : "Baseline runtime"} badge={resultMode === "agentic" ? text(getTransport(result), "MCP") : "Standard"} nodes={activeNodes} selectedId={selectedNode?.id} onSelect={setSelected} runtime/>
        <div className="architecture-detail" aria-live="polite">
          <div className="architecture-detail-icon"><GitBranch size={19}/></div>
          <div>
            <span>Selected component</span><h3>{selectedNode.label}</h3><p>{selectedNode.description}</p>
            <div className="architecture-detail-tags"><span>{selectedNode.subtitle}</span>{selectedNode.detail && <span>{selectedNode.detail}</span>}{selectedNode.status && <span className="detail-status">{selectedNode.status}</span>}</div>
          </div>
        </div>
      </div> : <div className="architecture-empty"><Network size={28}/><strong>No current run yet</strong><p>Run a Baseline or Agentic investigation first, then return here to overlay its real status, tool, transport, timing, and generation metadata.</p></div>}
    </div>}

    <div className="architecture-proof">
      <div><strong>Browser boundary</strong><span>No direct Neo4j/Cypher access</span></div>
      <div><strong>Retrieval boundary</strong><span>Bounded allowlisted tools</span></div>
      <div><strong>Agent transport</strong><span>MCP when agentic</span></div>
      <div><strong>Answer provenance</strong><span>Generation method + evidence trace</span></div>
    </div>
  </section>;
}

function ArchitectureCollapsibleGroup({ tone, icon, title, subtitle, items, open, onToggle }: {
  tone: "blue" | "violet" | "cyan" | "green" | "amber";
  icon: ReactNode;
  title: string;
  subtitle: string;
  items: ArchitectureGroupItem[];
  open: boolean;
  onToggle: () => void;
}) {
  return <div className={`architecture-group ${open ? "open" : ""}`}>
    <button type="button" className="architecture-group-toggle" onClick={onToggle} aria-expanded={open}>
      <span className={`architecture-group-icon tone-${tone}`}>{icon}</span>
      <span className="architecture-group-copy"><strong>{title}</strong><small>{subtitle}</small></span>
      <ChevronDown size={18} className="architecture-group-chevron"/>
    </button>
    {open && <div className="architecture-group-body"><div className="architecture-card-grid">
      {items.map((item) => <div className="architecture-mini-card" key={`${item.kicker}-${item.title}`}>
        <span>{item.kicker}</span><h4>{item.title}</h4><p>{item.description}</p>
        {item.tags?.length ? <div className="architecture-mini-tags">{item.tags.map((tag) => <small key={tag}>{tag}</small>)}</div> : null}
      </div>)}
    </div></div>}
  </div>;
}

function ArchitectureTraceStep({ marker, title, detail, last = false }: { marker: string; title: string; detail: string; last?: boolean }) {
  return <div className={`architecture-lineage-step ${last ? "last" : ""}`}><span>{marker}</span><div><strong>{title}</strong><small>{detail}</small></div></div>;
}

function ArchitectureLane({ title, badge, nodes, selectedId, onSelect, runtime = false }: {
  title: string;
  badge: string;
  nodes: ArchitectureNode[];
  selectedId?: string;
  onSelect: (node: ArchitectureNode) => void;
  runtime?: boolean;
}) {
  return <div className={`architecture-lane ${runtime ? "runtime-lane" : ""}`}>
    <div className="architecture-lane-heading"><strong>{title}</strong><span>{badge}</span></div>
    <div className="architecture-flow">
      {nodes.map((node, index) => <div className="architecture-flow-step" key={node.id}>
        <button type="button" className={`architecture-node ${selectedId === node.id ? "selected" : ""} ${node.status ? `node-${node.status.toLowerCase().replace(/_/g, "-")}` : ""}`} onClick={() => onSelect(node)} title={node.description}>
          <span className="architecture-node-index">{String(index + 1).padStart(2, "0")}</span>
          <span className="architecture-node-copy"><strong>{node.label}</strong><small>{node.subtitle}</small></span>
          {node.status && <span className="architecture-node-status">{node.status}</span>}
        </button>
        {index < nodes.length - 1 && <div className="architecture-connector" aria-hidden="true"><span>↓</span></div>}
      </div>)}
    </div>
  </div>;
}


function InvestigatorResultWorkspace({ result, summary, tab, setTab }: { result: UiResult; summary: string[][]; tab: InvestigatorTab; setTab: (tab: InvestigatorTab) => void }) {
  const related = getRelatedTrialResponse(result);
  const seedNct = related?.seed_nct_id ?? getEvidence(result)?.nct_id;
  const matches = related?.matches ?? [];
  const connectionIds = new Set(matches.flatMap((match) => (match.connected_via ?? []).map((path, index) => path.entity_id ?? `${path.relationship_type}:${text(path.entity?.canonical_key ?? path.entity?.normalized_name ?? path.entity?.name, String(index))}`)));
  const reviewDecision = result.human_review_decision;
  return <div className={`investigator-result-shell stable-workspace ${tab === "connections" ? "graph-active" : ""}`}>
    {reviewDecision && <div className="human-review-decision-strip" aria-label="Investigator study selection summary"><div><span>Investigator-guided analysis</span><strong>{reviewDecision.discovered_candidate_count} discovered · {reviewDecision.selected_candidate_count} analysed</strong></div><small>{reviewDecision.mode === "ALL" ? "All discovered candidates were approved for analysis." : "Only the investigator-selected studies drive this result."}</small></div>}
    <div className="investigator-result-tabs" role="tablist" aria-label="Investigator result views">
      <TabButton active={tab === "answer"} onClick={() => setTab("answer")} icon={<BookOpen size={15}/>} label="Answer"/>
      <TabButton active={tab === "studies"} onClick={() => setTab("studies")} icon={<FlaskConical size={15}/>} label={`Studies${matches.length ? ` · ${matches.length}` : ""}`}/>
      <TabButton active={tab === "connections"} onClick={() => setTab("connections")} icon={<Waypoints size={15}/>} label={`Connections${connectionIds.size ? ` · ${connectionIds.size}` : ""}`}/>
      <TabButton active={tab === "evidence"} onClick={() => setTab("evidence")} icon={<ShieldCheck size={15}/>} label="Evidence"/>
    </div>
    {tab === "answer" && <ResultPanel result={result} summary={summary} onStudies={() => setTab("studies")} onEvidence={() => setTab("evidence")} onConnections={() => setTab("connections")}/>}
    {tab !== "answer" && <section className={`panel investigator-inline-workspace task-workspace task-${tab}`}>
      <div className="inline-workspace-header"><div><span>{tab === "studies" ? "Study workspace" : tab === "connections" ? "Connection explanation" : "Evidence review"}</span><strong>{text(seedNct, "Latest investigation")}</strong></div></div>
      {tab === "studies" && <StudiesWorkspace result={result} onEvidence={() => setTab("evidence")}/>}
      {tab === "connections" && <GraphView result={result}/>}
      {tab === "evidence" && <EvidenceView result={result}/>}
    </section>}
    <ReportReviewPanel result={result}/>
  </div>;
}

const REPORT_SECTION_OPTIONS: Array<{ value: ReportSection; label: string; description: string }> = [
  { value: "ANSWER", label: "Answer summary", description: "Investigator-facing conclusion and key findings" },
  { value: "STUDIES", label: "Analysed studies", description: "Study identifiers, status, phase and enrollment" },
  { value: "CONNECTIONS", label: "Connection explanation", description: "Why the selected studies are related" },
  { value: "EVIDENCE", label: "Evidence references", description: "Source references supporting the investigation" },
  { value: "TECHNICAL_DETAILS", label: "Technical execution details", description: "Run ID, MCP transport/tool and generation metadata" },
];

function buildReportRequest(result: UiResult, sections: ReportSection[], investigatorNote: string) {
  const sources = (Array.isArray(result.sources) ? result.sources : []).map((source) => ({
    source_table: source.source_table ?? null,
    source_key: source.source_key ?? null,
    source_id: source.source_id ?? null,
  }));
  return {
    answer: {
      status: result.status ?? "GROUNDED",
      question: result.question ?? "TrialIQ investigation",
      answer: result.answer ?? "No narrative summary reported.",
      graph_response: result.graph_response ?? null,
      condition_search_response: result.condition_search_response ?? null,
      entity_search_response: result.entity_search_response ?? null,
      shared_entity_response: result.shared_entity_response ?? null,
      related_trial_response: result.related_trial_response ?? result.retrieval?.related_trial_response ?? null,
      limitations: result.limitations ?? [],
      sources,
    },
    preferences: {
      sections,
      investigator_note: investigatorNote.trim() || null,
    },
    run_id: result.run_id ?? null,
    agent_status: result.run_status ?? result.status ?? null,
    transport: result.retrieval?.transport ?? null,
    tool_name: result.retrieval?.tool_name ?? null,
    generation: result.generation ?? null,
    structured_synthesis: result.structured_synthesis ?? null,
    human_review_decision: result.human_review_decision ?? null,
  };
}

function ReportReviewPanel({ result }: { result: UiResult }) {
  const [open, setOpen] = useState(false);
  const [sections, setSections] = useState<ReportSection[]>(["ANSWER", "STUDIES", "CONNECTIONS", "EVIDENCE"]);
  const [investigatorNote, setInvestigatorNote] = useState("");
  const [reportDownloading, setReportDownloading] = useState(false);
  const [reportError, setReportError] = useState("");
  const related = getRelatedTrialResponse(result);
  const seedNct = related?.seed_nct_id ?? getEvidence(result)?.nct_id ?? "investigation";
  const toggleSection = (section: ReportSection) => setSections((current) => current.includes(section) ? current.filter((item) => item !== section) : [...current, section]);

  useEffect(() => {
    if (!open) return;
    document.body.classList.add("trialiq-modal-open");
    return () => document.body.classList.remove("trialiq-modal-open");
  }, [open]);

  const downloadReport = async () => {
    setReportError("");
    setReportDownloading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/query/agent/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildReportRequest(result, sections, investigatorNote)),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const detail = payload?.detail;
        throw new Error(typeof detail === "string" ? detail : "TrialIQ could not generate the PDF report.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      const disposition = response.headers.get("Content-Disposition") ?? "";
      const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
      anchor.download = filenameMatch?.[1] ?? `trialiq-${String(seedNct).replace(/[^A-Za-z0-9_-]+/g, "-")}-report.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setOpen(false);
    } catch (error) {
      setReportError(error instanceof Error ? error.message : "TrialIQ could not generate the PDF report.");
    } finally {
      setReportDownloading(false);
    }
  };

  return <section className="report-review-panel report-launch-panel">
    <div><span><strong>Ready to share this investigation?</strong><small>Choose what to include before TrialIQ generates the PDF.</small></span></div>
    <button type="button" className="secondary-button" onClick={() => setOpen(true)}><Download size={15}/> Prepare report</button>
    {open && <div className="trialiq-modal-backdrop report-modal-backdrop" role="presentation">
      <section className="trialiq-modal report-modal-panel" role="dialog" aria-modal="true" aria-labelledby="report-modal-title">
        <header className="trialiq-modal-header report-review-heading">
          <div><span>Human review checkpoint</span><h3 id="report-modal-title">Choose what to include in the report</h3><p>The PDF is generated only from the investigation already shown in TrialIQ. Technical execution details remain optional, and investigator-authored notes stay clearly separated from TrialIQ evidence.</p></div>
          <button type="button" className="icon-button modal-close-button" onClick={() => setOpen(false)} disabled={reportDownloading} aria-label="Close report preparation"><X size={18}/></button>
        </header>
        <div className="hitl-progress report-progress" aria-label="Report preparation progress"><span className="complete"><CheckCircle2 size={14}/> Investigation complete</span><span className="current">2 Review report contents</span><span>3 Generate PDF</span><span className="disabled-step">Email later</span></div>
        <div className="trialiq-modal-body report-review-body">
          <div className="report-section-grid">{REPORT_SECTION_OPTIONS.map((option) => <label key={option.value} className={`report-section-option ${sections.includes(option.value) ? "selected" : ""}`}>
            <input type="checkbox" checked={sections.includes(option.value)} disabled={reportDownloading} onChange={() => toggleSection(option.value)}/><span><strong>{option.label}</strong><small>{option.description}</small></span>
          </label>)}</div>
          <label className="report-note-field"><span>Investigator note <small>optional</small></span><textarea rows={4} value={investigatorNote} maxLength={2000} disabled={reportDownloading} onChange={(event) => setInvestigatorNote(event.target.value)} placeholder="Add context that should appear as an investigator-authored note in the PDF report."/></label>
          {reportError && <div className="graph-error" role="alert"><CircleAlert size={17}/><span>{reportError}</span></div>}
        </div>
        <footer className="trialiq-modal-footer report-review-actions"><div><strong>{sections.length} section{sections.length === 1 ? "" : "s"} selected</strong><span>PDF download is available now. Email delivery remains reserved for a later integration.</span></div><div>
          <button type="button" className="secondary-button" disabled title="Email integration is not configured yet"><Mail size={15}/> Send report</button>
          <button type="button" className="primary-button" disabled={!sections.length || reportDownloading} onClick={downloadReport}><Download size={15}/> {reportDownloading ? "Preparing PDF…" : "Download PDF"}</button>
        </div></footer>
      </section>
    </div>}
  </section>;
}

function ProcessingStatus({ elapsedSeconds, explorer = false, mode = "agentic" }: { elapsedSeconds: number; explorer?: boolean; mode?: ExecutionMode }) {
  return <div className="processing-toast" role="status" aria-live="polite" aria-busy="true">
    <div className="processing-spinner"/>
    <div className="processing-toast-content"><div className="processing-toast-heading"><strong>{explorer ? "Retrieving trial evidence" : mode === "agentic" ? "Reviewing connected study evidence" : "Running direct study query"}</strong><span>{elapsedSeconds}s</span></div>
      <p>{explorer ? "Calling the deterministic trial overview endpoint." : mode === "agentic" ? "TrialIQ is interpreting the question, finding connected studies, checking evidence, and preparing the result." : "TrialIQ is retrieving and checking the requested study evidence."}</p>
      <div className="processing-toast-progress"><div className="processing-toast-progress-bar"/></div>
    </div>
  </div>;
}

function clinicalLimitationText(value: string, studyNctId?: string | null) {
  const studyReference = studyNctId ? `the study of interest (${studyNctId})` : "the study of interest";
  if (value.includes("Traversal is limited to shared condition, intervention, and sponsor metadata")) return "This result considers shared conditions, interventions, and sponsors.";
  if (value.includes("Traversal is bounded to at most 1 hop")) return `The related-study search was limited to studies directly connected to ${studyReference}.`;
  if (value.includes("Traversal is bounded to at most")) return "The related-study search used a limited connection distance to keep the result focused.";
  if (value.includes("Results are bounded by per-hop and overall limits")) return "The number of connected studies reviewed is limited to keep the result focused and reviewable.";
  if (value.includes("Narrative synthesis was rejected by deterministic grounding validation")) return "TrialIQ used an evidence-based fallback summary because the generated narrative did not pass the evidence check.";
  return value;
}

function ResultPanel({ result, summary, onStudies, onEvidence, onConnections }: { result: UiResult; summary: string[][]; onStudies: () => void; onEvidence: () => void; onConnections: () => void }) {
  const evidence = getEvidence(result);
  const trial = evidence?.trial ?? null;
  const validation = getValidation(result);
  const status = text(result.status, "UNKNOWN");
  const mode = result.execution_mode ?? (getTrace(result).length ? "agentic" : "baseline");
  const related = getRelatedTrialResponse(result);
  const hasGraphSeed = Boolean(related?.seed_nct_id ?? evidence?.nct_id);
  const relatedNotFound = status === "NOT_FOUND" && related?.status === "NOT_FOUND";
  const generation = result.generation;
  const answerMethod = mode === "baseline"
    ? "Evidence summary"
    : generation?.method === "LLM"
      ? "TrialIQ summary"
      : generation?.method === "DETERMINISTIC"
        ? "Evidence summary"
        : "Evidence retrieved";
  const statusLabel = status === "GROUNDED" ? "Supported by evidence" : status === "NOT_FOUND" ? "No matching studies" : status;
  const methodTitle = mode === "baseline"
    ? "TrialIQ prepared this summary directly from the retrieved study evidence."
    : generation?.method === "LLM"
      ? "TrialIQ prepared this summary from the supporting evidence that passed its evidence checks."
      : generation?.method === "DETERMINISTIC"
        ? "TrialIQ prepared an evidence-based fallback summary from the retrieved study evidence."
        : "TrialIQ retrieved evidence for this investigation, but a full summary was not produced.";

  return <section className={`panel result-panel result-${mode}`}>
    <div className="result-header">
      <div><div className="section-kicker"><BookOpen size={16}/> TrialIQ findings</div>
        <h2>{text(trial?.brief_title, text(evidence?.nct_id, relatedNotFound ? "Bounded graph search" : "Evidence summary"))}</h2>
        <p className="muted">{text(result.question, "Question not reported")}</p></div>
      <div className="result-badges">
        <span className={`method-pill method-${mode}`} title={methodTitle}>{answerMethod}</span>
        <span className={`status-pill ${status === "GROUNDED" ? "status-grounded" : "status-review"}`}>{statusLabel}</span>
      </div>
    </div>
    {trial && <div className="summary-grid">{summary.map(([label, value]) => <div className="summary-tile" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>}
    {mode === "agentic" && related && !!related.matches?.length && <AgenticAnswerSummary result={result} response={related} onStudies={onStudies} onEvidence={onEvidence} onConnections={onConnections}/>}
    {!(mode === "agentic" && related && !!related.matches?.length) && <div className="answer-block"><div className="block-heading"><h3>Answer</h3><span>{validation.valid === true ? "Evidence validation passed" : relatedNotFound ? "Valid bounded search · no matches" : "Review evidence & limitations"}</span></div>
      <div className="answer-text">{relatedNotFound && related ? <RelatedTrialEmptyState response={related}/> : <MarkdownAnswer content={text(result.answer, "No synthesized answer was returned.")}/>}</div></div>}
    {!!result.limitations?.length && !relatedNotFound && <details className="result-limitations">
      <summary><span><Info size={15}/> Limitations & data notes</span><span className="limitations-summary-meta"><span className="limitation-count-badge" aria-label={`${result.limitations.length} limitation notes`}>{result.limitations.length}</span><span className="limitation-count-label">notes</span><ChevronDown size={15}/></span></summary>
      <ul>{result.limitations.map((item, i) => <li key={i}>{clinicalLimitationText(item, related?.seed_nct_id ?? evidence?.nct_id)}</li>)}</ul>
    </details>}
    <div className="result-actions answer-secondary-actions">
      {mode === "agentic" && related?.matches?.length ? <button type="button" className="secondary-button" onClick={onStudies}>View all related studies <ArrowRight size={16}/></button> : null}
      <button type="button" className="secondary-button" onClick={onEvidence}>Review evidence <ArrowRight size={16}/></button>
      {hasGraphSeed && <button type="button" className="secondary-button graph-result-action" onClick={onConnections}><Waypoints size={15}/> Explore connections <ArrowRight size={16}/></button>}
    </div>
    <details className="how-trialiq-disclosure"><summary>How TrialIQ produced this answer <ChevronDown size={14}/></summary><ExecutionView result={result}/></details>
  </section>;
}

function buildRelatedFallbackSynthesis(response: RelatedTrialResponse): StructuredSynthesis | null {
  const matches = response.matches ?? [];
  if (!matches.length) return null;
  const aggregate = response.metrics ?? {};
  const relatedCount = aggregate.related_trial_count || matches.length;
  const sharedCount = aggregate.unique_shared_entity_count || matches.reduce((total, match) => total + (match.metrics?.total_shared_entity_count || match.connected_via.length), 0);
  const pathCount = aggregate.evidence_path_count || matches.reduce((total, match) => total + (match.metrics?.evidence_path_count || match.connected_via.length), 0);
  const completedOnly = (response.overall_statuses ?? []).length === 1 && response.overall_statuses?.[0] === "COMPLETED";
  const comparable = matches.some((match) => Boolean(
    match.metrics?.start_date_comparison ||
    match.metrics?.completion_date_comparison ||
    match.metrics?.duration_comparison ||
    match.metrics?.enrollment_comparison
  ));
  const relationshipLabel = (value: string | undefined) => {
    if (value === "HAS_CONDITION") return "Condition";
    if (value === "HAS_INTERVENTION") return "Intervention";
    if (value === "SPONSORED_BY") return "Sponsor";
    return text(value, "Connection");
  };
  const keyFindings: StructuredFinding[] = matches.flatMap((match) => {
    if (!match.connected_via.length) return [];
    const connections = match.connected_via.map((path) => `${relationshipLabel(path.relationship_type)} — ${text(path.entity?.name ?? path.entity?.normalized_name, "shared entity")}`);
    return [{
      statement: `${match.nct_id} is connected through ${connections.join("; ")}.`,
      evidence_ids: match.connected_via.map((_path, index) => `path:${match.nct_id}:${index}`),
    }];
  });
  if (!keyFindings.length) return null;
  return {
    headline: `${relatedCount}${completedOnly ? " completed" : ""} related trial${relatedCount === 1 ? "" : "s"} connected to ${text(response.seed_nct_id, "the study of interest")}`,
    summary: `TrialIQ found ${relatedCount} related trial${relatedCount === 1 ? "" : "s"} through ${sharedCount} shared clinical factor${sharedCount === 1 ? "" : "s"} across ${pathCount} supporting connection${pathCount === 1 ? "" : "s"}.${comparable ? "" : " Timeline and enrollment comparisons cannot be calculated because the required values are not present in the loaded study records."}`,
    key_findings: keyFindings,
  };
}

type StandoutInsight = {
  key: string;
  label: string;
  value: string;
  detail: string;
};


function connectionReason(path: RelatedTrialPathEvidence) {
  if (path.relationship_type === "HAS_CONDITION") return "Condition";
  if (path.relationship_type === "HAS_INTERVENTION") return "Intervention";
  if (path.relationship_type === "SPONSORED_BY") return "Sponsor";
  return "Connection";
}

function AgenticAnswerSummary({ result, response, onStudies, onEvidence, onConnections }: { result: UiResult; response: RelatedTrialResponse; onStudies: () => void; onEvidence: () => void; onConnections: () => void }) {
  const matches = response.matches ?? [];
  const synthesis = result.structured_synthesis ?? buildRelatedFallbackSynthesis(response);
  const aggregate = response.metrics ?? {};
  const topStudies = matches.slice(0, 5);
  const connectionIds = new Set(matches.flatMap((match) => (match.connected_via ?? []).map((path, index) => path.entity_id ?? `${path.relationship_type}:${text(path.entity?.canonical_key ?? path.entity?.normalized_name ?? path.entity?.name, String(index))}`)));
  const comparableTiming = matches.filter((match) => match.metrics?.completion_date_comparison || match.metrics?.duration_comparison).length;
  const comparableEnrollment = matches.filter((match) => match.metrics?.enrollment_comparison).length;
  const findings = synthesis?.key_findings?.slice(0, 3) ?? [];
  return <div className="answer-dashboard">
    <section className="answer-hero-card">
      <div className="answer-hero-copy">
        <span>Answer</span>
        <h3>{synthesis?.headline ?? `${matches.length} related studies identified`}</h3>
        <p>{synthesis?.summary ?? `TrialIQ identified ${matches.length} related studies using the available source-backed connections.`}</p>
      </div>
      <div className="answer-hero-metrics">
        <div><strong>{matches.length}</strong><span>studies in this answer</span></div>
        <div><strong>{connectionIds.size}</strong><span>shared entities</span></div>
        <div><strong>{comparableTiming}/{matches.length}</strong><span>with timing comparisons</span></div>
        <div><strong>{comparableEnrollment}/{matches.length}</strong><span>with enrollment comparisons</span></div>
      </div>
    </section>

    {findings.length > 0 && <section className="answer-section compact-findings-section">
      <div className="answer-section-heading"><div><span>What stands out</span><strong>Evidence-backed highlights</strong></div><small>{findings.length} shown</small></div>
      <div className="compact-findings-grid">{findings.map((finding, index) => <article key={`${finding.statement}-${index}`}>
        <span>{index + 1}</span><p>{finding.statement}</p>
      </article>)}</div>
    </section>}

    <section className="answer-section related-preview-section">
      <div className="answer-section-heading"><div><span>Top related studies</span><strong>{matches.length} studies were analysed</strong></div><button type="button" className="text-action" onClick={onStudies}>View all studies <ArrowRight size={14}/></button></div>
      <div className="related-preview-list">{topStudies.map((match) => {
        const reasons = (match.connected_via ?? []).slice(0, 3).map((path) => ({ type: connectionReason(path), name: text(path.entity?.name ?? path.entity?.normalized_name, "Shared factor") }));
        return <button type="button" className="related-preview-row" key={match.nct_id} onClick={onStudies}>
          <div className="related-preview-id"><strong>{match.nct_id}</strong><span className={`clinical-status ${clinicalStatusClass(typeof match.trial?.overall_status === "string" ? match.trial.overall_status : null)}`}>{humanStatusLabel(typeof match.trial?.overall_status === "string" ? match.trial.overall_status : null)}</span></div>
          <div className="related-preview-title"><strong>{text(match.trial?.brief_title, "Study title not reported")}</strong><div>{reasons.map((reason, index) => <span key={`${reason.type}-${reason.name}-${index}`}>{reason.type}: {reason.name}</span>)}</div></div>
          <ArrowRight size={16}/>
        </button>;
      })}</div>
    </section>

    <div className="answer-next-actions" aria-label="Continue investigating this result">
      <button type="button" onClick={onStudies}><FlaskConical size={18}/><span><strong>Compare studies</strong><small>Filter, select and compare the analysed studies.</small></span><ArrowRight size={16}/></button>
      <button type="button" onClick={onConnections}><Waypoints size={18}/><span><strong>Explore connections</strong><small>See the clinical reasons linking the studies.</small></span><ArrowRight size={16}/></button>
      <button type="button" onClick={onEvidence}><ShieldCheck size={18}/><span><strong>Review evidence</strong><small>Inspect source records and validation status.</small></span><ArrowRight size={16}/></button>
    </div>
    {(aggregate.related_trial_count ?? matches.length) !== matches.length && <p className="answer-scope-note">This answer shows the bounded set analysed by TrialIQ. Wider graph connectivity may contain additional studies.</p>}
  </div>;
}

function parseTrialDate(value: unknown): number | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function formatShortDate(value: unknown) {
  const timestamp = parseTrialDate(value);
  if (timestamp === null) return "Not reported";
  return new Intl.DateTimeFormat("en", { month: "short", year: "numeric" }).format(new Date(timestamp));
}

function formatExactTimelineDate(value: number | null) {
  if (value === null) return "Not reported";
  return new Intl.DateTimeFormat("en", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
}

function timelineTicks(minDate: number, maxDate: number) {
  const yearMs = 365.25 * 24 * 60 * 60 * 1000;
  const spanYears = (maxDate - minDate) / yearMs;
  if (spanYears < 2) {
    return Array.from({ length: 5 }, (_, index) => {
      const value = minDate + ((maxDate - minDate) * index) / 4;
      return { value, label: new Intl.DateTimeFormat("en", { month: "short", year: "numeric" }).format(new Date(value)) };
    });
  }
  const firstYear = new Date(minDate).getFullYear();
  const lastYear = new Date(maxDate).getFullYear();
  const rawSpan = Math.max(1, lastYear - firstYear);
  const step = rawSpan <= 6 ? 1 : rawSpan <= 14 ? 2 : rawSpan <= 28 ? 5 : rawSpan <= 55 ? 10 : 20;
  const values: number[] = [minDate];
  const firstAligned = Math.ceil(firstYear / step) * step;
  for (let year = firstAligned; year <= lastYear; year += step) {
    const value = new Date(year, 0, 1).getTime();
    if (value > minDate && value < maxDate) values.push(value);
  }
  values.push(maxDate);
  return values
    .sort((a, b) => a - b)
    .filter((value, index, array) => index === 0 || value - array[index - 1] > yearMs * 0.55)
    .map((value) => ({ value, label: String(new Date(value).getFullYear()) }));
}

function focusedTimelineDomain(dates: number[]) {
  const sorted = [...dates].sort((a, b) => a - b);
  const fullMin = sorted[0];
  const fullMax = sorted[sorted.length - 1];
  if (sorted.length < 3) return { fullMin, fullMax, focusMin: fullMin, focusMax: fullMax, hasOutlier: false };
  const yearMs = 365.25 * 24 * 60 * 60 * 1000;
  const fullSpan = Math.max(1, fullMax - fullMin);
  let focusMin = fullMin;
  let focusMax = fullMax;
  let hasOutlier = false;
  const earliestGap = sorted[1] - fullMin;
  const latestGap = fullMax - sorted[sorted.length - 2];
  if (fullSpan > yearMs * 30 && earliestGap > yearMs * 12 && earliestGap / fullSpan > 0.35) {
    focusMin = sorted[1];
    hasOutlier = true;
  }
  if (fullSpan > yearMs * 30 && latestGap > yearMs * 12 && latestGap / fullSpan > 0.35) {
    focusMax = sorted[sorted.length - 2];
    hasOutlier = true;
  }
  if (focusMax <= focusMin) return { fullMin, fullMax, focusMin: fullMin, focusMax: fullMax, hasOutlier: false };
  return { fullMin, fullMax, focusMin, focusMax, hasOutlier };
}

function StudyTimeline({ response }: { response: RelatedTrialResponse }) {
  const [showFullRange, setShowFullRange] = useState(false);
  const anchor = response.anchor_trial ?? {};
  const rows = [
    { nctId: text(response.seed_nct_id), title: text(anchor.brief_title, "Study of interest"), start: parseTrialDate(anchor.start_date), end: parseTrialDate(anchor.completion_date), enrollment: anchor.enrollment, reference: true },
    ...(response.matches ?? []).map((match) => ({ nctId: match.nct_id, title: text(match.trial?.brief_title, "Related study"), start: parseTrialDate(match.trial?.start_date), end: parseTrialDate(match.trial?.completion_date), enrollment: match.trial?.enrollment, reference: false })),
  ].filter((row) => row.start !== null || row.end !== null);
  if (!rows.length) return null;

  const dates = rows.flatMap((row) => [row.start, row.end].filter((value): value is number => value !== null));
  const domain = focusedTimelineDomain(dates);
  const coreMin = showFullRange ? domain.fullMin : domain.focusMin;
  const coreMax = showFullRange ? domain.fullMax : domain.focusMax;
  const coreSpan = Math.max(1, coreMax - coreMin);
  const padding = Math.max(coreSpan * 0.025, 45 * 24 * 60 * 60 * 1000);
  const minDate = coreMin - padding;
  const maxDate = coreMax + padding;
  const span = Math.max(1, maxDate - minDate);
  const ticks = timelineTicks(coreMin, coreMax);
  const rangeLabel = `${new Date(coreMin).getFullYear()}–${new Date(coreMax).getFullYear()}`;
  const clampPercent = (value: number) => Math.max(0, Math.min(100, ((value - minDate) / span) * 100));

  return <section className="study-timeline-card">
    <div className="study-workspace-heading timeline-heading"><div><span>Timeline</span><h3>Study timing at a glance</h3><p>{rangeLabel} · {rows.length} studies shown · exact dates are available on hover.</p></div>{domain.hasOutlier && <div className="timeline-view-toggle" role="group" aria-label="Timeline range"><button type="button" className={!showFullRange ? "active" : ""} onClick={() => setShowFullRange(false)}>Focused</button><button type="button" className={showFullRange ? "active" : ""} onClick={() => setShowFullRange(true)}>Full range</button></div>}</div>
    {domain.hasOutlier && !showFullRange && <div className="timeline-outlier-note"><Info size={15}/><span>An unusually distant reported date is outside the focused visual scale. No source value is changed; use <strong>Full range</strong> to include every reported date.</span></div>}
    <div className="visual-timeline-scroll">
      <div className="visual-timeline-head"><span>Study</span><div className="visual-timeline-axis" aria-label={`Timeline ${rangeLabel}`}>{ticks.map((tick) => <span key={`${tick.value}-${tick.label}`} style={{ left: `${clampPercent(tick.value)}%` }}>{tick.label}</span>)}</div><span>Enrollment</span></div>
      {rows.map((row) => {
        const rawStart = row.start ?? row.end ?? coreMin;
        const rawEnd = row.end ?? row.start ?? coreMax;
        const start = Math.min(rawStart, rawEnd);
        const end = Math.max(rawStart, rawEnd);
        const left = clampPercent(start);
        const right = clampPercent(end);
        const width = Math.max(1.4, right - left);
        const clipped = start < minDate || end > maxDate;
        const durationDays = Math.max(0, Math.round((end - start) / (24 * 60 * 60 * 1000)));
        const tooltip = `${row.nctId} · Start ${formatExactTimelineDate(row.start)} · Completion ${formatExactTimelineDate(row.end)}${row.start !== null && row.end !== null ? ` · ${durationDays.toLocaleString()} days` : ""}${clipped ? " · extends beyond focused range" : ""}`;
        return <div className={`visual-timeline-row ${row.reference ? "reference" : ""} ${clipped ? "timeline-row-clipped" : ""}`} key={`visual-${row.nctId}`}>
          <div className="visual-timeline-label"><strong>{row.nctId}</strong><span title={row.title}>{row.reference ? "Study of interest · reference" : row.title}</span></div>
          <div className="visual-timeline-track" title={tooltip} aria-label={tooltip}>{ticks.map((tick) => <span className="visual-timeline-gridline" aria-hidden="true" key={`line-${row.nctId}-${tick.value}`} style={{ left: `${clampPercent(tick.value)}%` }}/>) }<span className="visual-timeline-bar" style={{ left: `${left}%`, width: `${width}%` }}/>{row.start !== null && <span className="visual-timeline-endpoint start" style={{ left: `${clampPercent(row.start)}%` }}/>} {row.end !== null && <span className="visual-timeline-endpoint end" style={{ left: `${clampPercent(row.end)}%` }}/>}</div>
          <div className="visual-timeline-enrollment">{row.enrollment === null || row.enrollment === undefined ? "—" : Number(row.enrollment).toLocaleString()}</div>
        </div>;
      })}
    </div>
  </section>;
}

function StudiesWorkspace({ result, onEvidence }: { result: UiResult; onEvidence: () => void }) {
  const related = getRelatedTrialResponse(result);
  if (!related?.matches?.length) return <div className="workspace-view"><RelatedTrialEmptyState response={related ?? { matches: [] }}/></div>;
  return <div className="workspace-view studies-workspace">
    <div className="study-workspace-heading"><div><span>Related studies</span><h2>Review, filter and compare</h2><p>The study list stays visible while deeper comparison is opened only when you choose it.</p></div><strong>{related.matches.length} studies in this answer</strong></div>
    <AgenticRelatedInsights result={result} response={related} onEvidence={onEvidence}/>
    <StudyTimeline response={related}/>
  </div>;
}

function AgenticRelatedInsights({ result, response, onEvidence }: { result: UiResult; response: RelatedTrialResponse; onEvidence: () => void }) {
  const matches = response.matches ?? [];
  const aggregate = response.metrics ?? {};
  const synthesis = result.structured_synthesis ?? buildRelatedFallbackSynthesis(response);
  const findingCount = synthesis?.key_findings?.length ?? 0;
  const generation = result.generation;
  const anchor = response.anchor_trial ?? {};
  const studyNctId = text(response.seed_nct_id, "selected study");
  const studyOfInterestLabel = `study of interest (${studyNctId})`;
  const [selectedCompareIds, setSelectedCompareIds] = useState<string[]>([]);
  const [comparisonOpen, setComparisonOpen] = useState(false);
  const [showAllFindings, setShowAllFindings] = useState(false);
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [connectionFilter, setConnectionFilter] = useState("ALL");
  const [completionFilter, setCompletionFilter] = useState("ALL");
  const [enrollmentFilter, setEnrollmentFilter] = useState("ALL");
  const matchKey = matches.map((match) => match.nct_id).join("|");

  useEffect(() => {
    setSelectedCompareIds([]);
    setComparisonOpen(false);
    setShowAllFindings(false);
    setStatusFilter("ALL");
    setConnectionFilter("ALL");
    setCompletionFilter("ALL");
    setEnrollmentFilter("ALL");
  }, [response.seed_nct_id, matchKey]);

  useEffect(() => {
    if (!comparisonOpen) return;
    document.body.classList.add("trialiq-modal-open");
    return () => document.body.classList.remove("trialiq-modal-open");
  }, [comparisonOpen]);

  const relationshipLabel = (value: string | undefined) => {
    if (value === "HAS_CONDITION") return "Condition";
    if (value === "HAS_INTERVENTION") return "Intervention";
    if (value === "SPONSORED_BY") return "Sponsor";
    return text(value, "Connection");
  };
  const loadedValue = (value: unknown) => value === null || value === undefined || value === "" ? "Not reported in loaded evidence" : String(value);
  const hasValue = (value: unknown) => value !== null && value !== undefined && value !== "";
  const referencedComparison = (value: unknown) => {
    if (!hasValue(value)) return "Not reported in loaded evidence";
    const raw = String(value);
    if (!response.seed_nct_id) return raw.replace(/anchor trial/gi, "study of interest");
    return raw
      .replace(/the anchor trial/gi, `the study of interest (${studyNctId})`)
      .replace(/anchor trial/gi, `study of interest (${studyNctId})`)
      .replace(/the study of interest(?!\s*\()/gi, `the study of interest (${studyNctId})`)
      .replace(/study of interest(?!\s*\()/gi, `study of interest (${studyNctId})`);
  };
  const compactDelta = (value: number | null | undefined, unit: string) => value === null || value === undefined ? "—" : value === 0 ? `0 ${unit}` : `${value > 0 ? "+" : "−"}${Math.abs(value).toLocaleString()} ${unit}`;
  const humanStatus = humanStatusLabel;
  const resetComparisonSelection = () => {
    setSelectedCompareIds([]);
    setComparisonOpen(false);
  };

  const availableStatuses = Array.from(new Set(matches
    .map((match) => typeof match.trial?.overall_status === "string" ? match.trial.overall_status : "")
    .filter(Boolean))).sort();
  const connectionOptions = [
    { value: "HAS_CONDITION", label: "Condition", available: matches.some((match) => match.connected_via.some((path) => path.relationship_type === "HAS_CONDITION")) },
    { value: "HAS_INTERVENTION", label: "Intervention", available: matches.some((match) => match.connected_via.some((path) => path.relationship_type === "HAS_INTERVENTION")) },
    { value: "SPONSORED_BY", label: "Sponsor", available: matches.some((match) => match.connected_via.some((path) => path.relationship_type === "SPONSORED_BY")) },
  ].filter((option) => option.available);
  const completionFilterAvailable = matches.some((match) => typeof match.metrics?.completion_date_difference_days === "number");
  const enrollmentFilterAvailable = matches.some((match) => typeof match.metrics?.enrollment_difference === "number");

  const visibleMatches = matches.filter((match) => {
    const status = typeof match.trial?.overall_status === "string" ? match.trial.overall_status : "";
    if (statusFilter !== "ALL" && status !== statusFilter) return false;
    if (connectionFilter !== "ALL" && !match.connected_via.some((path) => path.relationship_type === connectionFilter)) return false;

    const completionDifference = match.metrics?.completion_date_difference_days;
    if (completionFilter === "BEFORE" && !(typeof completionDifference === "number" && completionDifference < 0)) return false;
    if (completionFilter === "AFTER" && !(typeof completionDifference === "number" && completionDifference > 0)) return false;
    if (completionFilter === "SAME" && completionDifference !== 0) return false;

    const enrollmentDifference = match.metrics?.enrollment_difference;
    if (enrollmentFilter === "MORE" && !(typeof enrollmentDifference === "number" && enrollmentDifference > 0)) return false;
    if (enrollmentFilter === "FEWER" && !(typeof enrollmentDifference === "number" && enrollmentDifference < 0)) return false;
    if (enrollmentFilter === "SAME" && enrollmentDifference !== 0) return false;
    return true;
  });
  const filtersActive = statusFilter !== "ALL" || connectionFilter !== "ALL" || completionFilter !== "ALL" || enrollmentFilter !== "ALL";

  const hasCompletionComparison = visibleMatches.some((match) => hasValue(match.metrics?.completion_date_comparison));
  const hasDurationComparison = visibleMatches.some((match) => hasValue(match.metrics?.duration_comparison));
  const hasEnrollmentComparison = visibleMatches.some((match) => hasValue(match.metrics?.enrollment_comparison));
  const hasAnyTimelineEvidence = [anchor, ...visibleMatches.map((match) => match.trial ?? {})].some((trial) =>
    hasValue(trial.start_date) || hasValue(trial.completion_date) || hasValue(trial.enrollment)
  );
  const synthesisLabel = generation?.method === "LLM"
    ? generation.degraded
      ? "Evidence-checked summary · validated findings"
      : "Evidence-checked TrialIQ summary"
    : "Evidence-supported summary";
  const fourthKpi = generation?.method === "DETERMINISTIC"
    ? { label: "Summary", value: "Evidence based" }
    : { label: "Evidence-checked findings", value: String(findingCount) };
  const relationshipScope = (response.relationship_types ?? []).map(relationshipLabel).join(" + ") || "Bounded graph relationships";
  const statusScope = (response.overall_statuses ?? []).map((value) => value.charAt(0) + value.slice(1).toLowerCase()).join(", ");

  const conditionLinked = aggregate.condition_linked_trial_count ?? matches.filter((match) => (match.metrics?.shared_condition_count ?? 0) > 0).length;
  const interventionLinked = aggregate.intervention_linked_trial_count ?? matches.filter((match) => (match.metrics?.shared_intervention_count ?? 0) > 0).length;
  const sponsorLinked = aggregate.sponsor_linked_trial_count ?? matches.filter((match) => (match.metrics?.shared_sponsor_count ?? 0) > 0).length;
  const multiFactorCount = aggregate.multi_factor_trial_count ?? matches.filter((match) => (match.metrics?.total_shared_entity_count ?? 0) > 1).length;

  const pickLargestAbsolute = (
    candidates: RelatedTrialMatch[],
    getter: (match: RelatedTrialMatch) => number | null | undefined,
  ): RelatedTrialMatch | null => {
    const comparable = candidates.filter((match) => typeof getter(match) === "number");
    if (!comparable.length) return null;
    return comparable.reduce((best, current) =>
      Math.abs(getter(current) as number) > Math.abs(getter(best) as number) ? current : best
    );
  };

  const standoutInsights: StandoutInsight[] = [];
  const connectionParts = [
    conditionLinked > 0 ? `${conditionLinked} condition-linked` : "",
    interventionLinked > 0 ? `${interventionLinked} intervention-linked` : "",
    sponsorLinked > 0 ? `${sponsorLinked} sponsor-linked` : "",
  ].filter(Boolean);
  if (connectionParts.length) {
    standoutInsights.push({
      key: "connection-pattern",
      label: "Connection pattern",
      value: `${matches.length} stud${matches.length === 1 ? "y" : "ies"}`,
      detail: connectionParts.join(" · "),
    });
  }
  if (multiFactorCount > 0) {
    standoutInsights.push({
      key: "multi-factor",
      label: "Multiple shared factors",
      value: `${multiFactorCount}/${matches.length}`,
      detail: `related stud${multiFactorCount === 1 ? "y shares" : "ies share"} two or more clinical factors with the ${studyOfInterestLabel}`,
    });
  }

  const completionStandout = pickLargestAbsolute(matches, (match) => match.metrics?.completion_date_difference_days);
  if (completionStandout?.metrics?.completion_date_comparison) {
    standoutInsights.push({
      key: "completion",
      label: "Largest completion difference",
      value: `${Math.abs(completionStandout.metrics.completion_date_difference_days as number)} days`,
      detail: `${completionStandout.nct_id}: ${referencedComparison(completionStandout.metrics.completion_date_comparison)}`,
    });
  }
  const enrollmentStandout = pickLargestAbsolute(matches, (match) => match.metrics?.enrollment_difference);
  if (enrollmentStandout?.metrics?.enrollment_comparison) {
    standoutInsights.push({
      key: "enrollment",
      label: "Largest enrollment difference",
      value: `${Math.abs(enrollmentStandout.metrics.enrollment_difference as number)} participants`,
      detail: `${enrollmentStandout.nct_id}: ${referencedComparison(enrollmentStandout.metrics.enrollment_comparison)}`,
    });
  }
  const durationStandout = pickLargestAbsolute(matches, (match) => match.metrics?.duration_difference_days);
  if (durationStandout?.metrics?.duration_comparison && standoutInsights.length < 4) {
    standoutInsights.push({
      key: "duration",
      label: "Largest duration difference",
      value: `${Math.abs(durationStandout.metrics.duration_difference_days as number)} days`,
      detail: `${durationStandout.nct_id}: ${referencedComparison(durationStandout.metrics.duration_comparison)}`,
    });
  }

  const selectedMatches = selectedCompareIds
    .map((nctId) => matches.find((match) => match.nct_id === nctId))
    .filter((match): match is RelatedTrialMatch => Boolean(match));
  const anchorDuration = selectedMatches
    .map((match) => match.metrics?.anchor_duration_days)
    .find((value): value is number => typeof value === "number")
    ?? matches.map((match) => match.metrics?.anchor_duration_days).find((value): value is number => typeof value === "number");
  const comparisonLimitReached = selectedCompareIds.length >= 3;
  const toggleCompare = (nctId: string) => {
    setSelectedCompareIds((current) => {
      if (current.includes(nctId)) {
        const next = current.filter((item) => item !== nctId);
        if (!next.length) setComparisonOpen(false);
        return next;
      }
      if (current.length >= 3) return current;
      return [...current, nctId];
    });
  };

  return <div className="agent-results-stack">
    {synthesis && <section className={`agent-insight-card agent-synthesis-card ${generation?.method === "DETERMINISTIC" ? "agent-synthesis-fallback" : ""}`}>
      <div className="agent-answer-meta">
        <span className="agent-answer-pill anchor-pill">Study of interest · {studyNctId}</span>
        <span className="agent-answer-pill">{statusScope ? `${statusScope} · ` : ""}{relationshipScope}</span>
        <span className={`agent-answer-pill ${generation?.method === "LLM" && !generation.degraded ? "success-pill" : "fallback-pill"}`}>{synthesisLabel}</span>
      </div>
      <div className="agent-answer-heading">
        <div>
          <span className="agent-answer-eyebrow">TrialIQ conclusion</span>
          <h3>{synthesis.headline}</h3>
        </div>
      </div>
      <p className="agent-synthesis-summary">{synthesis.summary}</p>
      <div className="agent-findings">
        {synthesis.key_findings.slice(0, showAllFindings ? synthesis.key_findings.length : 3).map((finding, index) => <div className="agent-finding" key={`${finding.statement}-${index}`}>
          <div className="agent-finding-index">{index + 1}</div>
          <div className="agent-finding-copy">
            <strong>{finding.statement}</strong>
            <div className="agent-finding-evidence">
              <span>{finding.evidence_ids.length} evidence reference{finding.evidence_ids.length === 1 ? "" : "s"}</span>
              <button type="button" className="inline-evidence-action" onClick={onEvidence}>Inspect evidence <ArrowRight size={13}/></button>
            </div>
          </div>
        </div>)}
      </div>
      {synthesis.key_findings.length > 3 && <button type="button" className="finding-toggle-button" onClick={() => setShowAllFindings((current) => !current)}>{showAllFindings ? "Show fewer findings" : `Show all ${synthesis.key_findings.length} findings`} <ChevronDown size={14} className={showAllFindings ? "rotated" : ""}/></button>}
    </section>}

    <div className="agent-kpi-grid" aria-label="Agentic result metrics">
      <Metric label="Analysed related studies" value={String(aggregate.related_trial_count ?? matches.length)}/>
      <Metric label="Shared factors" value={String(aggregate.unique_shared_entity_count ?? 0)}/>
      <Metric label="Supporting links" value={String(aggregate.evidence_path_count ?? 0)}/>
      <Metric label={fourthKpi.label} value={fourthKpi.value}/>
    </div>

    {!!standoutInsights.length && <section className="agent-insight-card standout-card">
      <div className="block-heading"><h3>What stands out</h3><span>Deterministic observations relative to {studyNctId}</span></div>
      <div className="standout-grid">
        {standoutInsights.slice(0, 4).map((insight) => <div className="standout-item" key={insight.key}>
          <span>{insight.label}</span>
          <strong>{insight.value}</strong>
          <p>{insight.detail}</p>
        </div>)}
      </div>
    </section>}

    <section className="related-study-refinement-card related-study-refinement-toolbar">
      <div className="block-heading refinement-heading">
        <div><h3>Refine studies</h3><span>Filter the included investigation set without changing the TrialIQ conclusion.</span></div>
        <strong>{visibleMatches.length} of {matches.length} included studies shown</strong>
      </div>
      <div className="related-study-filter-grid">
        {availableStatuses.length > 1 && <label><span>Status</span><select value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); resetComparisonSelection(); }}><option value="ALL">All statuses</option>{availableStatuses.map((status) => <option key={status} value={status}>{humanStatus(status)}</option>)}</select></label>}
        {connectionOptions.length > 1 && <label><span>Connection</span><select value={connectionFilter} onChange={(event) => { setConnectionFilter(event.target.value); resetComparisonSelection(); }}><option value="ALL">All connection types</option>{connectionOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>}
        {completionFilterAvailable && <label><span>Completion timing vs reference</span><select value={completionFilter} onChange={(event) => { setCompletionFilter(event.target.value); resetComparisonSelection(); }}><option value="ALL">Any timing</option><option value="BEFORE">Before reference</option><option value="AFTER">After reference</option><option value="SAME">Same date</option></select></label>}
        {enrollmentFilterAvailable && <label><span>Enrollment vs reference</span><select value={enrollmentFilter} onChange={(event) => { setEnrollmentFilter(event.target.value); resetComparisonSelection(); }}><option value="ALL">Any enrollment</option><option value="MORE">Higher than reference</option><option value="FEWER">Lower than reference</option><option value="SAME">Same enrollment</option></select></label>}
      </div>
      {filtersActive && <button type="button" className="refinement-clear-button" onClick={() => { setStatusFilter("ALL"); setConnectionFilter("ALL"); setCompletionFilter("ALL"); setEnrollmentFilter("ALL"); resetComparisonSelection(); }}>Clear filters</button>}
    </section>

    <section className="agent-insight-card comparison-primary-section">
      <div className="block-heading comparison-heading">
        <div><h3>Study comparison</h3><span>The reference study is pinned; choose up to 3 included studies for a side-by-side comparison.</span></div>
        <small>{result.human_review_decision ? `${result.human_review_decision.discovered_candidate_count} discovered · ${result.human_review_decision.selected_candidate_count} included in investigation` : `${matches.length} included in investigation`}</small>
      </div>
      {visibleMatches.length ? <div className="comparison-table-wrap">
        <table className="comparison-table">
          <thead><tr><th>Related study</th><th>Status</th><th>Shared connection</th>{hasCompletionComparison && <th className="numeric-column">Completion Δ</th>}{hasDurationComparison && <th className="numeric-column">Duration Δ</th>}{hasEnrollmentComparison && <th className="numeric-column">Enrollment Δ</th>}</tr></thead>
          <tbody>{visibleMatches.map((match) => {
            const selected = selectedCompareIds.includes(match.nct_id);
            return <tr key={match.nct_id} className={selected ? "comparison-row-selected" : ""}>
              <td><label className="comparison-study-selector"><input type="checkbox" checked={selected} disabled={!selected && comparisonLimitReached} aria-label={`Select ${match.nct_id} for comparison`} onChange={() => toggleCompare(match.nct_id)}/><span><strong>{match.nct_id}</strong><small title={text(match.trial?.brief_title, "Title unavailable")}>{text(match.trial?.brief_title, "Title unavailable")}</small></span></label></td>
              <td><span className={`clinical-status ${clinicalStatusClass(typeof match.trial?.overall_status === "string" ? match.trial.overall_status : null)}`}>{humanStatusLabel(typeof match.trial?.overall_status === "string" ? match.trial.overall_status : null)}</span></td>
              <td><div className="comparison-connection-pills">
                {!!match.metrics?.shared_condition_count && <span>{match.metrics.shared_condition_count} condition{match.metrics.shared_condition_count === 1 ? "" : "s"}</span>}
                {!!match.metrics?.shared_intervention_count && <span>{match.metrics.shared_intervention_count} intervention{match.metrics.shared_intervention_count === 1 ? "" : "s"}</span>}
                {!!match.metrics?.shared_sponsor_count && <span>{match.metrics.shared_sponsor_count} sponsor{match.metrics.shared_sponsor_count === 1 ? "" : "s"}</span>}
                <span>{match.metrics?.evidence_path_count ?? match.connected_via.length} supporting link{(match.metrics?.evidence_path_count ?? match.connected_via.length) === 1 ? "" : "s"}</span>
              </div></td>
              {hasCompletionComparison && <td className="numeric-column"><span className="comparison-delta" title={referencedComparison(match.metrics?.completion_date_comparison)}>{compactDelta(match.metrics?.completion_date_difference_days, "days")}</span></td>}
              {hasDurationComparison && <td className="numeric-column"><span className="comparison-delta" title={referencedComparison(match.metrics?.duration_comparison)}>{compactDelta(match.metrics?.duration_difference_days, "days")}</span></td>}
              {hasEnrollmentComparison && <td className="numeric-column"><span className="comparison-delta" title={referencedComparison(match.metrics?.enrollment_comparison)}>{compactDelta(match.metrics?.enrollment_difference, "participants")}</span></td>}
            </tr>;
          })}</tbody>
        </table>
      </div> : <div className="refinement-zero-state"><strong>No related studies match the current filters.</strong><span>Clear or change a filter to bring studies back into the comparison view.</span></div>}
      <div className="compare-selection-bar">
        <div><strong>{selectedCompareIds.length} selected for comparison</strong><span>{comparisonLimitReached ? "Maximum of 3 related studies reached" : "Reference study is included automatically"}</span></div>
        <div>
          {!!selectedCompareIds.length && <button type="button" className="comparison-clear-button" onClick={() => { setSelectedCompareIds([]); setComparisonOpen(false); }}>Clear</button>}
          <button type="button" className="secondary-button comparison-open-button" disabled={selectedCompareIds.length < 1} onClick={() => setComparisonOpen(true)}>Compare {selectedCompareIds.length || "selected"} stud{selectedCompareIds.length === 1 ? "y" : "ies"} <ArrowRight size={15}/></button>
        </div>
      </div>
    </section>

    {comparisonOpen && selectedMatches.length >= 1 && <div className="trialiq-modal-backdrop comparison-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setComparisonOpen(false); }}><section className="trialiq-modal comparison-modal-panel" role="dialog" aria-modal="true" aria-labelledby="comparison-modal-title" onMouseDown={(event) => event.stopPropagation()}>
      <header className="trialiq-modal-header comparison-modal-header">
        <div><span>Study comparison</span><h2 id="comparison-modal-title">Compare selected studies</h2><p>Reference: <strong>{studyNctId}</strong> · {selectedMatches.length} related stud{selectedMatches.length === 1 ? "y" : "ies"}. Values are aligned by measure so differences can be scanned horizontally.</p></div>
        <button type="button" className="icon-button modal-close-button" onClick={() => setComparisonOpen(false)} aria-label="Close study comparison"><X size={18}/></button>
      </header>
      <div className="trialiq-modal-body comparison-modal-body">
        <div className="comparison-matrix-wrap">
          <table className="comparison-matrix">
            <thead><tr><th className="comparison-attribute-column">Measure</th><th className="comparison-reference-column"><span>Reference</span><strong>{studyNctId}</strong><small title={text(anchor.brief_title, "Title unavailable")}>{text(anchor.brief_title, "Title unavailable")}</small></th>{selectedMatches.map((match) => <th key={`head-${match.nct_id}`}><span>Related study</span><strong>{match.nct_id}</strong><small title={text(match.trial?.brief_title, "Title unavailable")}>{text(match.trial?.brief_title, "Title unavailable")}</small></th>)}</tr></thead>
            <tbody>
              <tr><th>Status</th><td><span className={`clinical-status ${clinicalStatusClass(typeof anchor.overall_status === "string" ? anchor.overall_status : null)}`}>{humanStatusLabel(typeof anchor.overall_status === "string" ? anchor.overall_status : null)}</span></td>{selectedMatches.map((match) => <td key={`status-${match.nct_id}`}><span className={`clinical-status ${clinicalStatusClass(typeof match.trial?.overall_status === "string" ? match.trial.overall_status : null)}`}>{humanStatusLabel(typeof match.trial?.overall_status === "string" ? match.trial.overall_status : null)}</span></td>)}</tr>
              <tr><th>Shared factors</th><td>—</td>{selectedMatches.map((match) => <td className="numeric-column" key={`shared-${match.nct_id}`}>{match.metrics?.total_shared_entity_count ?? match.connected_via.length}</td>)}</tr>
              <tr><th>Start date</th><td>{loadedValue(anchor.start_date)}</td>{selectedMatches.map((match) => <td key={`start-${match.nct_id}`}>{loadedValue(match.trial?.start_date)}</td>)}</tr>
              <tr><th>Completion date</th><td>{loadedValue(anchor.completion_date)}</td>{selectedMatches.map((match) => <td key={`completion-${match.nct_id}`}>{loadedValue(match.trial?.completion_date)}</td>)}</tr>
              <tr><th>Enrollment</th><td className="numeric-column">{loadedValue(anchor.enrollment)}</td>{selectedMatches.map((match) => <td className="numeric-column" key={`enrollment-${match.nct_id}`}>{loadedValue(match.metrics?.related_enrollment ?? match.trial?.enrollment)}</td>)}</tr>
              <tr><th>Study duration</th><td className="numeric-column">{anchorDuration === undefined ? "—" : `${anchorDuration.toLocaleString()} d`}</td>{selectedMatches.map((match) => <td className="numeric-column" key={`duration-${match.nct_id}`}>{match.metrics?.related_duration_days === null || match.metrics?.related_duration_days === undefined ? "—" : `${match.metrics.related_duration_days.toLocaleString()} d`}</td>)}</tr>
              <tr><th>Completion Δ</th><td>Reference</td>{selectedMatches.map((match) => <td className="numeric-column" key={`completion-delta-${match.nct_id}`}><span className="comparison-delta" title={referencedComparison(match.metrics?.completion_date_comparison)}>{compactDelta(match.metrics?.completion_date_difference_days, "days")}</span></td>)}</tr>
              <tr><th>Duration Δ</th><td>Reference</td>{selectedMatches.map((match) => <td className="numeric-column" key={`duration-delta-${match.nct_id}`}><span className="comparison-delta" title={referencedComparison(match.metrics?.duration_comparison)}>{compactDelta(match.metrics?.duration_difference_days, "days")}</span></td>)}</tr>
              <tr><th>Enrollment Δ</th><td>Reference</td>{selectedMatches.map((match) => <td className="numeric-column" key={`enrollment-delta-${match.nct_id}`}><span className="comparison-delta" title={referencedComparison(match.metrics?.enrollment_comparison)}>{compactDelta(match.metrics?.enrollment_difference, "participants")}</span></td>)}</tr>
            </tbody>
          </table>
        </div>
      </div>
      <footer className="trialiq-modal-footer comparison-modal-footer"><div><strong>{selectedMatches.length + 1} studies compared</strong><span>Hover compact deltas in the underlying table for the full source-backed comparison wording.</span></div><button type="button" className="secondary-button" onClick={() => setComparisonOpen(false)}>Close comparison</button></footer>
    </section></div>}

    <details className="agent-insight-card agent-collapsible-card">
      <summary className="agent-collapsible-summary">
        <div><h3>Why these studies are connected</h3><span>Shared with the study of interest ({studyNctId})</span></div>
        <div className="agent-collapsible-meta"><strong>{visibleMatches.length}</strong><span>analysed studies</span><ChevronDown size={16}/></div>
      </summary>
      <div className="agent-collapsible-body">
        {visibleMatches.length ? <div className="connection-groups">{visibleMatches.map((match) => <div className="connection-group" key={match.nct_id}>
          <div className="connection-group-title">
            <div><strong>{match.nct_id}</strong><span>{text(match.trial?.brief_title, "Related trial")}</span></div>
            <span className="connection-hop">{match.discovery_hop === 1 ? "Direct connection" : `Connection level ${match.discovery_hop}`}</span>
          </div>
          <div className="entity-chip-grid">{match.connected_via.map((path, index) => <div className="entity-chip" key={`${match.nct_id}-${path.entity_id ?? index}`}>
            <div className="entity-chip-head"><span className="entity-type-pill">{relationshipLabel(path.relationship_type)}</span><small>Shared factor</small></div>
            <strong>{text(path.entity?.name ?? path.entity?.normalized_name)}</strong>
            {path.entity_id && <details className="entity-technical-id"><summary>Technical identifier</summary><code>{path.entity_id}</code></details>}
            <small>Shared with {text(path.source_nct_id, studyNctId)}</small>
          </div>)}</div>
        </div>)}</div> : <div className="refinement-zero-state"><strong>No connection cards match the current filters.</strong><span>The evidence is still retained; clear the filters to restore the full result set.</span></div>}
      </div>
    </details>

    {hasAnyTimelineEvidence ? <details className="agent-insight-card agent-collapsible-card">
      <summary className="agent-collapsible-summary">
        <div><h3>Timeline & enrollment</h3><span>Reference study is pinned above</span></div>
        <div className="agent-collapsible-meta"><strong>{visibleMatches.length + 1}</strong><span>rows</span><ChevronDown size={16}/></div>
      </summary>
      <div className="agent-collapsible-body">
        <div className="timeline-table-wrap">
          <table className="timeline-table">
            <thead><tr><th>Trial</th><th>Start</th><th>Completion</th><th>Enrollment</th></tr></thead>
            <tbody>
              <tr className="anchor-row"><td><strong>{studyNctId}</strong><span>Reference</span></td><td>{loadedValue(anchor.start_date)}</td><td>{loadedValue(anchor.completion_date)}</td><td>{loadedValue(anchor.enrollment)}</td></tr>
              {visibleMatches.map((match) => <tr key={`timeline-${match.nct_id}`}><td><strong>{match.nct_id}</strong><span>{text(match.trial?.overall_status)}</span></td><td>{loadedValue(match.trial?.start_date)}</td><td>{loadedValue(match.trial?.completion_date)}</td><td>{loadedValue(match.trial?.enrollment)}</td></tr>)}
            </tbody>
          </table>
        </div>
      </div>
    </details> : <section className="agent-insight-card data-availability-card">
      <div className="data-availability-icon"><Info size={18}/></div>
      <div><span className="data-availability-label">Data availability</span><strong>Timeline & enrollment comparison unavailable</strong><p>Start dates, completion dates, and enrollment are not available in the loaded study records for these studies. TrialIQ does not fill in missing values.</p></div>
    </section>}

    <details className="agent-technical-details">
      <summary>Technical details & raw response</summary>
      <div className="agent-technical-body">
        <div>
          <strong>Raw grounded response</strong>
          <div className="technical-answer"><MarkdownAnswer content={text(result.answer, "No raw grounded response was returned.")}/></div>
        </div>
        {!!generation?.grounding_errors?.length && <div>
          <strong>Grounding validation diagnostics</strong>
          <ul>{generation.grounding_errors.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
        </div>}
      </div>
    </details>
  </div>;
}

function RelatedTrialEmptyState({ response }: { response: RelatedTrialResponse }) {
  const matches = Array.isArray(response.matches) ? response.matches.length : 0;
  return <div className="bounded-empty">
    <div className="bounded-empty-icon"><Network size={20}/></div>
    <div className="bounded-empty-copy">
      <strong>No related studies were found within the current search scope.</strong>
      <p>The search completed successfully, but no connected studies matched the current criteria.</p>
    </div>
    <div className="bounded-metrics" aria-label="Related-trial search bounds">
      <Metric label="Study of interest" value={text(response.seed_nct_id)}/>
      <Metric label="Search distance" value={response.max_hops === 1 ? "Direct" : `${response.max_hops ?? 0} steps`}/>
      <Metric label="Studies per step" value={text(response.per_hop_limit)}/>
      <Metric label="Maximum results" value={text(response.limit)}/>
      <Metric label="Analysed related studies" value={String(matches)}/>
    </div>
  </div>;
}


function Metric({ label, value }: { label: string; value: string }) {
  return <div className="bounded-metric"><span>{label}</span><strong>{value}</strong></div>;
}

function EvidenceWorkspace({ result, tab, setTab }: { result: UiResult; tab: WorkspaceTab; setTab: (tab: WorkspaceTab) => void }) {
  const trace = getTrace(result);
  const seedNct = getRelatedTrialResponse(result)?.seed_nct_id ?? getEvidence(result)?.nct_id;
  return <section className="panel evidence-panel">
    <div className="workspace-header">
      <div><div className="section-kicker"><ShieldCheck size={16}/> Supporting evidence</div><h2>{text(seedNct, text(result.run_id, "Latest query"))}</h2></div>
      {result.run_id && <div className="run-id"><span>Run ID</span><code>{result.run_id}</code></div>}
    </div>
    <div className="workspace-tabs" role="tablist" aria-label="Supporting evidence views">
      <TabButton active={tab === "evidence"} onClick={() => setTab("evidence")} icon={<Database size={16}/>} label="Evidence"/>
      <TabButton active={tab === "graph"} onClick={() => setTab("graph")} icon={<Waypoints size={16}/>} label="Connections"/>
      <TabButton active={tab === "execution"} onClick={() => setTab("execution")} icon={<TimerReset size={16}/>} label={`How TrialIQ reached this result${trace.length ? ` · ${trace.length}` : ""}`}/>
    </div>
    {tab === "evidence" && <EvidenceView result={result}/>}
    {tab === "graph" && <GraphView result={result}/>}
    {tab === "execution" && <ExecutionView result={result}/>}
  </section>;
}
function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: ReactNode; label: string }) {
  return <button type="button" role="tab" aria-selected={active} className={active ? "workspace-tab active" : "workspace-tab"} onClick={onClick}>{icon}{label}</button>;
}

function EvidenceView({ result }: { result: UiResult }) {
  const embeddedEvidence = getEvidence(result);
  const embeddedValidation = getValidation(result);
  const embeddedSources = Array.isArray(result.sources) ? result.sources : [];
  const seedNct = getRelatedTrialResponse(result)?.seed_nct_id ?? embeddedEvidence?.nct_id;

  const [lineage, setLineage] = useState<LineageResponse | null>(null);
  const [lineageLoading, setLineageLoading] = useState(false);
  const [lineageError, setLineageError] = useState("");

  useEffect(() => {
    if (!seedNct) {
      setLineage(null);
      setLineageError("");
      setLineageLoading(false);
      return;
    }

    const controller = new AbortController();
    setLineageLoading(true);
    setLineageError("");

    fetch(`${API_BASE_URL}/api/v1/lineage/trials/${encodeURIComponent(seedNct)}`, { signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          const detail = payload?.detail;
          throw new Error(typeof detail === "string" ? detail : "Source records could not be loaded.");
        }
        return payload as LineageResponse;
      })
      .then((payload) => setLineage(payload))
      .catch((error) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setLineage(null);
        setLineageError(error instanceof Error ? error.message : "Source records could not be loaded.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLineageLoading(false);
      });

    return () => controller.abort();
  }, [seedNct]);

  const lineageRecords = Array.isArray(lineage?.records) ? lineage.records : [];
  const hasLiveLineage = lineage?.status === "SUCCESS" && Array.isArray(lineage?.records);
  const waitingForLineage = Boolean(seedNct && lineageLoading && lineage === null);
  const validation = hasLiveLineage && lineage?.validation ? lineage.validation : embeddedValidation;
  const sources: Source[] = hasLiveLineage
    ? lineageRecords
        .filter((record) => record.source_key != null || record.source_id != null)
        .map((record) => ({
          source_table: record.source_table,
          source_key: record.source_key,
          source_id: record.source_id,
          source_database: record.source_database,
          source_schema: record.source_schema,
          source_nct_id: record.source_nct_id,
        }))
    : embeddedSources;

  const recordsForCollection = (key: typeof collections[number]): Record<string, unknown>[] => {
    if (hasLiveLineage) {
      return lineageRecords
        .filter((record) => record.collection === key)
        .map((record) => ({ ...record }));
    }
    return embeddedEvidence?.[key] ?? [];
  };

  const validationValue = validation.valid === true
    ? "Verified"
    : validation.valid === false
      ? "Requires review"
      : "Not reported";
  const [selectedCollection, setSelectedCollection] = useState<typeof collections[number] | null>(null);
  const categoryRows = collections.map((key) => ({ key, records: recordsForCollection(key) }));
  const visibleCategories = categoryRows.filter((item) => item.records.length > 0);
  const selectedRecords = selectedCollection ? recordsForCollection(selectedCollection) : [];

  return <div className="workspace-view compact-evidence-view">
    <section className="evidence-overview-card">
      <div className="evidence-overview-status">
        <div className={`evidence-status-icon ${validation.valid === true ? "success" : validation.valid === false ? "danger" : "neutral"}`}>{validation.valid === true ? <CheckCircle2 size={22}/> : <ShieldCheck size={22}/>}</div>
        <div><span>Evidence supporting this answer</span><h2>{waitingForLineage ? "Loading source records…" : validationValue}</h2><p>{seedNct ? `Source-backed evidence for the study of interest (${seedNct}).` : "Source-backed evidence for this result."}</p></div>
      </div>
      <div className="evidence-overview-metrics">
        <div><strong>{waitingForLineage ? "—" : sources.length}</strong><span>source records</span></div>
        <div><strong>{waitingForLineage ? "—" : validation.warnings?.length ?? 0}</strong><span>warnings</span></div>
        <div><strong>{waitingForLineage ? "—" : validation.errors?.length ?? 0}</strong><span>errors</span></div>
      </div>
    </section>

    {lineageError && <div className="evidence-inline-notice warning" role="status"><CircleAlert size={16}/><div><strong>Source records could not be loaded.</strong><span>{lineageError} Embedded response evidence is shown where available.</span></div></div>}
    {!!validation.errors?.length && <MessageList title="Validation errors" messages={validation.errors} kind="error"/>}
    {!!validation.warnings?.length && <MessageList title="Validation warnings" messages={validation.warnings} kind="warning"/>}

    <section className="evidence-category-card">
      <div className="study-workspace-heading"><div><span>Source categories</span><h3>Open only what you need to inspect</h3><p>Technical identifiers stay behind the selected category rather than filling the page.</p></div><strong>{hasLiveLineage ? `${lineageRecords.length} records` : `${sources.length} references`}</strong></div>
      <div className="evidence-category-list">
        {visibleCategories.length ? visibleCategories.map(({ key, records }) => <button type="button" className="evidence-category-row" key={key} onClick={() => setSelectedCollection(key)}>
          <span className="evidence-category-icon"><Database size={17}/></span>
          <span><strong>{collectionLabel(key)}</strong><small>{records.length} source record{records.length === 1 ? "" : "s"}</small></span>
          <ArrowRight size={16}/>
        </button>) : <div className="evidence-empty-row"><Database size={18}/><span>No source categories were returned for this result.</span></div>}
      </div>
    </section>

    <details className="technical-evidence-disclosure">
      <summary>Technical source details <ChevronDown size={14}/></summary>
      <div className="technical-evidence-body">
        <div className="source-grid compact-source-grid">{sources.map((source, i) => <div className="source-card source-card-audited" key={`${source.source_key ?? i}`}>
          <div className="source-card-top"><span>Reference {i + 1}</span><span className="source-status-dot">source</span></div>
          <strong>{collectionLabel(source.source_table ?? "source")}</strong>
          <small className="source-key">Record {source.source_id ?? i + 1}</small>
        </div>)}</div>
        <details className="raw-response"><summary><span><Database size={14}/> Technical audit payload</span><ChevronDown size={15}/></summary><pre>{JSON.stringify({ query_result: result, lineage_response: lineage }, null, 2)}</pre></details>
      </div>
    </details>

    {selectedCollection && <div className="evidence-drawer-backdrop" role="presentation" onClick={() => setSelectedCollection(null)}>
      <aside className="evidence-detail-drawer" role="dialog" aria-modal="true" aria-label={`${collectionLabel(selectedCollection)} evidence`} onClick={(event) => event.stopPropagation()}>
        <div className="evidence-drawer-header"><div><span>Source evidence</span><h3>{collectionLabel(selectedCollection)}</h3><p>{selectedRecords.length} record{selectedRecords.length === 1 ? "" : "s"} supporting the study of interest.</p></div><button type="button" className="icon-button" onClick={() => setSelectedCollection(null)} aria-label="Close evidence details"><X size={18}/></button></div>
        <div className="evidence-drawer-records">{selectedRecords.length ? selectedRecords.map((record, index) => <ReadableRecord key={`${selectedCollection}-${index}`} record={record}/>) : <p className="muted">No records returned.</p>}</div>
      </aside>
    </div>}
  </div>;
}

function truncateGraphLabel(value: string, max = 26) {
  return value.length <= max ? value : `${value.slice(0, Math.max(1, max - 1))}…`;
}

function splitGraphLabel(value: string, maxPerLine = 24) {
  const normalized = value.trim();
  if (normalized.length <= maxPerLine) return [normalized];
  const words = normalized.split(/\s+/);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxPerLine || !current) current = candidate;
    else { lines.push(current); current = word; }
    if (lines.length === 1 && current.length > maxPerLine) break;
  }
  if (current && lines.length < 2) lines.push(current);
  const visibleLines = lines.slice(0, 2);
  if (visibleLines.length === 2 && visibleLines.join(" ").length < normalized.length) {
    visibleLines[1] = truncateGraphLabel(visibleLines[1], maxPerLine);
  }
  return visibleLines;
}

function graphRelationshipLabel(value: GraphRelationship) {
  if (value === "HAS_CONDITION") return "Condition";
  if (value === "HAS_INTERVENTION") return "Intervention";
  return "Sponsor";
}

function graphConnectionDepthLabel(depth: number) {
  if (depth <= 0) return "Study of interest";
  return depth === 1 ? "Direct connection" : "2-step connection";
}

function buildGraphLayout(nodes: GraphViewNode[], maxHops: number) {
  const grouped = new Map<number, GraphViewNode[]>();
  for (const node of nodes) {
    const column = node.type === "trial" ? node.hop * 2 : Math.max(1, node.hop * 2 - 1);
    grouped.set(column, [...(grouped.get(column) ?? []), node]);
  }
  for (const group of grouped.values()) group.sort((a, b) => a.label.localeCompare(b.label));

  const maxRowsPerLane = 6;
  const visibleRows = Math.max(1, ...Array.from(grouped.values()).map((group) => Math.min(maxRowsPerLane, group.length)));
  const height = Math.max(440, visibleRows * 92 + 120);
  const positions = new Map<string, { x: number; y: number }>();
  let cursorX = 110;

  for (const column of Array.from(grouped.keys()).sort((a, b) => a - b)) {
    const group = grouped.get(column) ?? [];
    const laneCount = Math.max(1, Math.ceil(group.length / maxRowsPerLane));
    group.forEach((node, index) => {
      const lane = Math.floor(index / maxRowsPerLane);
      const row = index % maxRowsPerLane;
      const rowsInLane = Math.min(maxRowsPerLane, group.length - lane * maxRowsPerLane);
      const x = cursorX + lane * 188;
      const y = ((row + 1) / (rowsInLane + 1)) * height;
      positions.set(node.id, { x, y });
    });
    cursorX += laneCount * 188 + 86;
  }

  const width = Math.max(maxHops === 2 ? 1180 : 760, cursorX + 30);
  return { positions, width, height };
}

function findGraphPath(seedId: string, targetId: string, edges: GraphViewEdge[]) {
  if (!seedId || !targetId || seedId === targetId) return null;
  const adjacency = new Map<string, Array<{ nodeId: string; edgeId: string }>>();
  for (const edge of edges) {
    adjacency.set(edge.source, [...(adjacency.get(edge.source) ?? []), { nodeId: edge.target, edgeId: edge.id }]);
    adjacency.set(edge.target, [...(adjacency.get(edge.target) ?? []), { nodeId: edge.source, edgeId: edge.id }]);
  }

  const previous = new Map<string, { nodeId: string; edgeId: string } | null>([[seedId, null]]);
  const queue = [seedId];
  for (let index = 0; index < queue.length && !previous.has(targetId); index += 1) {
    const current = queue[index];
    for (const next of adjacency.get(current) ?? []) {
      if (previous.has(next.nodeId)) continue;
      previous.set(next.nodeId, { nodeId: current, edgeId: next.edgeId });
      queue.push(next.nodeId);
      if (next.nodeId === targetId) break;
    }
  }
  if (!previous.has(targetId)) return null;

  const nodeIds = [targetId];
  const edgeIds: string[] = [];
  let cursor = targetId;
  while (cursor !== seedId) {
    const step = previous.get(cursor);
    if (!step) return null;
    edgeIds.unshift(step.edgeId);
    cursor = step.nodeId;
    nodeIds.unshift(cursor);
  }
  return { nodeIds, edgeIds };
}

function buildGraphConnectionRows(nodes: GraphViewNode[], edges: GraphViewEdge[], seedId: string): GraphConnectionRow[] {
  if (!seedId) return [];
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const edgeById = new Map(edges.map((edge) => [edge.id, edge]));
  const rows: GraphConnectionRow[] = [];

  for (const study of nodes.filter((node) => node.type === "trial" && node.id !== seedId)) {
    const path = findGraphPath(seedId, study.id, edges);
    if (!path) continue;
    const pathEdges = path.edgeIds.map((id) => edgeById.get(id)).filter((edge): edge is GraphViewEdge => Boolean(edge));
    const whyConnected = Array.from(new Set(pathEdges.map((edge) => graphRelationshipLabel(edge.relationship)))).join(" + ") || "Shared clinical entity";
    const sharedEntity = Array.from(new Set(
      path.nodeIds
        .map((id) => nodeById.get(id))
        .filter((node): node is GraphViewNode => Boolean(node && node.type !== "trial"))
        .map((node) => node.label),
    )).join(" → ") || "Shared entity";
    rows.push({
      studyId: study.id,
      studyLabel: study.label,
      whyConnected,
      sharedEntity,
      depth: study.hop,
      depthLabel: graphConnectionDepthLabel(study.hop),
      pathNodeIds: path.nodeIds,
      pathEdgeIds: path.edgeIds,
    });
  }

  return rows.sort((a, b) => a.depth - b.depth || a.studyLabel.localeCompare(b.studyLabel));
}

function GraphNodeShape({ node, x, y, selected, onPath, muted, onSelect }: { node: GraphViewNode; x: number; y: number; selected: boolean; onPath: boolean; muted: boolean; onSelect: () => void }) {
  const activate = (event: KeyboardEvent<SVGGElement>) => {
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(); }
  };
  const labelLines = splitGraphLabel(node.label, node.type === "trial" ? 20 : 23);
  const typeLabel = node.type === "trial"
    ? node.hop === 0 ? "STUDY OF INTEREST" : `CONNECTED STUDY · ${node.hop === 1 ? "DIRECT" : "2-STEP"}`
    : `${collectionLabel(node.type).toUpperCase()} · ${node.hop === 1 ? "DIRECT" : "2-STEP"}`;
  const nodeWidth = node.type === "trial" ? 176 : 166;
  const nodeHeight = node.type === "trial" ? 76 : 72;
  return <g className={`graphrag-node graph-node-${node.type} ${selected ? "selected" : ""} ${onPath ? "is-path" : ""} ${muted ? "is-muted" : ""}`} role="button" tabIndex={0}
    aria-label={`${node.type} ${node.label}, ${graphConnectionDepthLabel(node.hop)}`} onClick={onSelect} onKeyDown={activate}>
    <title>{`${node.type}: ${node.label}`}</title>
    {node.type === "condition" ? <ellipse cx={x} cy={y} rx={nodeWidth / 2} ry={nodeHeight / 2}/> :
      node.type === "intervention" ? <polygon points={`${x - nodeWidth / 2},${y} ${x - nodeWidth / 2 + 24},${y - nodeHeight / 2} ${x + nodeWidth / 2 - 24},${y - nodeHeight / 2} ${x + nodeWidth / 2},${y} ${x + nodeWidth / 2 - 24},${y + nodeHeight / 2} ${x - nodeWidth / 2 + 24},${y + nodeHeight / 2}`}/> :
      node.type === "sponsor" ? <rect x={x - nodeWidth / 2} y={y - nodeHeight / 2} width={nodeWidth} height={nodeHeight} rx={nodeHeight / 2}/> :
      <rect x={x - nodeWidth / 2} y={y - nodeHeight / 2} width={nodeWidth} height={nodeHeight} rx="12"/>}
    <text className="graphrag-node-type" x={x} y={y - 13} textAnchor="middle">{typeLabel}</text>
    <text className="graphrag-node-label" x={x} y={labelLines.length > 1 ? y + 5 : y + 10} textAnchor="middle">
      {labelLines.map((line, index) => <tspan key={`${node.id}-label-${index}`} x={x} dy={index === 0 ? 0 : 14}>{line}</tspan>)}
    </text>
  </g>;
}

function csvCell(value: unknown) {
  const normalized = value === null || value === undefined ? "" : String(value);
  return `"${normalized.replace(/"/g, '""')}"`;
}

function downloadClientFile(filename: string, content: BlobPart, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

async function copyClientText(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("Clipboard copy is unavailable in this browser.");
}

function GraphView({ result }: { result: UiResult }) {
  const evidence = getEvidence(result);
  const related = getRelatedTrialResponse(result);
  const seedNct = related?.seed_nct_id ?? evidence?.nct_id;
  const analysedMatches = related?.matches ?? [];
  const reportedDepth = related?.max_hops === 2 ? 2 : 1;
  const [maxHops, setMaxHops] = useState<1 | 2>(reportedDepth);
  const [graph, setGraph] = useState<GraphViewResponse | null>(null);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [graphError, setGraphError] = useState("");
  const [relationshipFilter, setRelationshipFilter] = useState<GraphFilter>("ALL");
  const [selection, setSelection] = useState<GraphSelection>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [visibleEntityStudies, setVisibleEntityStudies] = useState(5);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [expandedScope, setExpandedScope] = useState(false);
  const [displayMode, setDisplayMode] = useState<GraphDisplayMode>("network");
  const [frameCollapsed, setFrameCollapsed] = useState(false);
  const [frameMaximized, setFrameMaximized] = useState(false);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");
  const [viewport, setViewport] = useState({ x: 0, y: 0, width: 720, height: 420 });
  const [dragState, setDragState] = useState<{ pointerId: number; clientX: number; clientY: number; viewX: number; viewY: number } | null>(null);
  const graphSvgRef = useRef<SVGSVGElement | null>(null);

  const connectionEntities = useMemo(() => {
    const groups = new Map<string, {
      id: string;
      relationship: GraphRelationship;
      label: string;
      fanout: number | null;
      matches: RelatedTrialMatch[];
    }>();
    for (const match of analysedMatches) {
      for (const path of match.connected_via ?? []) {
        const relationship = path.relationship_type as GraphRelationship | undefined;
        if (!relationship || !["HAS_CONDITION", "HAS_INTERVENTION", "SPONSORED_BY"].includes(relationship)) continue;
        const entity = path.entity ?? {};
        const label = text(entity.name ?? entity.normalized_name ?? entity.canonical_key, "Shared factor");
        const identity = path.entity_id ?? `${relationship}:${text(entity.canonical_key ?? entity.normalized_name ?? entity.name, label)}`;
        const fanoutValue = Number(entity.loaded_trial_count ?? entity.trial_count ?? NaN);
        const existing = groups.get(identity) ?? {
          id: identity,
          relationship,
          label,
          fanout: Number.isFinite(fanoutValue) ? fanoutValue : null,
          matches: [],
        };
        if (!existing.matches.some((item) => item.nct_id === match.nct_id)) existing.matches.push(match);
        if (existing.fanout === null && Number.isFinite(fanoutValue)) existing.fanout = fanoutValue;
        groups.set(identity, existing);
      }
    }
    return Array.from(groups.values()).sort((a, b) => {
      if (a.relationship !== b.relationship) return a.relationship.localeCompare(b.relationship);
      if (a.matches.length !== b.matches.length) return b.matches.length - a.matches.length;
      const fanoutA = a.fanout ?? Number.MAX_SAFE_INTEGER;
      const fanoutB = b.fanout ?? Number.MAX_SAFE_INTEGER;
      return fanoutA - fanoutB || a.label.localeCompare(b.label);
    });
  }, [analysedMatches]);

  const analysisGraph = useMemo<GraphViewResponse>(() => {
    const seedId = `trial:${seedNct ?? "unknown"}`;
    const nodes = new Map<string, GraphViewNode>();
    const edges = new Map<string, GraphViewEdge>();
    if (seedNct) {
      nodes.set(seedId, {
        id: seedId,
        type: "trial",
        label: seedNct,
        hop: 0,
        metadata: related?.anchor_trial ?? evidence?.trial ?? {},
      });
    }
    for (const match of analysedMatches) {
      const relatedTrialId = `trial:${match.nct_id}`;
      nodes.set(relatedTrialId, { id: relatedTrialId, type: "trial", label: match.nct_id, hop: match.discovery_hop, metadata: match.trial });
      for (let pathIndex = 0; pathIndex < (match.connected_via ?? []).length; pathIndex += 1) {
        const path = match.connected_via[pathIndex];
        const relationship = path.relationship_type as GraphRelationship | undefined;
        if (!relationship || !["HAS_CONDITION", "HAS_INTERVENTION", "SPONSORED_BY"].includes(relationship)) continue;
        const entity = path.entity ?? {};
        const entityType: GraphNodeType = relationship === "HAS_CONDITION" ? "condition" : relationship === "HAS_INTERVENTION" ? "intervention" : "sponsor";
        const entityId = path.entity_id ?? `${entityType}:${text(entity.canonical_key ?? entity.normalized_name ?? entity.name, `${match.nct_id}-${pathIndex}`)}`;
        nodes.set(entityId, { id: entityId, type: entityType, label: text(entity.name ?? entity.normalized_name ?? entity.canonical_key, "Shared factor"), hop: match.discovery_hop, metadata: entity });
        const sourceNctId = text(path.source_nct_id, seedNct ?? "");
        const sourceTrialId = `trial:${sourceNctId}`;
        if (sourceNctId && !nodes.has(sourceTrialId)) nodes.set(sourceTrialId, { id: sourceTrialId, type: "trial", label: sourceNctId, hop: Math.max(match.discovery_hop - 1, 0), metadata: {} });
        for (const [trialId, suffix] of [[sourceTrialId, "source"], [relatedTrialId, "target"]] as const) {
          if (!trialId || trialId === "trial:") continue;
          const edgeId = `${trialId}|${relationship}|${entityId}|${match.discovery_hop}|${suffix}`;
          edges.set(edgeId, { id: edgeId, source: trialId, target: entityId, relationship, hop: match.discovery_hop });
        }
      }
    }
    return {
      status: "SUCCESS",
      seed_node: seedNct ? seedId : null,
      nodes: Array.from(nodes.values()),
      edges: Array.from(edges.values()),
      max_hops: related?.max_hops ?? 1,
      per_hop_limit: related?.per_hop_limit ?? Math.max(1, analysedMatches.length || 1),
      limit: related?.limit ?? Math.max(1, analysedMatches.length || 1),
      match_count: analysedMatches.length,
      truncated: false,
      validation: related?.validation,
      limitations: [],
    };
  }, [seedNct, analysedMatches, related?.anchor_trial, related?.max_hops, related?.per_hop_limit, related?.limit, related?.validation, evidence?.trial]);

  const selectedEntity = selectedEntityId ? connectionEntities.find((entity) => entity.id === selectedEntityId) : undefined;
  const categories: Array<{ relationship: GraphRelationship; label: string; sharedSingular: string; sharedPlural: string; description: string }> = [
    { relationship: "HAS_CONDITION", label: "Conditions", sharedSingular: "shared condition", sharedPlural: "shared conditions", description: "Clinical conditions shared with analysed studies" },
    { relationship: "HAS_INTERVENTION", label: "Interventions", sharedSingular: "shared intervention", sharedPlural: "shared interventions", description: "Treatments or interventions shared with analysed studies" },
    { relationship: "SPONSORED_BY", label: "Sponsors", sharedSingular: "shared sponsor", sharedPlural: "shared sponsors", description: "Organizations shared with analysed studies" },
  ];

  useEffect(() => {
    setMaxHops(reportedDepth);
    setRelationshipFilter("ALL");
    setSelection(null);
    setSelectedEntityId(null);
    setVisibleEntityStudies(5);
    setAdvancedOpen(false);
    setExpandedScope(false);
    setDisplayMode("network");
    setFrameCollapsed(false);
    setFrameMaximized(false);
    setDownloadOpen(false);
    setCopyStatus("");
    setGraph(null);
    setGraphError("");
  }, [seedNct, reportedDepth]);

  useEffect(() => {
    if (!advancedOpen || !expandedScope || !seedNct) { setLoadingGraph(false); return; }
    const controller = new AbortController();
    const graphLimit = maxHops === 2 ? 40 : 20;
    const perHopLimit = 20;
    setLoadingGraph(true);
    setGraphError("");
    fetch(`${API_BASE_URL}/api/v1/lineage/trials/${encodeURIComponent(seedNct)}/graph?max_hops=${maxHops}&per_hop_limit=${perHopLimit}&limit=${graphLimit}`, { signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          const detail = payload?.detail;
          throw new Error(typeof detail === "string" ? detail : "Study connection graph could not be loaded.");
        }
        return payload as GraphViewResponse;
      })
      .then((payload) => {
        setGraph(payload);
        setSelection(null);
        const loadedLayout = buildGraphLayout(payload.nodes ?? [], maxHops);
        setViewport({ x: 0, y: 0, width: loadedLayout.width, height: loadedLayout.height });
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setGraphError(error instanceof Error ? error.message : "Study connection graph could not be loaded.");
      })
      .finally(() => { if (!controller.signal.aborted) setLoadingGraph(false); });
    return () => controller.abort();
  }, [seedNct, maxHops, advancedOpen, expandedScope, analysedMatches.length]);

  useEffect(() => {
    document.body.classList.toggle("graph-workspace-open", frameMaximized);
    return () => document.body.classList.remove("graph-workspace-open");
  }, [frameMaximized]);

  useEffect(() => {
    if (!advancedOpen) return;
    const sourceGraph = expandedScope ? graph : analysisGraph;
    if (!sourceGraph) return;
    const sourceEdges = sourceGraph.edges ?? [];
    const filteredEdges = relationshipFilter === "ALL" ? sourceEdges : sourceEdges.filter((edge) => edge.relationship === relationshipFilter);
    const visibleIds = new Set<string>([sourceGraph.seed_node ?? ""]);
    filteredEdges.forEach((edge) => { visibleIds.add(edge.source); visibleIds.add(edge.target); });
    const sourceNodes = sourceGraph.nodes ?? [];
    const filteredNodes = relationshipFilter === "ALL" ? sourceNodes : sourceNodes.filter((node) => visibleIds.has(node.id));
    const fitted = buildGraphLayout(filteredNodes, maxHops);
    setViewport({ x: 0, y: 0, width: fitted.width, height: fitted.height });
  }, [advancedOpen, expandedScope, graph, analysisGraph, relationshipFilter, maxHops]);

  if (!seedNct) return <div className="workspace-view"><div className="empty-inline"><Network size={24}/><strong>No study is available for connection exploration</strong><p>Run a study-specific investigation or open a study first.</p></div></div>;

  const activeGraph = expandedScope ? graph : analysisGraph;
  const allNodes = activeGraph?.nodes ?? [];
  const allEdges = activeGraph?.edges ?? [];
  const visibleEdges = relationshipFilter === "ALL" ? allEdges : allEdges.filter((edge) => edge.relationship === relationshipFilter);
  const visibleNodeIds = new Set<string>([activeGraph?.seed_node ?? ""]);
  visibleEdges.forEach((edge) => { visibleNodeIds.add(edge.source); visibleNodeIds.add(edge.target); });
  const visibleNodes = relationshipFilter === "ALL" ? allNodes : allNodes.filter((node) => visibleNodeIds.has(node.id));
  const layout = buildGraphLayout(visibleNodes, maxHops);
  const selectedNode = selection?.kind === "node" ? allNodes.find((node) => node.id === selection.id) : undefined;
  const selectedEdge = selection?.kind === "edge" ? allEdges.find((edge) => edge.id === selection.id) : undefined;
  const edgeSource = selectedEdge ? allNodes.find((node) => node.id === selectedEdge.source) : undefined;
  const edgeTarget = selectedEdge ? allNodes.find((node) => node.id === selectedEdge.target) : undefined;
  const connectionRows = buildGraphConnectionRows(visibleNodes, visibleEdges, activeGraph?.seed_node ?? "");
  const visibleRelatedStudyCount = connectionRows.length;
  const visibleSharedEntityCount = visibleNodes.filter((node) => node.type !== "trial").length;
  const visibleEvidenceLinkCount = visibleEdges.length;
  const selectedConnection = selection?.kind === "node" ? connectionRows.find((row) => row.studyId === selection.id) : undefined;
  const selectedPath = (() => {
    if (!selection || !activeGraph?.seed_node) return null;
    const targetId = selection.kind === "node" ? selection.id : selectedEdge?.source;
    if (!targetId || targetId === activeGraph.seed_node) return null;
    const path = findGraphPath(activeGraph.seed_node, targetId, visibleEdges);
    if (!path) return null;
    const nodeIds = new Set(path.nodeIds);
    const edgeIds = new Set(path.edgeIds);
    if (selection.kind === "edge" && selectedEdge) {
      nodeIds.add(selectedEdge.source);
      nodeIds.add(selectedEdge.target);
      edgeIds.add(selectedEdge.id);
    }
    return { nodeIds, edgeIds };
  })();

  const filters: Array<{ value: GraphFilter; label: string }> = [
    { value: "ALL", label: "All" },
    { value: "HAS_CONDITION", label: "Conditions" },
    { value: "HAS_INTERVENTION", label: "Interventions" },
    { value: "SPONSORED_BY", label: "Sponsors" },
  ];

  const openBroaderGraph = (relationship?: GraphRelationship) => {
    setAdvancedOpen(true);
    setExpandedScope(true);
    setRelationshipFilter(relationship ?? "ALL");
    setSelection(null);
    setFrameCollapsed(false);
  };

  const fitGraph = () => setViewport({ x: 0, y: 0, width: layout.width, height: layout.height });
  const zoomGraph = (factor: number) => setViewport((current) => {
    const minWidth = Math.max(240, layout.width * .22);
    const maxWidth = Math.max(layout.width, layout.width * 3);
    const nextWidth = Math.min(maxWidth, Math.max(minWidth, current.width * factor));
    const aspect = layout.height / Math.max(1, layout.width);
    const nextHeight = nextWidth * aspect;
    return {
      x: current.x + (current.width - nextWidth) / 2,
      y: current.y + (current.height - nextHeight) / 2,
      width: nextWidth,
      height: nextHeight,
    };
  });

  const handleGraphPointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    const target = event.target as Element;
    if (target.closest(".graphrag-node") || target.closest(".graphrag-edge-hitbox")) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragState({ pointerId: event.pointerId, clientX: event.clientX, clientY: event.clientY, viewX: viewport.x, viewY: viewport.y });
  };
  const handleGraphPointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (!dragState || dragState.pointerId !== event.pointerId) return;
    const rect = event.currentTarget.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dx = event.clientX - dragState.clientX;
    const dy = event.clientY - dragState.clientY;
    setViewport((current) => ({
      ...current,
      x: dragState.viewX - dx * (current.width / rect.width),
      y: dragState.viewY - dy * (current.height / rect.height),
    }));
  };
  const handleGraphPointerEnd = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (dragState?.pointerId === event.pointerId) setDragState(null);
  };

  const visibleStudyNodes = visibleNodes.filter((node) => node.type === "trial");
  const graphText = [
    `Study of interest: ${seedNct}`,
    `Display scope: ${expandedScope ? "Expanded bounded network" : "Analysed set"}`,
    `Connected studies shown: ${connectionRows.length}`,
    "",
    ...connectionRows.map((row) => `${row.studyLabel} — ${row.whyConnected} — ${row.sharedEntity} — ${row.depthLabel}`),
  ].join("\n");

  const copyGraph = async () => {
    try {
      await copyClientText(graphText);
      setCopyStatus("Copied");
    } catch {
      setCopyStatus("Copy failed");
    }
    window.setTimeout(() => setCopyStatus(""), 1800);
  };

  const graphExportStyle = `
    .graphrag-edge{stroke:#aab9cf;stroke-width:1.5}.graphrag-edge-label{fill:#748097;font:700 9px system-ui}
    .graphrag-node>*:first-child{fill:#fff;stroke:#7790bc;stroke-width:1.5}.graph-node-trial>*:first-child{stroke:#3157b7;stroke-width:2}
    .graphrag-node-type{fill:#748097;font:800 8px system-ui;letter-spacing:.6px}.graphrag-node-label{fill:#24344f;font:800 11px system-ui}
  `;
  const serializedGraphSvg = () => {
    const source = graphSvgRef.current;
    if (!source) return null;
    const clone = source.cloneNode(true) as SVGSVGElement;
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.setAttribute("width", String(layout.width));
    clone.setAttribute("height", String(layout.height));
    clone.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
    clone.removeAttribute("style");
    const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
    style.textContent = graphExportStyle;
    clone.insertBefore(style, clone.firstChild);
    return new XMLSerializer().serializeToString(clone);
  };
  const downloadSvg = () => {
    const value = serializedGraphSvg();
    if (value) downloadClientFile(`${seedNct}-trialiq-network.svg`, value, "image/svg+xml;charset=utf-8");
  };
  const downloadPng = () => {
    const value = serializedGraphSvg();
    if (!value) return;
    const blob = new Blob([value], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const image = new Image();
    image.onload = () => {
      const maxWidth = 2400;
      const scale = Math.min(2, maxWidth / Math.max(1, layout.width));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(layout.width * scale));
      canvas.height = Math.max(1, Math.round(layout.height * scale));
      const context = canvas.getContext("2d");
      if (context) {
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((png) => { if (png) downloadClientFile(`${seedNct}-trialiq-network.png`, png, "image/png"); });
      }
      URL.revokeObjectURL(url);
    };
    image.src = url;
  };
  const downloadStudiesCsv = () => {
    const rows = ["nct_id,title,status,phase,connection_depth", ...visibleStudyNodes.map((node) => [
      node.label,
      node.metadata?.brief_title ?? "",
      node.metadata?.overall_status ?? "",
      node.metadata?.phase ?? "",
      graphConnectionDepthLabel(node.hop),
    ].map(csvCell).join(","))];
    downloadClientFile(`${seedNct}-trialiq-visible-studies.csv`, rows.join("\r\n"), "text/csv;charset=utf-8");
  };
  const downloadConnectionsCsv = () => {
    const rows = ["connected_study,why_connected,shared_entity,connection_depth", ...connectionRows.map((row) => [
      row.studyLabel,
      row.whyConnected,
      row.sharedEntity,
      row.depthLabel,
    ].map(csvCell).join(","))];
    downloadClientFile(`${seedNct}-trialiq-visible-connections.csv`, rows.join("\r\n"), "text/csv;charset=utf-8");
  };
  const downloadGraphJson = () => downloadClientFile(`${seedNct}-trialiq-graph.json`, JSON.stringify({
    seed_nct_id: seedNct,
    display_scope: expandedScope ? "expanded" : "analysed_set",
    max_hops: activeGraph?.max_hops ?? maxHops,
    relationship_filter: relationshipFilter,
    nodes: visibleNodes,
    edges: visibleEdges,
  }, null, 2), "application/json;charset=utf-8");

  return <div className="workspace-view connection-explorer-view">
    <div className="connection-explorer-note"><Waypoints size={18}/><div><strong>Why are these studies related?</strong><p>Choose a condition, intervention, or sponsor to see which studies in this answer share that connection with {seedNct}.</p></div></div>

    <section className="connection-explorer-shell">
      <div className="connection-anchor-card">
        <span>Study of interest</span>
        <strong>{seedNct}</strong>
        <p>{text(related?.anchor_trial?.brief_title ?? evidence?.trial?.brief_title, "Study title not reported")}</p>
        <small>{text(related?.anchor_trial?.overall_status ?? evidence?.trial?.overall_status, "Status not reported")}</small>
      </div>
      <div className="connection-flow-line" aria-hidden="true"><span/></div>
      <div className="connection-category-grid">
        {categories.map((category) => {
          const entities = connectionEntities.filter((entity) => entity.relationship === category.relationship);
          const analysedStudyIds = new Set(entities.flatMap((entity) => entity.matches.map((match) => match.nct_id)));
          return <article className={`connection-category-card category-${category.relationship.toLowerCase()}`} key={category.relationship}>
            <div className="connection-category-head">
              <div><span>{category.label}</span><strong>{entities.length} {entities.length === 1 ? category.sharedSingular : category.sharedPlural}</strong></div>
              <small>{analysedStudyIds.size} analysed stud{analysedStudyIds.size === 1 ? "y" : "ies"}</small>
            </div>
            <p>{category.description}</p>
            {entities.length ? <div className="connection-entity-list">{entities.map((entity) => <button type="button" className={`connection-entity-button ${selectedEntityId === entity.id ? "active" : ""}`} key={entity.id} onClick={() => { setSelectedEntityId(entity.id); setVisibleEntityStudies(5); }}>
              <span className="connection-entity-copy"><strong>{entity.label}</strong><small>{entity.matches.length} analysed stud{entity.matches.length === 1 ? "y" : "ies"}</small></span>
              <span className="connection-entity-reach">{entity.fanout !== null ? <><strong>{entity.fanout.toLocaleString()}</strong><small>studies in loaded graph</small></> : <><strong>Source-backed</strong><small>shared entity</small></>}</span>
              <ArrowRight size={15}/>
            </button>)}</div> : <div className="connection-category-empty">No {category.sharedPlural} connect the analysed studies.</div>}
          </article>;
        })}
      </div>
    </section>

    {selectedEntity && <section className="connection-branch-panel" aria-live="polite">
      <div className="connection-branch-heading">
        <div><span>{graphRelationshipLabel(selectedEntity.relationship)} branch</span><h3>{selectedEntity.label}</h3><p>{selectedEntity.matches.length} analysed stud{selectedEntity.matches.length === 1 ? "y is" : "ies are"} connected through this {graphRelationshipLabel(selectedEntity.relationship).toLowerCase()}.{selectedEntity.fanout !== null ? ` ${selectedEntity.fanout.toLocaleString()} studies in the loaded graph share it.` : ""}</p></div>
        <button type="button" className="secondary-button connection-broader-action" onClick={() => openBroaderGraph(selectedEntity.relationship)}>View wider network <ArrowRight size={15}/></button>
      </div>
      <div className="connection-branch-study-grid">
        {selectedEntity.matches.slice(0, visibleEntityStudies).map((match) => <article className="connection-branch-study" key={`${selectedEntity.id}-${match.nct_id}`}>
          <div><span>Related study</span><strong>{match.nct_id}</strong></div>
          <p>{text(match.trial?.brief_title, "Title unavailable")}</p>
          <div className="connection-branch-meta"><span className={`clinical-status ${clinicalStatusClass(typeof match.trial?.overall_status === "string" ? match.trial.overall_status : null)}`}>{humanStatusLabel(typeof match.trial?.overall_status === "string" ? match.trial.overall_status : null)}</span><span className="connection-depth-badge">{match.discovery_hop === 1 ? "Direct connection" : `Connection level ${match.discovery_hop}`}</span></div>
        </article>)}
      </div>
      {visibleEntityStudies < selectedEntity.matches.length && <button type="button" className="connection-show-more" onClick={() => setVisibleEntityStudies((current) => Math.min(current + 5, selectedEntity.matches.length))}>Show {Math.min(5, selectedEntity.matches.length - visibleEntityStudies)} more analysed studies <ChevronDown size={15}/></button>}
    </section>}

    <section className="advanced-graph-gate">
      <div><span>Technical graph explorer</span><strong>Need the node-link view?</strong><p>This optional view exposes graph controls for technical inspection. It is not required to understand the answer.</p></div>
      <button type="button" className="secondary-button" onClick={() => setAdvancedOpen((current) => {
        const next = !current;
        if (next) setViewport({ x: 0, y: 0, width: layout.width, height: layout.height });
        return next;
      })}>{advancedOpen ? "Close technical graph" : "Open technical graph"} <Waypoints size={15}/></button>
    </section>

    {advancedOpen && <section className={`advanced-graph-panel graph-result-frame ${frameMaximized ? "graph-frame-maximized" : ""} ${frameCollapsed ? "graph-frame-collapsed" : ""}`}>
      <header className="graph-result-frame-header">
        <div className="graph-result-frame-title">
          <Network size={18}/>
          <div><span>Network explorer</span><strong>{seedNct}</strong><small>{activeGraph ? `${visibleRelatedStudyCount} related studies · ${visibleSharedEntityCount} shared entities · ${visibleEvidenceLinkCount} evidence links` : "Preparing graph"}</small></div>
        </div>
        <div className="graph-result-frame-actions" aria-label="Graph workspace actions">
          <div className="graph-action-group"><span>View</span><div className="graph-view-switch" role="group" aria-label="Graph result view">
            <button type="button" className={displayMode === "network" ? "active" : ""} onClick={() => setDisplayMode("network")}><Network size={14}/> Network</button>
            <button type="button" className={displayMode === "table" ? "active" : ""} onClick={() => setDisplayMode("table")}><Table2 size={14}/> Table</button>
          </div></div>
          <div className="graph-action-group"><span>Actions</span><div className="graph-action-cluster">
            <button type="button" className="graph-icon-action graph-labeled-action" onClick={() => void copyGraph()} title="Copy visible graph as text" aria-label="Copy visible graph as text"><Copy size={15}/><span>Copy</span></button>
            <details className="graph-download-menu" open={downloadOpen} onToggle={(event) => setDownloadOpen(event.currentTarget.open)}>
              <summary className="graph-icon-action graph-labeled-action" title="Download graph" aria-label="Download graph"><Download size={15}/><span>Download</span></summary>
              <div className="graph-download-popover">
                <button type="button" disabled={displayMode !== "network"} onClick={downloadPng}>PNG image</button>
                <button type="button" disabled={displayMode !== "network"} onClick={downloadSvg}>SVG image</button>
                <button type="button" onClick={downloadStudiesCsv}>CSV · visible studies</button>
                <button type="button" onClick={downloadConnectionsCsv}>CSV · visible connections</button>
                <button type="button" onClick={downloadGraphJson}>JSON · graph data</button>
              </div>
            </details>
          </div></div>
          <div className="graph-frame-actions">
            <button type="button" className="graph-icon-action" onClick={() => setFrameCollapsed((current) => !current)} title={frameCollapsed ? "Restore graph" : "Minimize graph"} aria-label={frameCollapsed ? "Restore graph" : "Minimize graph"}>{frameCollapsed ? <ChevronDown size={16}/> : <ChevronUp size={16}/>}</button>
            <button type="button" className="graph-icon-action" onClick={() => { setFrameMaximized((current) => !current); setFrameCollapsed(false); }} title={frameMaximized ? "Restore graph size" : "Maximize graph"} aria-label={frameMaximized ? "Restore graph size" : "Maximize graph"}>{frameMaximized ? <Minimize2 size={16}/> : <Maximize2 size={16}/>}</button>
          </div>
        </div>
        {copyStatus && <span className="graph-copy-status" role="status">{copyStatus}</span>}
      </header>

      {!frameCollapsed && <>
        <div className="graph-result-frame-controls">
          <div className="graphrag-toolbar compact-graph-toolbar">
            <div className="graph-control-group"><span>Filter</span><div className="graph-filter-row">{filters.map((filter) =>
              <button type="button" key={filter.value} className={relationshipFilter === filter.value ? "active" : ""} onClick={() => { setRelationshipFilter(filter.value); setSelection(null); }}>{filter.label}</button>)}</div></div>
            <div className="graph-control-group"><span>Scope</span><div className="graph-depth-switch" role="group" aria-label="Graph display scope">
              <button type="button" className={!expandedScope ? "active" : ""} onClick={() => {
                setExpandedScope(false); setSelection(null); setGraphError("");
                const analysedLayout = buildGraphLayout(analysisGraph.nodes ?? [], reportedDepth);
                setViewport({ x: 0, y: 0, width: analysedLayout.width, height: analysedLayout.height });
              }}>Analysed</button>
              <button type="button" className={expandedScope ? "active" : ""} onClick={() => { setExpandedScope(true); setSelection(null); }}>Expanded</button>
            </div></div>
            <div className="graph-control-group"><span>Depth</span>{expandedScope ? <div className="graph-depth-switch" role="group" aria-label="Graph traversal depth">
              <button type="button" className={maxHops === 1 ? "active" : ""} onClick={() => setMaxHops(1)}>Direct</button>
              <button type="button" className={maxHops === 2 ? "active" : ""} onClick={() => setMaxHops(2)}>2-step</button>
            </div> : <div className="graph-scope-static">{(related?.max_hops ?? 1) === 1 ? "Direct connection" : "2-step connection"}</div>}</div>
          </div>
          {displayMode === "network" && <div className="graph-navigation-toolbar" aria-label="Graph navigation controls">
            <strong>Explore</strong>
            <button type="button" onClick={fitGraph} title="Fit graph to view"><RotateCcw size={14}/> Fit</button>
            <button type="button" onClick={() => zoomGraph(.8)} title="Zoom in"><ZoomIn size={15}/></button>
            <button type="button" onClick={() => zoomGraph(1.25)} title="Zoom out"><ZoomOut size={15}/></button>
            <button type="button" onClick={fitGraph} title="Reset graph position">Reset</button>
            <span>Drag empty space to pan</span>
          </div>}
        </div>

        {expandedScope && loadingGraph && <div className="graph-loading" role="status"><div className="processing-spinner"/><span>Loading expanded bounded node-link graph…</span></div>}
        {expandedScope && graphError && <div className="graph-error" role="alert"><CircleAlert size={17}/><span>{graphError}</span></div>}

        {activeGraph && !(expandedScope && loadingGraph) && <>
          <div className="graph-metrics compact-graph-metrics">
            <Metric label="Studies shown" value={String(visibleRelatedStudyCount)}/>
            <Metric label="Shared entities" value={String(visibleSharedEntityCount)}/>
            <Metric label="Evidence links" value={String(visibleEvidenceLinkCount)}/>
            <Metric label="Depth" value={(activeGraph.max_hops ?? maxHops) === 1 ? "Direct connection" : "2-step connection"}/>
          </div>
          <p className="graph-scope-copy">{expandedScope ? "Counts reflect the currently visible bounded network after the active relationship filter." : `Counts reflect the visible subset of the ${analysedMatches.length} related studies analysed in the current answer.`}</p>

          <div className={`graph-workspace-body ${(selectedNode || selectedEdge) ? "has-selection" : ""}`}>
            <div className="graph-workspace-primary">
              {displayMode === "network" ? <div className="graphrag-canvas-shell bounded-canvas-shell neo4j-style-canvas" aria-label="Interactive related-trial graph">
                {visibleEdges.length && connectionRows.length ? <svg ref={graphSvgRef} className={`graphrag-canvas ${dragState ? "is-panning" : ""}`} viewBox={`${viewport.x} ${viewport.y} ${viewport.width} ${viewport.height}`} role="img" aria-label={`Study connections for ${seedNct}`}
                  onPointerDown={handleGraphPointerDown} onPointerMove={handleGraphPointerMove} onPointerUp={handleGraphPointerEnd} onPointerCancel={handleGraphPointerEnd}
                  onWheel={(event) => { event.preventDefault(); zoomGraph(event.deltaY < 0 ? .9 : 1.1); }}>
                  <g className="graphrag-edges">{visibleEdges.map((edge) => {
                    const source = layout.positions.get(edge.source); const target = layout.positions.get(edge.target);
                    if (!source || !target) return null;
                    const selected = selection?.kind === "edge" && selection.id === edge.id;
                    const onPath = selectedPath?.edgeIds.has(edge.id) ?? false;
                    const muted = Boolean(selectedPath && !onPath);
                    const midX = (source.x + target.x) / 2; const midY = (source.y + target.y) / 2;
                    return <g key={edge.id}>
                      <line className={`graphrag-edge relationship-${edge.relationship.toLowerCase()} ${selected ? "selected" : ""} ${onPath ? "is-path" : ""} ${muted ? "is-muted" : ""}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y}/>
                      <line className="graphrag-edge-hitbox" x1={source.x} y1={source.y} x2={target.x} y2={target.y} role="button" tabIndex={0}
                        aria-label={`${graphRelationshipLabel(edge.relationship)} connection`} onClick={() => setSelection({ kind: "edge", id: edge.id })}
                        onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelection({ kind: "edge", id: edge.id }); } }}><title>{graphRelationshipLabel(edge.relationship)}</title></line>
                      {(selected || onPath) && <text className={`graphrag-edge-label ${onPath ? "is-path" : ""}`} x={midX} y={midY - 7} textAnchor="middle">{graphRelationshipLabel(edge.relationship)}</text>}
                    </g>;
                  })}</g>
                  <g className="graphrag-nodes">{visibleNodes.map((node) => {
                    const position = layout.positions.get(node.id); if (!position) return null;
                    const onPath = selectedPath?.nodeIds.has(node.id) ?? false;
                    const muted = Boolean(selectedPath && !onPath);
                    return <GraphNodeShape key={node.id} node={node} x={position.x} y={position.y} selected={selection?.kind === "node" && selection.id === node.id} onPath={onPath} muted={muted} onSelect={() => setSelection({ kind: "node", id: node.id })}/>;
                  })}</g>
                </svg> : <div className="graph-empty"><Network size={24}/><strong>No visible connections for this filter</strong><span>The selected relationship type has no study-to-entity evidence in the current graph scope.</span></div>}
              </div> : <div className="graph-table-view" role="region" aria-label="Visible study connections as a table">
                <table><thead><tr><th>Connected study</th><th>Why connected</th><th>Shared entity</th><th>Connection depth</th></tr></thead><tbody>
                  {connectionRows.map((row) => <tr key={`table-${row.studyId}`} className={selection?.kind === "node" && selection.id === row.studyId ? "is-selected" : ""} role="button" tabIndex={0}
                    onClick={() => setSelection({ kind: "node", id: row.studyId })}
                    onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelection({ kind: "node", id: row.studyId }); } }}>
                    <td><strong>{row.studyLabel}</strong></td><td>{row.whyConnected}</td><td>{row.sharedEntity}</td><td>{row.depthLabel}</td>
                  </tr>)}
                </tbody></table>
                {!connectionRows.length && <div className="graph-table-empty">No connected studies for the current filter.</div>}
              </div>}
            </div>

            {(selectedNode || selectedEdge) && <aside className="graph-selection-drawer" aria-live="polite">
              <div className="graph-inspector-heading"><span>Connection details</span><strong>{selectedConnection?.studyLabel ?? (selectedEdge ? graphRelationshipLabel(selectedEdge.relationship) : selectedNode?.label ?? "Selection")}</strong></div>
              {selectedConnection && <div className="graph-inspector-body">
                <InspectorRow label="Connected study" value={selectedConnection.studyLabel}/><InspectorRow label="Why connected" value={selectedConnection.whyConnected}/>
                <InspectorRow label="Shared entity" value={selectedConnection.sharedEntity}/><InspectorRow label="Connection depth" value={selectedConnection.depthLabel}/>
                <InspectorRow label="Title" value={text(selectedNode?.metadata?.brief_title)}/><InspectorRow label="Status" value={text(selectedNode?.metadata?.overall_status)}/>
              </div>}
              {selectedNode && !selectedConnection && <div className="graph-inspector-body">
                <InspectorRow label="Item type" value={selectedNode.hop === 0 ? "Study of interest" : collectionLabel(selectedNode.type)}/><InspectorRow label="Connection depth" value={graphConnectionDepthLabel(selectedNode.hop)}/>
                {selectedNode.type === "trial" && <><InspectorRow label="Title" value={text(selectedNode.metadata?.brief_title)}/><InspectorRow label="Status" value={text(selectedNode.metadata?.overall_status)}/><InspectorRow label="Phase" value={text(selectedNode.metadata?.phase)}/></>}
                {selectedNode.type !== "trial" && <><InspectorRow label="Name" value={selectedNode.label}/><InspectorRow label="Loaded study reach" value={selectedNode.metadata?.loaded_trial_count ? Number(selectedNode.metadata.loaded_trial_count).toLocaleString() : "Not reported"}/></>}
              </div>}
              {selectedEdge && <div className="graph-inspector-body"><InspectorRow label="Connection type" value={graphRelationshipLabel(selectedEdge.relationship)}/><InspectorRow label="Connection depth" value={graphConnectionDepthLabel(selectedEdge.hop)}/><InspectorRow label="Study" value={edgeSource?.label ?? selectedEdge.source}/><InspectorRow label="Shared entity" value={edgeTarget?.label ?? selectedEdge.target}/></div>}
              <button type="button" className="comparison-close-button graph-selection-close" onClick={() => setSelection(null)}>Close details</button>
            </aside>}
          </div>
          {(activeGraph.match_count ?? 0) === 0 && <div className="graph-zero-state"><Network size={18}/><div><strong>No related studies were found within the current search distance.</strong><p>The study of interest ({seedNct}) is still shown because the connection search completed successfully.</p></div></div>}
          {!!activeGraph.limitations?.length && <div className="graph-limitations"><strong>Graph notes</strong><ul>{activeGraph.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></div>}
        </>}
      </>}
    </section>}
  </div>;
}

function InspectorRow({ label, value }: { label: string; value: string }) {
  return <div className="graph-inspector-row"><span>{label}</span><strong>{value}</strong></div>;
}

function executionStagePresentation(stage: string | undefined) {
  const key = (stage ?? "").toLowerCase();
  if (key === "intent") return { title: "Understood your question", detail: "Identified the study and the type of comparison you asked for.", icon: <Search size={19}/> };
  if (key === "retrieval") return { title: "Found connected studies", detail: "Searched the available study relationships and supporting records.", icon: <Network size={19}/> };
  if (key === "metrics") return { title: "Compared available study data", detail: "Calculated the comparisons that can be supported by the loaded data.", icon: <GitBranch size={19}/> };
  if (key === "validation") return { title: "Checked the supporting evidence", detail: "Verified that the result only refers to evidence returned for this investigation.", icon: <ShieldCheck size={19}/> };
  if (key === "synthesis") return { title: "Prepared the TrialIQ summary", detail: "Turned the checked evidence into a concise investigator-facing result.", icon: <BookOpen size={19}/> };
  return { title: collectionLabel(stage ?? "Evidence step"), detail: "Completed this step using the available evidence.", icon: <CheckCircle2 size={19}/> };
}

function ExecutionView({ result }: { result: UiResult }) {
  const trace = getTrace(result);
  const transport = getTransport(result);
  const toolName = getToolName(result);
  const mode = result.execution_mode ?? (trace.length ? "agentic" : "baseline");
  return <div className="workspace-view">
    {trace.length ? <section className="clinical-workflow-card">
      <div className="clinical-workflow-heading">
        <div><span>How TrialIQ reached this result</span><h3>From your question to an evidence-checked answer</h3><p>TrialIQ followed the steps below using the study information and connections available for this investigation.</p></div>
        <span className="clinical-workflow-badge"><CheckCircle2 size={15}/> Completed</span>
      </div>
      <div className="clinical-workflow" role="list" aria-label="TrialIQ investigation workflow">
        {trace.map((stage, index) => {
          const presentation = executionStagePresentation(stage.stage);
          return <div className="clinical-workflow-segment" key={`${stage.stage ?? "stage"}-${index}`} role="listitem">
            <div className="clinical-workflow-step" style={{ animationDelay: `${index * 160}ms` }}>
              <div className="clinical-workflow-icon">{presentation.icon}</div>
              <div><span>Step {index + 1}</span><strong>{presentation.title}</strong><p>{presentation.detail}</p></div>
            </div>
            {index < trace.length - 1 && <div className="clinical-workflow-connector" aria-hidden="true"><span/></div>}
          </div>;
        })}
      </div>
    </section> : <div className="empty-inline"><TimerReset size={24}/><strong>No workflow details were reported</strong><p>Workflow detail appears here only when it is returned with the investigation result.</p></div>}

    <details className="execution-technical-details">
      <summary><span>Technical run details</span><span>For developers and audit review <ChevronDown size={15}/></span></summary>
      <div className="execution-technical-body">
        <div className="execution-summary">
          <Quality label="Run ID" value={text(result.run_id, "Not reported")}/>
          <Quality label="Execution mode" value={mode === "agentic" ? "Guided / agentic" : "Direct / baseline"}/>
          <Quality label="Answer method" value={mode === "baseline" ? "Deterministic" : result.generation?.method === "LLM" ? "AI / LLM synthesis" : result.generation?.method === "DETERMINISTIC" ? "Deterministic synthesis" : "Agentic retrieval"}/>
          {mode === "agentic" ? <>
            <Quality label="Transport" value={transport}/>
            <Quality label="MCP tool" value={toolName}/>
            {result.generation?.provider && <Quality label="LLM provider" value={result.generation.provider}/>}
            {result.generation?.model && <Quality label="LLM model" value={result.generation.model}/>}
          </> : <Quality label="API path" value="Standard /query"/>}
          <Quality label="Stages" value={String(trace.length)}/>
        </div>
        {trace.length > 0 && <div className="trace-list">{trace.map((stage, i) => <div className="trace-row" key={`${stage.stage ?? "stage"}-${i}`}>
          <div className="trace-marker"><CheckCircle2 size={16}/></div>
          <div className="trace-body"><div className="trace-title"><strong>{text(stage.stage, `Stage ${i + 1}`)}</strong><span>{text(stage.status, "reported")}</span></div>
            <div className="trace-meta">
              {stage.duration_ms !== undefined && <span>Stage: {formatDuration(stage.duration_ms)}</span>}
              {traceDetailEntries(stage).map(([label, value]) => <span key={`${stage.stage}-${label}`}>{label}: {value}</span>)}
            </div>
          </div>
        </div>)}</div>}
      </div>
    </details>
  </div>;
}

function Quality({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "success" | "warning" | "danger" | "info" }) {
  return <div className={`quality-card quality-${tone}`}><span>{label}</span><strong>{value}</strong></div>;
}
function MessageList({ title, messages, kind }: { title: string; messages: string[]; kind: "error" | "warning" }) {
  return <div className={`message-list ${kind}`}><strong>{title}</strong><ul>{messages.map((message, i) => <li key={i}>{message}</li>)}</ul></div>;
}
function ReadableRecord({ record }: { record: Record<string, unknown> }) {
  const preferred = [
    "name", "condition_name", "intervention_name", "official_title", "brief_title",
    "overall_status", "study_type", "phase", "role", "facility_name", "city", "country",
    "nct_id", "source_nct_id", "source_database", "source_schema", "source_table", "source_id", "source_key",
  ];
  const priority = new Map(preferred.map((key, index) => [key, index]));
  const entries = Object.entries(record)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .sort(([a], [b]) => (priority.get(a) ?? 999) - (priority.get(b) ?? 999))
    .slice(0, 8);
  return <div className="readable-record">{entries.map(([key, value]) => <div className="record-field" key={key}><span>{collectionLabel(key)}</span><strong>{typeof value === "object" ? JSON.stringify(value) : text(value)}</strong></div>)}</div>;
}
function EmptyState({ title = "Ready to investigate", message = "Run a question to see the grounded answer, evidence, graph view, and execution metadata here." }) {
  return <section className="empty-state panel"><div className="empty-icon"><BookOpen size={22}/></div><h2>{title}</h2><p>{message}</p></section>;
}
