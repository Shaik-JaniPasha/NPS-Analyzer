import React, { useState } from 'react'

// ✅ Your LIVE backend (Render)
const BASE_URL = "https://nps-analyzer.onrender.com"

export default function App() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const upload = async () => {
    if (!file) return alert('Please upload a file')

    setLoading(true)
    setResult(null)

    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch(`${BASE_URL}/api/upload`, {
        method: 'POST',
        body: form
      })

      const data = await res.json()

      if (!res.ok) {
        setResult({ error: data.detail || 'Upload failed' })
      } else {
        setResult(data)
      }

    } catch (err) {
      setResult({ error: 'Backend not reachable' })
    }

    setLoading(false)
  }

  return (
    <div style={{ fontFamily: 'Arial', background: '#f4f6f8', minHeight: '100vh', padding: '40px' }}>
      
      <h1 style={{ textAlign: 'center' }}>🚀 NPS Analyzer</h1>
      <p style={{ textAlign: 'center', color: '#555' }}>
        Upload your customer feedback and get instant insights
      </p>

      <div style={{ 
        maxWidth: 600, 
        margin: 'auto', 
        background: '#fff', 
        padding: 20, 
        borderRadius: 10, 
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)' 
      }}>

        <input type="file" onChange={(e) => setFile(e.target.files[0])} />
        <br /><br />

        <button onClick={upload} disabled={loading} style={{
          padding: '10px 20px',
          background: '#007bff',
          color: '#fff',
          border: 'none',
          borderRadius: 5,
          cursor: 'pointer'
        }}>
          {loading ? 'Processing...' : 'Upload & Analyze'}
        </button>

        {loading && <p style={{ marginTop: 10 }}>⏳ Processing your file...</p>}

        {result?.error && (
          <p style={{ color: 'red', marginTop: 10 }}>❌ {result.error}</p>
        )}

        {result && !result.error && (
          <>
            <h3>📊 KPIs</h3>
            <ul>
              {result.kpi.map((k, i) => (
                <li key={i}>{k.Metric}: <strong>{k.Value}</strong></li>
              ))}
            </ul>

            <h3>🎯 Focus Areas</h3>
            <ul>
              {result.focus_areas.map((f, i) => (
                <li key={i}>{f.Theme}: <strong>{f.Count}</strong></li>
              ))}
            </ul>

            <h3>💡 Insights</h3>
            <ul>
              {result.insights.map((ins, i) => (
                <li key={i}>{ins.Insights}</li>
              ))}
            </ul>

            <button 
              onClick={() => window.open(`${BASE_URL}${result.download_url}`)}
              style={{
                marginTop: 15,
                padding: '10px 20px',
                background: 'green',
                color: '#fff',
                border: 'none',
                borderRadius: 5,
                cursor: 'pointer'
              }}
            >
              Download file
            </button>
          </>
        )}

      </div>
    </div>
  )
}