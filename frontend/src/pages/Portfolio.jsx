import { useEffect, useRef, useState } from 'react'

const API = ''

const TICKERS = [
  { symbol: 'AAPL',  name: 'Apple Inc',                    sector: 'Technology' },
  { symbol: 'MSFT',  name: 'Microsoft Corp',                sector: 'Technology' },
  { symbol: 'NVDA',  name: 'NVIDIA Corp',                   sector: 'Technology' },
  { symbol: 'GOOGL', name: 'Alphabet Inc',                  sector: 'Technology' },
  { symbol: 'META',  name: 'Meta Platforms',                sector: 'Technology' },
  { symbol: 'AMZN',  name: 'Amazon.com Inc',                sector: 'Technology' },
  { symbol: 'TSLA',  name: 'Tesla Inc',                     sector: 'Technology' },
  { symbol: 'AMD',   name: 'Advanced Micro Devices',        sector: 'Technology' },
  { symbol: 'INTC',  name: 'Intel Corp',                    sector: 'Technology' },
  { symbol: 'CRM',   name: 'Salesforce Inc',                sector: 'Technology' },
  { symbol: 'JPM',   name: 'JPMorgan Chase',                sector: 'Financials' },
  { symbol: 'BAC',   name: 'Bank of America',               sector: 'Financials' },
  { symbol: 'GS',    name: 'Goldman Sachs',                 sector: 'Financials' },
  { symbol: 'MS',    name: 'Morgan Stanley',                sector: 'Financials' },
  { symbol: 'WFC',   name: 'Wells Fargo',                   sector: 'Financials' },
  { symbol: 'C',     name: 'Citigroup Inc',                 sector: 'Financials' },
  { symbol: 'BLK',   name: 'BlackRock Inc',                 sector: 'Financials' },
  { symbol: 'AXP',   name: 'American Express',              sector: 'Financials' },
  { symbol: 'USB',   name: 'US Bancorp',                    sector: 'Financials' },
  { symbol: 'COF',   name: 'Capital One Financial',         sector: 'Financials' },
  { symbol: 'XOM',   name: 'Exxon Mobil',                   sector: 'Energy' },
  { symbol: 'CVX',   name: 'Chevron Corp',                  sector: 'Energy' },
  { symbol: 'COP',   name: 'ConocoPhillips',                sector: 'Energy' },
  { symbol: 'EOG',   name: 'EOG Resources',                 sector: 'Energy' },
  { symbol: 'SLB',   name: 'SLB (Schlumberger)',            sector: 'Energy' },
  { symbol: 'PSX',   name: 'Phillips 66',                   sector: 'Energy' },
  { symbol: 'MPC',   name: 'Marathon Petroleum',            sector: 'Energy' },
  { symbol: 'VLO',   name: 'Valero Energy',                 sector: 'Energy' },
  { symbol: 'OXY',   name: 'Occidental Petroleum',          sector: 'Energy' },
  { symbol: 'HAL',   name: 'Halliburton Co',                sector: 'Energy' },
  { symbol: 'JNJ',   name: 'Johnson & Johnson',             sector: 'Healthcare' },
  { symbol: 'UNH',   name: 'UnitedHealth Group',            sector: 'Healthcare' },
  { symbol: 'PFE',   name: 'Pfizer Inc',                    sector: 'Healthcare' },
  { symbol: 'ABBV',  name: 'AbbVie Inc',                    sector: 'Healthcare' },
  { symbol: 'MRK',   name: 'Merck & Co',                    sector: 'Healthcare' },
  { symbol: 'TMO',   name: 'Thermo Fisher Scientific',      sector: 'Healthcare' },
  { symbol: 'ABT',   name: 'Abbott Laboratories',           sector: 'Healthcare' },
  { symbol: 'DHR',   name: 'Danaher Corp',                  sector: 'Healthcare' },
  { symbol: 'BMY',   name: 'Bristol-Myers Squibb',          sector: 'Healthcare' },
  { symbol: 'AMGN',  name: 'Amgen Inc',                     sector: 'Healthcare' },
  { symbol: 'HD',    name: 'Home Depot',                    sector: 'Consumer Discretionary' },
  { symbol: 'MCD',   name: "McDonald's Corp",               sector: 'Consumer Discretionary' },
  { symbol: 'NKE',   name: 'Nike Inc',                      sector: 'Consumer Discretionary' },
  { symbol: 'SBUX',  name: 'Starbucks Corp',                sector: 'Consumer Discretionary' },
  { symbol: 'TGT',   name: 'Target Corp',                   sector: 'Consumer Discretionary' },
  { symbol: 'LOW',   name: "Lowe's Companies",              sector: 'Consumer Discretionary' },
  { symbol: 'TJX',   name: 'TJX Companies',                 sector: 'Consumer Discretionary' },
  { symbol: 'BKNG',  name: 'Booking Holdings',              sector: 'Consumer Discretionary' },
  { symbol: 'MAR',   name: 'Marriott International',        sector: 'Consumer Discretionary' },
  { symbol: 'COST',  name: 'Costco Wholesale',              sector: 'Consumer Discretionary' },
]

const EMPTY_FORM = { symbol: '', shares: '', avg_cost: '' }

function fmt(n, decimals = 2) {
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

function PnlCell({ value }) {
  const pos = value >= 0
  return (
    <span className={pos ? 'text-green-400' : 'text-red-400'}>
      {pos ? '+' : ''}{fmt(value)}
    </span>
  )
}

function TickerInput({ value, onChange }) {
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(0)
  const containerRef = useRef(null)

  const suggestions = value.trim().length === 0 ? [] : TICKERS.filter((t) =>
    t.symbol.startsWith(value.toUpperCase()) ||
    t.name.toLowerCase().includes(value.toLowerCase())
  ).slice(0, 8)

  useEffect(() => { setHighlighted(0) }, [value])

  // Close on outside click
  useEffect(() => {
    function handler(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function select(ticker) {
    onChange(ticker.symbol)
    setOpen(false)
  }

  function handleKey(e) {
    if (!open || !suggestions.length) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setHighlighted((i) => Math.min(i + 1, suggestions.length - 1)) }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setHighlighted((i) => Math.max(i - 1, 0)) }
    if (e.key === 'Enter')     { e.preventDefault(); select(suggestions[highlighted]) }
    if (e.key === 'Escape')    { setOpen(false) }
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 w-36 focus:outline-none focus:border-blue-500"
        placeholder="Ticker or name"
        value={value}
        onChange={(e) => { onChange(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKey}
        autoComplete="off"
      />
      {open && suggestions.length > 0 && (
        <ul className="absolute z-50 left-0 top-full mt-1 w-72 bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden">
          {suggestions.map((t, i) => (
            <li
              key={t.symbol}
              onMouseDown={() => select(t)}
              onMouseEnter={() => setHighlighted(i)}
              className={`flex items-center gap-3 px-3 py-2 cursor-pointer text-sm ${i === highlighted ? 'bg-gray-800' : ''}`}
            >
              <span className="font-mono text-blue-300 w-14 shrink-0">{t.symbol}</span>
              <span className="text-gray-300 truncate flex-1">{t.name}</span>
              <span className="text-gray-600 text-xs shrink-0">{t.sector.split(' ')[0]}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function Portfolio() {
  const [holdings, setHoldings] = useState(() => {
    try { return JSON.parse(localStorage.getItem('finsight_holdings') || '[]') }
    catch { return [] }
  })
  const [form, setForm] = useState(EMPTY_FORM)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    localStorage.setItem('finsight_holdings', JSON.stringify(holdings))
  }, [holdings])

  function addHolding(e) {
    e.preventDefault()
    const sym = form.symbol.trim().toUpperCase()
    const shares = parseFloat(form.shares)
    const avg_cost = parseFloat(form.avg_cost)
    if (!sym || isNaN(shares) || isNaN(avg_cost) || shares <= 0 || avg_cost <= 0) return
    setHoldings((h) => [...h.filter((x) => x.symbol !== sym), { symbol: sym, shares, avg_cost }])
    setForm(EMPTY_FORM)
    setResult(null)
  }

  function removeHolding(sym) {
    setHoldings((h) => h.filter((x) => x.symbol !== sym))
    setResult(null)
  }

  async function calculate() {
    if (!holdings.length) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/portfolio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ holdings }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(d.detail || `HTTP ${res.status}`)
      }
      setResult(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">

      {/* Add holding form */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">Holdings</h2>
        <form onSubmit={addHolding} className="flex gap-3 flex-wrap items-start">
          <TickerInput value={form.symbol} onChange={(v) => setForm((f) => ({ ...f, symbol: v }))} />
          <input
            type="number" min="0" step="any"
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 w-32 focus:outline-none focus:border-blue-500"
            placeholder="Shares"
            value={form.shares}
            onChange={(e) => setForm((f) => ({ ...f, shares: e.target.value }))}
          />
          <input
            type="number" min="0" step="any"
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 w-36 focus:outline-none focus:border-blue-500"
            placeholder="Avg cost / share"
            value={form.avg_cost}
            onChange={(e) => setForm((f) => ({ ...f, avg_cost: e.target.value }))}
          />
          <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded transition">
            Add
          </button>
        </form>
      </div>

      {/* Holdings list */}
      {holdings.length > 0 && (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {holdings.map((h) => (
              <div key={h.symbol} className="flex items-center gap-2 bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm">
                <span className="text-blue-300 font-mono font-medium">{h.symbol}</span>
                <span className="text-gray-400">{h.shares} @ ${fmt(h.avg_cost)}</span>
                <button onClick={() => removeHolding(h.symbol)} className="text-gray-600 hover:text-red-400 transition text-xs ml-1">✕</button>
              </div>
            ))}
          </div>
          <button
            onClick={calculate}
            disabled={loading}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm rounded transition"
          >
            {loading ? 'Calculating…' : 'Calculate P&L'}
          </button>
        </div>
      )}

      {error && (
        <div className="bg-red-950 border border-red-800 rounded-lg px-4 py-3 text-sm text-red-300">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">

          {/* Summary bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Market Value', value: `$${fmt(result.total_value)}` },
              { label: 'Total Cost', value: `$${fmt(result.total_cost)}` },
              { label: 'Total P&L', value: <PnlCell value={result.total_pnl} /> },
              { label: 'Return', value: <PnlCell value={result.total_pnl_pct} /> },
            ].map(({ label, value }) => (
              <div key={label} className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3">
                <div className="text-xs text-gray-500 mb-1">{label}</div>
                <div className="text-lg font-semibold text-gray-100">{value}</div>
              </div>
            ))}
          </div>

          {/* Positions table */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Positions</h3>
            <div className="overflow-x-auto rounded-lg border border-gray-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-xs text-gray-500 uppercase">
                    {['Symbol', 'Company', 'Sector', 'Shares', 'Avg Cost', 'Price', 'Value', 'P&L', 'Return'].map((h) => (
                      <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.positions.map((p) => (
                    <tr key={p.symbol} className="border-b border-gray-900 hover:bg-gray-900/50">
                      <td className="px-3 py-2 font-mono text-blue-300">{p.symbol}</td>
                      <td className="px-3 py-2 text-gray-300">{p.company_name}</td>
                      <td className="px-3 py-2 text-gray-400">{p.sector}</td>
                      <td className="px-3 py-2 text-gray-300">{p.shares}</td>
                      <td className="px-3 py-2 text-gray-300">${fmt(p.avg_cost)}</td>
                      <td className="px-3 py-2 text-gray-300">${fmt(p.current_price)}</td>
                      <td className="px-3 py-2 text-gray-200">${fmt(p.value)}</td>
                      <td className="px-3 py-2"><PnlCell value={p.pnl} /></td>
                      <td className="px-3 py-2"><PnlCell value={p.pnl_pct} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Sector exposure */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Sector Exposure</h3>
            <div className="space-y-2">
              {result.sector_exposure.map((s) => (
                <div key={s.sector} className="flex items-center gap-3">
                  <span className="text-sm text-gray-400 w-48 shrink-0">{s.sector}</span>
                  <div className="flex-1 bg-gray-900 rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${s.pct}%` }} />
                  </div>
                  <span className="text-sm text-gray-300 w-16 text-right">{s.pct}%</span>
                  <span className="text-sm text-gray-500 w-28 text-right">${fmt(s.value)}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-gray-600">Prices as of {result.as_of_date} (end-of-day Gold data)</p>
        </div>
      )}

      {holdings.length === 0 && (
        <div className="text-center py-16 text-gray-600 text-sm">
          Add your holdings above to calculate portfolio value and P&L.
        </div>
      )}
    </div>
  )
}
