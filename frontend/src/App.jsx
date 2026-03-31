import React, { memo, startTransition, useDeferredValue, useEffect, useMemo, useReducer, useRef, useState } from 'react'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'https://nps-analyzer.onrender.com'
const ACCEPTED_TYPES = '.xlsx,.xls'
const POLL_INTERVAL_MS = 1800

const initialState = {
  file: null,
  dragActive: false,
  uploadError: '',
  submitStatus: 'idle',
  jobId: '',
  progress: { current: 0, total: 1, percent: 0, status: 'idle', message: '' },
  result: null,
}

function reducer(state, action) {
  switch (action.type) {
    case 'setFile':
      return { ...state, file: action.file, uploadError: '', result: null }
    case 'setDragActive':
      return { ...state, dragActive: action.value }
    case 'setError':
      return { ...state, uploadError: action.message, submitStatus: 'error' }
    case 'startUpload':
      return {
        ...state,
        uploadError: '',
        submitStatus: 'uploading',
        result: null,
        progress: { current: 0, total: 1, percent: 0, status: 'queued', message: 'Uploading file' },
      }
    case 'setJob':
      return {
        ...state,
        jobId: action.jobId,
        submitStatus: 'processing',
        progress: { ...state.progress, status: 'queued', message: action.message ?? 'Processing started' },
      }
    case 'setProgress':
      return {
        ...state,
        progress: {
          current: action.progress.current ?? 0,
          total: action.progress.total ?? 1,
          percent: action.progress.percent ?? 0,
          status: action.progress.status ?? 'processing',
          message: action.progress.message ?? 'Processing',
        },
      }
    case 'setResult':
      return {
        ...state,
        submitStatus: 'completed',
        result: action.result,
        progress: { ...state.progress, percent: 100, status: 'completed', message: 'Analysis complete' },
      }
    case 'setProcessingError':
      return {
        ...state,
        submitStatus: 'error',
        uploadError: action.message,
        progress: { ...state.progress, status: 'failed', message: 'Processing failed' },
      }
    default:
      return state
  }
}

function formatMetricValue(metric, value) {
  if (typeof value !== 'number') return value
  if (metric === 'Total Responses') return value.toLocaleString()
  return `${value.toFixed(2)}%`
}

const MetricCard = memo(function MetricCard({ metric, value }) {
  return (
    <article className="metric-card">
      <span className="metric-card__label">{metric}</span>
      <strong className="metric-card__value">{formatMetricValue(metric, value)}</strong>
    </article>
  )
})

const InsightList = memo(function InsightList({ title, items, itemKey, renderValue, emptyState }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h3>{title}</h3>
      </div>
      {items?.length ? (
        <ul className="panel__list">
          {items.map((item, index) => (
            <li className="panel__list-item" key={`${item[itemKey] ?? title}-${index}`}>
              {renderValue(item)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="panel__empty">{emptyState}</p>
      )}
    </section>
  )
})

const FocusAreaPanel = memo(function FocusAreaPanel({ items }) {
  const categories = useMemo(() => [...new Set((items ?? []).map((item) => item['NPS Category']))], [items])
  const [activeCategory, setActiveCategory] = useState('Detractor')
  const selectedCategory = categories.includes(activeCategory) ? activeCategory : (categories[0] ?? 'Detractor')

  useEffect(() => {
    if (!categories.includes(activeCategory) && categories[0]) {
      setActiveCategory(categories[0])
    }
  }, [activeCategory, categories])

  const filteredItems = useMemo(() => {
    const selected = (items ?? []).filter((item) => item['NPS Category'] === selectedCategory)
    const maxCount = Math.max(...selected.map((item) => item.Count), 1)
    return selected.map((item) => ({ ...item, width: `${(item.Count / maxCount) * 100}%` }))
  }, [items, selectedCategory])

  return (
    <section className="panel panel--focus">
      <div className="panel__header">
        <div>
          <h3>Priority Focus Areas</h3>
          <p>Interactive breakdown for passive and detractor themes.</p>
        </div>
      </div>

      {categories.length ? (
        <>
          <div className="segmented-control" role="tablist" aria-label="Focus area category">
            {categories.map((category) => (
              <button
                key={category}
                type="button"
                className={`segmented-control__button ${selectedCategory === category ? 'segmented-control__button--active' : ''}`}
                onClick={() => setActiveCategory(category)}
              >
                {category}
              </button>
            ))}
          </div>

          <div className="focus-chart">
            {filteredItems.map((item) => (
              <button key={`${item.Theme}-${item['NPS Category']}`} type="button" className="focus-chart__row" title={`${item.Theme}: ${item.Count}`}>
                <span className="focus-chart__label">{item.Theme}</span>
                <span className="focus-chart__track">
                  <span className="focus-chart__bar" style={{ width: item.width }} />
                </span>
                <strong className="focus-chart__value">{item.Count}</strong>
              </button>
            ))}
          </div>
        </>
      ) : (
        <p className="panel__empty">Passive and detractor themes will appear here after analysis.</p>
      )}
    </section>
  )
})

const AvoidableImpactPanel = memo(function AvoidableImpactPanel({ items }) {
  const groupedItems = useMemo(() => {
    const grouped = new Map()
    for (const item of items ?? []) {
      const surveyType = item['Survey Type']
      if (!grouped.has(surveyType)) grouped.set(surveyType, [])
      grouped.get(surveyType).push(item)
    }
    return [...grouped.entries()]
  }, [items])

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <h3>Avoidable Impact</h3>
          <p>Split clearly by survey type. Promoters are excluded from this view.</p>
        </div>
      </div>
      {groupedItems.length ? (
        <div className="impact-groups">
          {groupedItems.map(([surveyType, records]) => (
            <div className="impact-group" key={surveyType}>
              <h4>{surveyType} Surveys</h4>
              <ul className="panel__list">
                {records.map((item) => (
                  <li className="panel__list-item" key={`${surveyType}-${item['Impact Classification']}`}>
                    <span>{item['Impact Classification']}</span>
                    <strong>{item.Count}</strong>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : (
        <p className="panel__empty">Avoidable classification will appear here for passive and detractor surveys.</p>
      )}
    </section>
  )
})

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const deferredResult = useDeferredValue(state.result)
  const pollTimerRef = useRef(null)

  const selectedFileMeta = useMemo(() => {
    if (!state.file) return null
    return {
      name: state.file.name,
      sizeLabel: `${(state.file.size / 1024 / 1024).toFixed(2)} MB`,
    }
  }, [state.file])

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) window.clearTimeout(pollTimerRef.current)
    }
  }, [])

  useEffect(() => {
    if (!state.jobId || state.submitStatus !== 'processing') return undefined

    let cancelled = false

    const poll = async () => {
      try {
        const response = await fetch(`${BASE_URL}/api/progress/${state.jobId}`)
        const payload = await response.json()

        if (!response.ok) throw new Error(payload.detail || 'Unable to fetch job progress.')
        if (cancelled) return

        dispatch({ type: 'setProgress', progress: payload })

        if (payload.status === 'completed' && payload.result) {
          startTransition(() => {
            dispatch({ type: 'setResult', result: payload.result })
          })
          return
        }

        if (payload.status === 'failed') {
          dispatch({ type: 'setProcessingError', message: payload.error || 'Processing failed.' })
          return
        }

        pollTimerRef.current = window.setTimeout(poll, POLL_INTERVAL_MS)
      } catch (error) {
        if (!cancelled) {
          dispatch({ type: 'setProcessingError', message: error.message || 'Backend not reachable.' })
        }
      }
    }

    poll()

    return () => {
      cancelled = true
      if (pollTimerRef.current) window.clearTimeout(pollTimerRef.current)
    }
  }, [state.jobId, state.submitStatus])

  const handleFileSelection = (file) => {
    if (!file) return
    const isExcel = file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls')
    if (!isExcel) {
      dispatch({ type: 'setError', message: 'Please upload an Excel file in .xlsx or .xls format.' })
      return
    }
    dispatch({ type: 'setFile', file })
  }

  const handleUpload = async () => {
    if (!state.file) {
      dispatch({ type: 'setError', message: 'Choose an Excel file before starting analysis.' })
      return
    }

    dispatch({ type: 'startUpload' })

    const form = new FormData()
    form.append('file', state.file)

    try {
      const response = await fetch(`${BASE_URL}/api/upload`, {
        method: 'POST',
        body: form,
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Upload failed.')
      dispatch({ type: 'setJob', jobId: payload.job_id, message: payload.message })
    } catch (error) {
      dispatch({ type: 'setProcessingError', message: error.message || 'Backend not reachable.' })
    }
  }

  return (
    <div className="app-shell">
      <div className="app-shell__backdrop app-shell__backdrop--left" />
      <div className="app-shell__backdrop app-shell__backdrop--right" />

      <main className="app-layout">
        <section className="hero-card">
          <div className="hero-card__eyebrow">NPS Final</div>
          <div className="hero-card__grid">
            <div>
              <h1>Turn raw customer feedback into faster, cleaner decisions.</h1>
              <p className="hero-card__copy">
                Upload your NPS workbook, track live analysis progress, and review KPI, passive and detractor themes, and service-impact insights in one place.
              </p>
              <div className="hero-card__stats">
                <div>
                  <span>Translation scope</span>
                  <strong>Only SA Question 6 comments are translated</strong>
                </div>
                <div>
                  <span>Avoidable logic</span>
                  <strong>Only passives and detractors are classified</strong>
                </div>
              </div>
            </div>

            <section className="upload-card">
              <label
                className={`dropzone ${state.dragActive ? 'dropzone--active' : ''}`}
                onDragEnter={() => dispatch({ type: 'setDragActive', value: true })}
                onDragOver={(event) => {
                  event.preventDefault()
                  dispatch({ type: 'setDragActive', value: true })
                }}
                onDragLeave={() => dispatch({ type: 'setDragActive', value: false })}
                onDrop={(event) => {
                  event.preventDefault()
                  dispatch({ type: 'setDragActive', value: false })
                  handleFileSelection(event.dataTransfer.files?.[0])
                }}
              >
                <input type="file" accept={ACCEPTED_TYPES} onChange={(event) => handleFileSelection(event.target.files?.[0])} />
                <span className="dropzone__title">Drop your Excel file here</span>
                <span className="dropzone__subtitle">or click to browse local files</span>
                {selectedFileMeta ? (
                  <div className="file-pill">
                    <strong>{selectedFileMeta.name}</strong>
                    <span>{selectedFileMeta.sizeLabel}</span>
                  </div>
                ) : (
                  <span className="dropzone__hint">Supports .xlsx and .xls uploads up to 15 MB.</span>
                )}
              </label>

              <button className="primary-button" onClick={handleUpload} disabled={state.submitStatus === 'uploading' || state.submitStatus === 'processing'}>
                {state.submitStatus === 'uploading' || state.submitStatus === 'processing' ? 'Analyzing workbook...' : 'Upload and analyze'}
              </button>

              <div className="status-card">
                <div className="status-card__row">
                  <span>Status</span>
                  <strong>{state.progress.message || 'Waiting for file upload'}</strong>
                </div>
                <div className="progress-bar" aria-hidden="true">
                  <div className="progress-bar__value" style={{ width: `${state.progress.percent || 0}%` }} />
                </div>
                <div className="status-card__row status-card__row--muted">
                  <span>Progress</span>
                  <strong>{state.progress.percent || 0}%</strong>
                </div>
              </div>

              {state.uploadError ? <p className="feedback feedback--error">{state.uploadError}</p> : null}
            </section>
          </div>
        </section>

        <section className="results-grid">
          <section className="panel panel--metrics">
            <div className="panel__header">
              <h2>Overview</h2>
              <p>High-level performance indicators from the latest uploaded workbook.</p>
            </div>
            {deferredResult?.kpi?.length ? (
              <div className="metric-grid">
                {deferredResult.kpi.map((item, index) => (
                  <MetricCard key={`${item.Metric}-${index}`} metric={item.Metric} value={item.Value} />
                ))}
              </div>
            ) : (
              <p className="panel__empty">Run an analysis to populate your KPI dashboard.</p>
            )}
          </section>

          <FocusAreaPanel items={deferredResult?.focus_areas} />

          <AvoidableImpactPanel items={deferredResult?.avoidable_summary} />

          <InsightList
            title="Executive Insights"
            items={deferredResult?.insights}
            itemKey="Insights"
            emptyState="Your executive summary will appear here after processing."
            renderValue={(item) => <span>{item.Insights}</span>}
          />
        </section>

        {deferredResult?.download_url ? (
          <section className="download-banner">
            <div>
              <h3>Processed workbook ready</h3>
              <p>Download the enriched Excel file with detailed data, summary sheets, KPI tables, and refined passive and detractor reporting.</p>
            </div>
            <a className="secondary-button" href={`${BASE_URL}${deferredResult.download_url}`} target="_blank" rel="noreferrer">
              Download output
            </a>
          </section>
        ) : null}
      </main>
    </div>
  )
}
