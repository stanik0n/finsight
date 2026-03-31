import { useState } from 'react'
import QueryInput from '../components/QueryInput'
import SqlPanel from '../components/SqlPanel'
import ResultsTable from '../components/ResultsTable'

const API = ''  // empty = same origin (proxied by Vite in dev)

export default function Chat() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleQuestion(question) {
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })

      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(detail.detail || `HTTP ${res.status}`)
      }

      const data = await res.json()
      setHistory((h) => [data, ...h])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">

      <QueryInput onSubmit={handleQuestion} loading={loading} />

      {error && (
        <div className="bg-red-950 border border-red-800 rounded-lg px-4 py-3 text-sm text-red-300">
          <strong>Error:</strong> {error}
        </div>
      )}

      {loading && (
        <div className="text-center py-12 text-gray-500 text-sm animate-pulse">
          Generating SQL and querying data…
        </div>
      )}

      <div className="space-y-10">
        {history.map((entry, i) => (
          <div key={i} className="space-y-4">
            {/* Question */}
            <div className="flex items-start gap-3">
              <span className="mt-0.5 text-xs px-2 py-0.5 rounded bg-blue-900 text-blue-300 font-mono shrink-0">Q</span>
              <p className="text-gray-200 text-sm">{entry.question}</p>
            </div>

            {/* Generated SQL */}
            <SqlPanel sql={entry.sql} path={entry.path} />

            {/* Results table */}
            <ResultsTable results={entry.results} />
          </div>
        ))}
      </div>

      {history.length === 0 && !loading && (
        <div className="text-center py-16 text-gray-600 text-sm">
          Ask a question about US stock market data above.
          <br />
          <span className="text-gray-700 text-xs">
            Powered by Qwen2.5-7B via Groq · DuckDB · 50 tickers across 5 sectors
          </span>
        </div>
      )}
    </div>
  )
}
