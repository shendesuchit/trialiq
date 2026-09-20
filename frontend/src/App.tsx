import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type EvidenceRecord = Record<string, unknown>

type ValidationResult = {
  valid: boolean
  errors?: string[]
  warnings?: string[]
}

type GraphResponse = {
  status?: string
  nct_id?: string
  evidence?: Record<string, unknown>
  validation?: ValidationResult
}

type ConditionMatch = {
  nct_id?: string | null
  trial?: Record<string, unknown> | null
  matched_conditions?: Array<Record<string, unknown>>
}

type ConditionSearchResponse = {
  status?: string
  condition?: string | null
  limit?: number
  matches?: ConditionMatch[]
  validation?: ValidationResult
}

type EvidenceSource = {
  source_table?: string | null
  source_key?: string | null
  source_id?: string | number | null
}

type QueryResponse = {
  status?: string
  message?: string
  question?: string
  answer?: string
  limitations?: string[]
  sources?: EvidenceSource[]
  nct_id?: string | null
  intent?: string | null
  graph_response?: GraphResponse | null
  condition_search_response?: ConditionSearchResponse | null
}

type AnswerResponse = {
  status: string
  question: string
  answer: string
  limitations?: string[]
  sources?: EvidenceSource[]
  graph_response?: GraphResponse | null
}

type LineageRecord = {
  collection?: string | null
  record_index?: number | null
  nct_id?: string | null
  source_table?: string | null
  source_key?: string | null
  source_id?: string | number | null
  provenance_version?: string | null
  pipeline_run_id?: string | null
  source_database?: string | null
  source_schema?: string | null
  source_nct_id?: string | null
  extracted_at_utc?: string | null
  transformed_at_utc?: string | null
  transformation_version?: string | null
}

type LineageResponse = {
  status?: string
  nct_id?: string
  source_count?: number
  records?: LineageRecord[]
  validation?: ValidationResult
  limitations?: string[]
}

const API_BASE_URL = 'http://127.0.0.1:8000'
const API_URL = `${API_BASE_URL}/api/v1/trials/overview`
const QUERY_API_URL = `${API_BASE_URL}/api/v1/query`
const CONDITION_SEARCH_API_URL = `${API_BASE_URL}/api/v1/trials/search-by-condition`
const LINEAGE_API_URL = `${API_BASE_URL}/api/v1/lineage/trials`
const HEALTH_URL = `${API_BASE_URL}/health`
const NCT_ID_PATTERN = /^NCT\d{8}$/i

const EVIDENCE_COLLECTIONS = [
  'trial',
  'conditions',
  'interventions',
  'sponsors',
  'facilities',
  'designs',
  'eligibilities',
]

const PRIORITY_FIELDS: Record<string, string[]> = {
  trial: ['nct_id', 'brief_title', 'overall_status', 'study_type', 'phase'],
  conditions: ['name', 'nct_id'],
  interventions: ['name', 'intervention_type', 'nct_id'],
  sponsors: ['name', 'agency_class', 'lead_or_collaborator', 'nct_id'],
  facilities: ['name', 'city', 'state', 'country', 'nct_id'],
  designs: ['primary_purpose', 'masking', 'intervention_model', 'nct_id'],
  eligibilities: [
    'criteria',
    'minimum_age',
    'maximum_age',
    'gender',
    'adult',
    'child',
    'older_adult',
    'nct_id',
  ],
}

function formatLabel(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return 'Not available'
  }

  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }

  return String(value)
}

function asRecords(value: unknown): EvidenceRecord[] {
  if (Array.isArray(value)) {
    return value.filter(
      (item): item is EvidenceRecord =>
        typeof item === 'object' && item !== null,
    )
  }

  if (typeof value === 'object' && value !== null) {
    return [value as EvidenceRecord]
  }

  return []
}

function EvidenceField({ field, value }: { field: string; value: unknown }) {
  return (
    <div className="evidence-field">
      <span className="evidence-field-label">{formatLabel(field)}</span>
      <span className="evidence-field-value">
        {typeof value === 'object' && value !== null ? (
          <pre>{JSON.stringify(value, null, 2)}</pre>
        ) : (
          formatValue(value)
        )}
      </span>
    </div>
  )
}

function EvidenceRecordView({
  collectionName,
  record,
  recordIndex,
}: {
  collectionName: string
  record: EvidenceRecord
  recordIndex: number
}) {
  const priorityFields = PRIORITY_FIELDS[collectionName] ?? []
  const entries = Object.entries(record)
  const primaryEntries = priorityFields
    .filter((field) => Object.prototype.hasOwnProperty.call(record, field))
    .map((field) => [field, record[field]] as [string, unknown])
  const primaryKeys = new Set(primaryEntries.map(([field]) => field))
  const additionalEntries = entries.filter(([field]) => !primaryKeys.has(field))

  return (
    <article className="evidence-record" key={`${collectionName}-${recordIndex}`}>
      <div className="record-heading">
        <h4>Record {recordIndex + 1}</h4>
        <span className="record-field-count">
          {entries.length} field{entries.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="evidence-primary-fields">
        {primaryEntries.map(([field, value]) => (
          <EvidenceField key={field} field={field} value={value} />
        ))}
      </div>

      {additionalEntries.length > 0 && (
        <details className="additional-fields">
          <summary>Additional fields ({additionalEntries.length})</summary>
          <div className="evidence-additional-fields">
            {additionalEntries.map(([field, value]) => (
              <EvidenceField key={field} field={field} value={value} />
            ))}
          </div>
        </details>
      )}
    </article>
  )
}

function EvidenceCollection({
  collectionName,
  value,
}: {
  collectionName: string
  value: unknown
}) {
  const records = asRecords(value)

  if (records.length === 0) {
    return null
  }

  return (
    <details className="evidence-collection">
      <summary>
        <span>{formatLabel(collectionName)}</span>
        <span className="collection-count">
          {records.length} record{records.length === 1 ? '' : 's'}
        </span>
      </summary>

      <div className="evidence-records">
        {records.map((record, recordIndex) => (
          <EvidenceRecordView
            key={`${collectionName}-${recordIndex}`}
            collectionName={collectionName}
            record={record}
            recordIndex={recordIndex}
          />
        ))}
      </div>
    </details>
  )
}

function ConditionResults({ response }: { response?: ConditionSearchResponse | null }) {
  if (!response) return null

  const matches = response.matches ?? []

  return (
    <section className="condition-results">
      <div className="section-heading">
        <div>
          <h4>Matching trials</h4>
          <p className="technical-note">Exact normalized condition matching from the evidence graph.</p>
        </div>
        <span className="result-count">{matches.length} found</span>
      </div>
      {matches.length === 0 ? (
        <div className="no-results">
          <strong>No matching trials found</strong>
          <p>Try a broader condition name or verify the terminology used in the source data.</p>
        </div>
      ) : (
        <div className="trial-result-grid">
          {matches.map((match, index) => {
            const trial = match.trial ?? {}
            const title = String(trial.brief_title ?? 'Title not available')
            const status = String(trial.overall_status ?? 'Status not available')
            const studyType = String(trial.study_type ?? 'Study type not available')
            const conditions = match.matched_conditions ?? []
            return (
              <article className="trial-result-card" key={`${match.nct_id ?? 'match'}-${index}`}>
                <div className="trial-result-topline">
                  <span className="nct-badge">{match.nct_id ?? 'NCT unavailable'}</span>
                  <span className="trial-status">{status}</span>
                </div>
                <h5>{title}</h5>
                <p className="trial-meta">{studyType}</p>
                {conditions.length > 0 && (
                  <div className="condition-tags">
                    {conditions.map((condition, conditionIndex) => (
                      <span key={`${String(condition.name ?? 'condition')}-${conditionIndex}`}>
                        {String(condition.name ?? condition.downcase_name ?? 'Condition')}
                      </span>
                    ))}
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

function App() {
  const [nctId, setNctId] = useState('NCT00000102')
  const [result, setResult] = useState<AnswerResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiStatus, setApiStatus] = useState<
    'checking' | 'connected' | 'unavailable'
  >('checking')
  const [rawCopied, setRawCopied] = useState(false)
  const [lineageResult, setLineageResult] = useState<LineageResponse | null>(null)
  const [lineageError, setLineageError] = useState('')
  const [lineageLoading, setLineageLoading] = useState(false)
  const [query, setQuery] = useState('Give me an overview of NCT00000102')
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null)
  const [queryError, setQueryError] = useState('')
  const [queryLoading, setQueryLoading] = useState(false)
  const [condition, setCondition] = useState('Cancer')
  const [conditionResult, setConditionResult] = useState<ConditionSearchResponse | null>(null)
  const [conditionError, setConditionError] = useState('')
  const [conditionLoading, setConditionLoading] = useState(false)

  useEffect(() => {
    let cancelled = false

    fetch(HEALTH_URL)
      .then((response) => {
        if (!response.ok) {
          throw new Error('API health check failed')
        }

        if (!cancelled) {
          setApiStatus('connected')
        }
      })
      .catch(() => {
        if (!cancelled) {
          setApiStatus('unavailable')
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setResult(null)
    setRawCopied(false)

    const normalizedId = nctId.trim().toUpperCase()

    if (!normalizedId) {
      setError('Please enter an NCT ID.')
      return
    }

    if (!NCT_ID_PATTERN.test(normalizedId)) {
      setError('Enter a valid NCT ID, for example NCT00000102.')
      return
    }

    setNctId(normalizedId)
    setLoading(true)

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nct_id: normalizedId }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail
            ? typeof data.detail === 'string'
              ? data.detail
              : JSON.stringify(data.detail)
            : 'The request could not be completed.',
        )
      }

      setResult(data as AnswerResponse)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'An unexpected error occurred.',
      )
    } finally {
      setLoading(false)
    }
  }

  async function handleQuerySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setQueryError('')
    setQueryResult(null)

    const normalizedQuestion = query.trim()
    if (!normalizedQuestion) {
      setQueryError('Please enter a question.')
      return
    }

    setQueryLoading(true)
    try {
      const response = await fetch(QUERY_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: normalizedQuestion }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(
          data.detail
            ? typeof data.detail === 'string'
              ? data.detail
              : JSON.stringify(data.detail)
            : 'The query request could not be completed.',
        )
      }
      setQueryResult(data as QueryResponse)
    } catch (requestError) {
      setQueryError(
        requestError instanceof Error
          ? requestError.message
          : 'An unexpected error occurred.',
      )
    } finally {
      setQueryLoading(false)
    }
  }

  async function handleConditionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setConditionError('')
    setConditionResult(null)
    const normalizedCondition = condition.trim()
    if (!normalizedCondition) {
      setConditionError('Please enter a condition.')
      return
    }

    setConditionLoading(true)
    try {
      const response = await fetch(CONDITION_SEARCH_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ condition: normalizedCondition, limit: 20 }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(
          data.detail
            ? typeof data.detail === 'string'
              ? data.detail
              : JSON.stringify(data.detail)
            : 'The condition search could not be completed.',
        )
      }
      setConditionResult(data.condition_search_response ?? data)
    } catch (requestError) {
      setConditionError(
        requestError instanceof Error
          ? requestError.message
          : 'An unexpected condition search error occurred.',
      )
    } finally {
      setConditionLoading(false)
    }
  }

  async function handleLoadLineage(identifier: string) {
    const normalizedId = identifier.trim().toUpperCase()
    setLineageError('')
    setLineageResult(null)

    if (!NCT_ID_PATTERN.test(normalizedId)) {
      setLineageError('A valid NCT ID is required to load lineage.')
      return
    }

    setLineageLoading(true)
    try {
      const response = await fetch(`${LINEAGE_API_URL}/${encodeURIComponent(normalizedId)}`)
      const data = await response.json()
      if (!response.ok) {
        throw new Error(
          data.detail
            ? typeof data.detail === 'string'
              ? data.detail
              : JSON.stringify(data.detail)
            : 'The lineage request could not be completed.',
        )
      }
      setLineageResult(data as LineageResponse)
    } catch (requestError) {
      setLineageError(
        requestError instanceof Error
          ? requestError.message
          : 'An unexpected lineage error occurred.',
      )
    } finally {
      setLineageLoading(false)
    }
  }

  async function copyRawResponse() {
    if (!result?.graph_response) return

    await navigator.clipboard.writeText(
      JSON.stringify(result.graph_response, null, 2),
    )
    setRawCopied(true)
  }

  const graphResponse = result?.graph_response
  const validation = graphResponse?.validation
  const evidence = graphResponse?.evidence
  const validationErrors = validation?.errors ?? []
  const validationWarnings = validation?.warnings ?? []

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">CLINICAL TRIAL INTELLIGENCE</p>
          <h1>TrialIQ</h1>
          <p className="subtitle">Evidence-grounded clinical trial exploration</p>
        </div>
        <span className={`system-status system-status-${apiStatus}`}>
          {apiStatus === 'checking' && 'Checking API…'}
          {apiStatus === 'connected' && 'API Connected'}
          {apiStatus === 'unavailable' && 'API Unavailable'}
        </span>
      </header>

      <section className="search-card">
        <h2>Ask about a clinical trial</h2>
        <p>Ask about a specific trial or discover trials by condition. Results remain tied to validated backend evidence.</p>
        <form onSubmit={handleQuerySubmit} className="search-form">
          <label htmlFor="trial-query">Your question</label>
          <div className="search-row">
            <input
              id="trial-query"
              type="text"
              placeholder="Give me an overview of NCT00000102"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              disabled={queryLoading}
            />
            <button type="submit" disabled={queryLoading}>
              {queryLoading ? 'Asking...' : 'Ask query'}
            </button>
          </div>
        </form>
        {queryError && <p className="inline-error">{queryError}</p>}
        {queryResult && (
          <div className="query-result">
            <div className="section-heading">
              <h3>Query response</h3>
              <span className={`status status-${String(queryResult.status ?? '').toLowerCase()}`}>
                {String(queryResult.status ?? 'UNKNOWN')}
              </span>
            </div>
            <p className="query-message">{String(queryResult.message ?? 'The query was processed.')}</p>
            {queryResult.question && (
              <p className="query-question"><strong>Question:</strong> {queryResult.question}</p>
            )}
            {queryResult.answer && (
              <section className="query-answer-panel">
                <h4>Answer</h4>
                <div className="answer-content">
                  {queryResult.answer.split('\n').map((line, index) => (
                    <p key={index}>{line}</p>
                  ))}
                </div>
              </section>
            )}
            <ConditionResults response={queryResult.condition_search_response} />
            {queryResult.nct_id && <p><strong>NCT ID:</strong> {String(queryResult.nct_id)}</p>}
            {queryResult.intent && <p><strong>Intent:</strong> {String(queryResult.intent)}</p>}
            {queryResult.sources && queryResult.sources.length > 0 && (
              <section className="evidence-sources-panel">
                <div className="section-heading">
                  <h4>Evidence sources</h4>
                  <span>{queryResult.sources.length} sources</span>
                </div>
                <div className="source-grid">
                  {queryResult.sources.map((source, index) => (
                    <article className="source-card" key={index}>
                      <span className="source-number">Source {index + 1}</span>
                      <div><strong>Table</strong><p>{formatValue(source.source_table)}</p></div>
                      <div><strong>Key</strong><p>{formatValue(source.source_key)}</p></div>
                      <div><strong>ID</strong><p>{formatValue(source.source_id)}</p></div>
                    </article>
                  ))}
                </div>
              </section>
            )}
            {queryResult.limitations && queryResult.limitations.length > 0 && (
              <div className="limitations">
                <h4>Limitations</h4>
                <ul>{queryResult.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}</ul>
              </div>
            )}
            {queryResult.graph_response && (
              <details className="technical-subsection">
                <summary>Graph response and validation</summary>
                <div className="technical-subsection-content">
                  <div className="validation-metrics">
                    <div className="validation-metric"><span>Graph status</span><strong>{formatValue(queryResult.graph_response.status)}</strong></div>
                    <div className="validation-metric"><span>Validation</span><strong>{queryResult.graph_response.validation ? (queryResult.graph_response.validation.valid ? 'Valid' : 'Invalid') : 'Not available'}</strong></div>
                    <div className="validation-metric"><span>Errors</span><strong>{queryResult.graph_response.validation?.errors?.length ?? 0}</strong></div>
                    <div className="validation-metric"><span>Warnings</span><strong>{queryResult.graph_response.validation?.warnings?.length ?? 0}</strong></div>
                  </div>
                  <pre className="raw-json">{JSON.stringify(queryResult.graph_response, null, 2)}</pre>
                </div>
              </details>
            )}
            <details className="technical-subsection">
              <summary>Complete query response</summary>
              <div className="technical-subsection-content">
                <pre className="raw-json">{JSON.stringify(queryResult, null, 2)}</pre>
              </div>
            </details>
          </div>
        )}
      </section>

      <section className="search-card">
        <h2>Discover trials by condition</h2>
        <p>Search the indexed evidence graph for trials matching an exact normalized condition name.</p>
        <form onSubmit={handleConditionSubmit} className="search-form">
          <label htmlFor="condition-search">Condition</label>
          <div className="search-row">
            <input
              id="condition-search"
              type="text"
              placeholder="Cancer"
              value={condition}
              onChange={(event) => setCondition(event.target.value)}
              disabled={conditionLoading}
            />
            <button type="submit" disabled={conditionLoading}>
              {conditionLoading ? 'Searching...' : 'Find trials'}
            </button>
          </div>
        </form>
        {conditionError && <p className="inline-error">{conditionError}</p>}
        {conditionResult && (
          <div className="condition-search-result">
            <div className="section-heading">
              <h3>Condition search response</h3>
              <span className={`status status-${String(conditionResult.status ?? '').toLowerCase()}`}>
                {String(conditionResult.status ?? 'UNKNOWN')}
              </span>
            </div>
            <p className="query-message">{conditionResult.condition ? `Search results for ${conditionResult.condition}.` : 'The condition search was processed.'}</p>
            <ConditionResults response={conditionResult} />
          </div>
        )}
      </section>

      <section className="search-card">
        <h2>Explore a clinical trial</h2>
        <p>Enter a ClinicalTrials.gov identifier to retrieve a validated trial overview.</p>
        <form onSubmit={handleSubmit} className="search-form">
          <label htmlFor="nct-id">NCT ID</label>
          <div className="search-row">
            <input
              id="nct-id"
              type="text"
              placeholder="NCT00000102"
              value={nctId}
              onChange={(event) => setNctId(event.target.value)}
              disabled={loading}
            />
            <button type="submit" disabled={loading}>
              {loading ? 'Loading...' : 'Get overview'}
            </button>
          </div>
        </form>
      </section>

      {error && (
        <section className="result-card error-card">
          <h2>Request error</h2>
          <p>{error}</p>
        </section>
      )}

      {result && (
        <section className="result-card">
          <div className="result-heading">
            <h2>Trial overview</h2>
            <span className={`status status-${result.status.toLowerCase()}`}>
              {result.status}
            </span>
          </div>

          <div className="answer-content">
            {result.answer.split('\n').map((line, index) => (
              <p key={index}>{line}</p>
            ))}
          </div>

          <div className="trial-summary">
            <div className="summary-item">
              <span className="summary-label">NCT ID</span>
              <strong>{graphResponse?.nct_id ?? nctId}</strong>
            </div>
            <div className="summary-item">
              <span className="summary-label">Evidence status</span>
              <strong>{formatValue(graphResponse?.status)}</strong>
            </div>
            <div className="summary-item">
              <span className="summary-label">Sources</span>
              <strong>{result.sources?.length ?? 0}</strong>
            </div>
          </div>

          {result.sources && result.sources.length > 0 && (
            <section className="evidence-sources-panel">
              <div className="section-heading">
                <h3>Evidence sources</h3>
                <span>{result.sources.length} sources</span>
              </div>
              <div className="source-grid">
                {result.sources.map((source, index) => (
                  <article className="source-card" key={index}>
                    <span className="source-number">Source {index + 1}</span>
                    <div><strong>Table</strong><p>{formatValue(source.source_table)}</p></div>
                    <div><strong>Key</strong><p>{formatValue(source.source_key)}</p></div>
                    <div><strong>ID</strong><p>{formatValue(source.source_id)}</p></div>
                  </article>
                ))}
              </div>
            </section>
          )}

          {result.limitations && result.limitations.length > 0 && (
            <div className="limitations">
              <h3>Limitations</h3>
              <ul>{result.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}</ul>
            </div>
          )}

          <section className="lineage-panel">
            <div className="section-heading">
              <h3>Source lineage</h3>
              <span>Post-query source metadata</span>
            </div>
            <p className="technical-note">Retrieve source records associated with this validated trial response.</p>
            <button type="button" className="secondary-button lineage-button" onClick={() => void handleLoadLineage(graphResponse?.nct_id ?? nctId)} disabled={lineageLoading}>
              {lineageLoading ? 'Loading lineage...' : 'Load lineage'}
            </button>
            {lineageError && <p className="inline-error">{lineageError}</p>}
            {lineageResult && (
              <div className="lineage-result">
                <div className="validation-metrics">
                  <div className="validation-metric"><span>Status</span><strong>{formatValue(lineageResult.status)}</strong></div>
                  <div className="validation-metric"><span>NCT ID</span><strong>{formatValue(lineageResult.nct_id)}</strong></div>
                  <div className="validation-metric"><span>Source records</span><strong>{formatValue(lineageResult.source_count)}</strong></div>
                </div>
                {lineageResult.records && lineageResult.records.length > 0 && (
                  <div className="lineage-records">
                    {lineageResult.records.map((record, index) => (
                      <article className="source-card" key={`${record.collection ?? 'record'}-${record.record_index ?? index}`}>
                        <span className="source-number">Record {index + 1}</span>
                        <div><strong>Collection</strong><p>{formatValue(record.collection)}</p></div>
                        <div><strong>Source table</strong><p>{formatValue(record.source_table)}</p></div>
                        <div><strong>Source key</strong><p>{formatValue(record.source_key)}</p></div>
                        <div><strong>Source ID</strong><p>{formatValue(record.source_id)}</p></div>
                        <details className="provenance-details">
                          <summary>Provenance metadata</summary>
                          <div><strong>Pipeline run</strong><p>{formatValue(record.pipeline_run_id)}</p></div>
                          <div><strong>Source database</strong><p>{formatValue(record.source_database)}</p></div>
                          <div><strong>Source schema</strong><p>{formatValue(record.source_schema)}</p></div>
                          <div><strong>Extraction time</strong><p>{formatValue(record.extracted_at_utc)}</p></div>
                          <div><strong>Transformation version</strong><p>{formatValue(record.transformation_version)}</p></div>
                        </details>
                      </article>
                    ))}
                  </div>
                )}
                {lineageResult.limitations && lineageResult.limitations.length > 0 && (
                  <div className="limitations"><h4>Lineage limitations</h4><ul>{lineageResult.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></div>
                )}
                <details className="technical-subsection">
                  <summary>Complete lineage response</summary>
                  <div className="technical-subsection-content"><pre className="raw-json">{JSON.stringify(lineageResult, null, 2)}</pre></div>
                </details>
              </div>
            )}
          </section>

          {graphResponse && (
            <details className="technical-details">
              <summary>Evidence and validation details</summary>
              <div className="technical-content">
                <section className="technical-section">
                  <div className="section-heading">
                    <h3>Validation summary</h3>
                    <span className={validation?.valid ? 'validation-valid' : 'validation-invalid'}>
                      {validation ? (validation.valid ? 'Valid' : 'Invalid') : 'Not available'}
                    </span>
                  </div>
                  <div className="validation-metrics">
                    <div className="validation-metric"><span>Errors</span><strong>{validationErrors.length}</strong></div>
                    <div className="validation-metric"><span>Warnings</span><strong>{validationWarnings.length}</strong></div>
                    <div className="validation-metric"><span>Graph status</span><strong>{formatValue(graphResponse.status)}</strong></div>
                  </div>
                  {validationErrors.length > 0 && <div className="validation-list"><h4>Validation errors</h4><ul>{validationErrors.map((item, index) => <li key={index}>{item}</li>)}</ul></div>}
                  {validationWarnings.length > 0 && <div className="validation-list"><h4>Validation warnings</h4><ul>{validationWarnings.map((item, index) => <li key={index}>{item}</li>)}</ul></div>}
                </section>

                {evidence && (
                  <details className="technical-section technical-subsection">
                    <summary>
                      <span>Evidence record inspector</span>
                      <span className="section-summary-meta">Structured records</span>
                    </summary>
                    <div className="technical-subsection-content">
                      {EVIDENCE_COLLECTIONS.map((collectionName) => (
                        <EvidenceCollection key={collectionName} collectionName={collectionName} value={evidence[collectionName]} />
                      ))}
                    </div>
                  </details>
                )}

                <details className="technical-section technical-subsection">
                  <summary>
                    <span>Raw graph response</span>
                    <span className="section-summary-actions">
                      <button type="button" className="secondary-button" onClick={(event) => { event.preventDefault(); void copyRawResponse() }}>
                        {rawCopied ? 'Copied' : 'Copy JSON'}
                      </button>
                    </span>
                  </summary>
                  <div className="technical-subsection-content">
                    <p className="technical-note">Complete response preserved for traceability. Expand or copy the JSON for debugging and verification.</p>
                    <pre className="raw-json">{JSON.stringify(graphResponse, null, 2)}</pre>
                  </div>
                </details>
              </div>
            </details>
          )}
        </section>
      )}

      {!result && !error && !loading && (
        <section className="empty-state">
          <h2>Ready to investigate</h2>
          <p>Your evidence-grounded trial overview will appear here.</p>
        </section>
      )}
    </main>
  )
}

export default App
