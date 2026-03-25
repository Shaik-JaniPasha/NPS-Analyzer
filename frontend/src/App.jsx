import React, { useState } from 'react'
import { useMediaQuery } from 'react-responsive'

export default function App() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const isMobile = useMediaQuery({ maxWidth: 767 })
  const isTablet = useMediaQuery({ minWidth: 768, maxWidth: 1023 })
  const isDesktop = useMediaQuery({ minWidth: 1024 })

  const onFileChange = (e) => setFile(e.target.files[0])

  const upload = async () => {
    if (!file) return alert('Choose a file')

    setLoading(true)
    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch('http://127.0.0.1:8000/api/upload', {
        method: 'POST',
        body: form,
      })

      const data = await res.json()

      if (!res.ok) {
        setResult({ error: data.detail || 'Upload failed' })
      } else {
        setResult(data)
      }
    } catch (e) {
      setResult({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  const download = () => {
    if (result && result.download_file) {
      window.open(`http://localhost:8000/${result.download_file}`, '_blank')
    } else {
      alert("No file available")
    }
  }

  return (
    <div className={`container ${isMobile ? 'mobile' : isTablet ? 'tablet' : 'desktop'}`}>
      
      <header>
        <h1>🚀 NPS Analyzer</h1>
      </header>

      <main>
        <div className="upload-card">
          
          <input type="file" onChange={onFileChange} accept=".xlsx,.xls" />
          
          <button onClick={upload} disabled={loading}>
            {loading ? 'Processing...' : 'Upload & Analyze'}
          </button>

          <div style={{ marginTop: 10 }}>
            {loading && <span style={{ color: '#0366d6' }}>Processing... please wait.</span>}
            {!loading && result && !result.error && (
              <span style={{ color: 'green' }}>✅ Analysis complete</span>
            )}
            {!loading && result && result.error && (
              <span style={{ color: 'red' }}>❌ Error: {result.error}</span>
            )}
          </div>

          {result && !result.error && (
            <div className="result">

              {/* 🔥 KPIs */}
              <h2>📊 KPIs</h2>
              <ul>
                <li>Total Responses: {result.kpis?.["Total Responses"]}</li>
                <li>Positive %: {result.kpis?.["Positive %"]}</li>
                <li>Negative %: {result.kpis?.["Negative %"]}</li>
                <li>Neutral %: {result.kpis?.["Neutral %"]}</li>
                <li>Avoidable Issues %: {result.kpis?.["Avoidable Issues %"]}</li>
              </ul>

              {/* 🔥 Focus Areas */}
              <h3>🎯 Focus Areas</h3>
              <ul>
                {result.focus_areas?.map((f, i) => (
                  <li key={i}>{f.Theme}: {f.Count}</li>
                ))}
              </ul>

              {/* 🔥 KEY INSIGHTS (NEW FEATURE) */}
              <h3>💡 Key Insights</h3>
              <ul>
                {result.insights?.map((ins, i) => (
                  <li key={i}>{ins}</li>
                ))}
              </ul>

              {/* 🔽 Download */}
              <button onClick={download}>⬇ Download Excel</button>

            </div>
          )}

        </div>
      </main>

      <footer>
        <small>
          Responsive: {isMobile ? 'Mobile' : isTablet ? 'Tablet' : 'Desktop'}
        </small>
      </footer>
    </div>
  )
}