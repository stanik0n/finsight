import { useEffect, useMemo, useRef, useState } from 'react'
import { SignInButton } from '@clerk/react'
import { authedFetch } from '../lib/api'
import { useFinsightAuth } from '../lib/finsight-auth'

const TICKERS = [
  { symbol: 'AAPL', name: 'Apple Inc', sector: 'Technology' },
  { symbol: 'MSFT', name: 'Microsoft Corp', sector: 'Technology' },
  { symbol: 'NVDA', name: 'NVIDIA Corp', sector: 'Technology' },
  { symbol: 'GOOGL', name: 'Alphabet Inc', sector: 'Technology' },
  { symbol: 'META', name: 'Meta Platforms', sector: 'Technology' },
  { symbol: 'AMZN', name: 'Amazon.com Inc', sector: 'Technology' },
  { symbol: 'TSLA', name: 'Tesla Inc', sector: 'Technology' },
  { symbol: 'AMD', name: 'Advanced Micro Devices', sector: 'Technology' },
  { symbol: 'INTC', name: 'Intel Corp', sector: 'Technology' },
  { symbol: 'CRM', name: 'Salesforce Inc', sector: 'Technology' },
  { symbol: 'JPM', name: 'JPMorgan Chase', sector: 'Financials' },
  { symbol: 'BAC', name: 'Bank of America', sector: 'Financials' },
  { symbol: 'GS', name: 'Goldman Sachs', sector: 'Financials' },
  { symbol: 'MS', name: 'Morgan Stanley', sector: 'Financials' },
  { symbol: 'WFC', name: 'Wells Fargo', sector: 'Financials' },
  { symbol: 'C', name: 'Citigroup Inc', sector: 'Financials' },
  { symbol: 'BLK', name: 'BlackRock Inc', sector: 'Financials' },
  { symbol: 'AXP', name: 'American Express', sector: 'Financials' },
  { symbol: 'USB', name: 'US Bancorp', sector: 'Financials' },
  { symbol: 'COF', name: 'Capital One Financial', sector: 'Financials' },
  { symbol: 'XOM', name: 'Exxon Mobil', sector: 'Energy' },
  { symbol: 'CVX', name: 'Chevron Corp', sector: 'Energy' },
  { symbol: 'COP', name: 'ConocoPhillips', sector: 'Energy' },
  { symbol: 'EOG', name: 'EOG Resources', sector: 'Energy' },
  { symbol: 'SLB', name: 'SLB (Schlumberger)', sector: 'Energy' },
  { symbol: 'PSX', name: 'Phillips 66', sector: 'Energy' },
  { symbol: 'MPC', name: 'Marathon Petroleum', sector: 'Energy' },
  { symbol: 'VLO', name: 'Valero Energy', sector: 'Energy' },
  { symbol: 'OXY', name: 'Occidental Petroleum', sector: 'Energy' },
  { symbol: 'HAL', name: 'Halliburton Co', sector: 'Energy' },
  { symbol: 'JNJ', name: 'Johnson & Johnson', sector: 'Healthcare' },
  { symbol: 'UNH', name: 'UnitedHealth Group', sector: 'Healthcare' },
  { symbol: 'PFE', name: 'Pfizer Inc', sector: 'Healthcare' },
  { symbol: 'ABBV', name: 'AbbVie Inc', sector: 'Healthcare' },
  { symbol: 'MRK', name: 'Merck & Co', sector: 'Healthcare' },
  { symbol: 'TMO', name: 'Thermo Fisher Scientific', sector: 'Healthcare' },
  { symbol: 'ABT', name: 'Abbott Laboratories', sector: 'Healthcare' },
  { symbol: 'DHR', name: 'Danaher Corp', sector: 'Healthcare' },
  { symbol: 'BMY', name: 'Bristol-Myers Squibb', sector: 'Healthcare' },
  { symbol: 'AMGN', name: 'Amgen Inc', sector: 'Healthcare' },
  { symbol: 'HD', name: 'Home Depot', sector: 'Consumer Discretionary' },
  { symbol: 'MCD', name: "McDonald's Corp", sector: 'Consumer Discretionary' },
  { symbol: 'NKE', name: 'Nike Inc', sector: 'Consumer Discretionary' },
  { symbol: 'SBUX', name: 'Starbucks Corp', sector: 'Consumer Discretionary' },
  { symbol: 'TGT', name: 'Target Corp', sector: 'Consumer Discretionary' },
  { symbol: 'LOW', name: "Lowe's Companies", sector: 'Consumer Discretionary' },
  { symbol: 'TJX', name: 'TJX Companies', sector: 'Consumer Discretionary' },
  { symbol: 'BKNG', name: 'Booking Holdings', sector: 'Consumer Discretionary' },
  { symbol: 'MAR', name: 'Marriott International', sector: 'Consumer Discretionary' },
  { symbol: 'COST', name: 'Costco Wholesale', sector: 'Consumer Discretionary' },
]

function fmt(n, d = 2) {
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })
}

function markerColor(index) {
  const colors = ['#1f8f54', '#2a63f6', '#f4c62a', '#d14f59', '#7a5cff']
  return colors[index % colors.length]
}

function TickerInput({ value, onChange, widthClass = 'w-full' }) {
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(0)
  const containerRef = useRef(null)

  const suggestions =
    value.trim().length === 0
      ? []
      : TICKERS.filter(
          (ticker) =>
            ticker.symbol.startsWith(value.toUpperCase()) ||
            ticker.name.toLowerCase().includes(value.toLowerCase()),
        ).slice(0, 8)

  useEffect(() => {
    setHighlighted(0)
  }, [value])

  useEffect(() => {
    function handler(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function selectTicker(ticker) {
    onChange(ticker.symbol)
    setOpen(false)
  }

  function handleKey(event) {
    if (!open || !suggestions.length) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setHighlighted((current) => Math.min(current + 1, suggestions.length - 1))
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlighted((current) => Math.max(current - 1, 0))
    }
    if (event.key === 'Enter') {
      event.preventDefault()
      selectTicker(suggestions[highlighted])
    }
    if (event.key === 'Escape') setOpen(false)
  }

  return (
    <div ref={containerRef} className={`relative ${widthClass}`}>
      <input
        className="terminal-input"
        placeholder="Ticker or name"
        value={value}
        onChange={(event) => {
          onChange(event.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKey}
        autoComplete="off"
      />
      {open && suggestions.length > 0 && (
        <ul className="absolute left-0 top-full z-50 mt-1 w-full overflow-hidden border-2 border-[#14181c] bg-white shadow-[4px_4px_0_rgba(20,24,28,0.95)]">
          {suggestions.map((ticker, index) => (
            <li
              key={ticker.symbol}
              onMouseDown={() => selectTicker(ticker)}
              onMouseEnter={() => setHighlighted(index)}
              className="flex cursor-pointer items-center gap-3 px-4 py-3 text-sm"
              style={{ backgroundColor: index === highlighted ? '#f0f4f6' : '#ffffff' }}
            >
              <span className="min-w-[56px] text-[11px] font-bold uppercase tracking-[0.18em] text-slate-700">
                {ticker.symbol}
              </span>
              <span className="flex-1 truncate text-slate-700">{ticker.name}</span>
              <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">
                {ticker.sector.split(' ')[0]}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const FALLBACK_POINTS = {
  SPY: [38, 40, 42, 41, 43, 45, 46, 48],
  VTI: [36, 37, 39, 40, 41, 42, 44, 45],
  Technology: [28, 34, 30, 42, 39, 48, 44, 56],
  Financials: [24, 26, 31, 32, 36, 35, 39, 42],
  Energy: [44, 46, 39, 37, 41, 32, 28, 31],
  Healthcare: [26, 29, 35, 33, 38, 42, 40, 44],
  'Consumer Discretionary': [22, 27, 25, 34, 30, 37, 35, 40],
}

function LineStrip({ points, up }) {
  const max = Math.max(...points)
  const min = Math.min(...points)
  const coords = points.map((value, index) => {
    const x = (index / (points.length - 1)) * 100
    const y = 40 - ((value - min) / (max - min || 1)) * 30
    return `${x},${y}`
  })

  return (
    <svg viewBox="0 0 100 40" className="h-16 w-full">
      <polyline
        fill="none"
        stroke={up ? '#74c9af' : '#d17b73'}
        strokeWidth="1.6"
        points={coords.join(' ')}
      />
    </svg>
  )
}

function SectorMatrixChart({ sectors }) {
  const chartWidth = 640
  const chartHeight = 300
  const padding = { top: 26, right: 26, bottom: 58, left: 44 }
  const innerWidth = chartWidth - padding.left - padding.right
  const innerHeight = chartHeight - padding.top - padding.bottom
  const baselineY = padding.top + innerHeight / 2
  const maxAbsChange = Math.max(
    1,
    ...sectors.map((sector) => Math.abs(Number(sector.avg_pct_change) || 0)),
  )
  const stepX = sectors.length > 1 ? innerWidth / (sectors.length - 1) : innerWidth

  const rsiPoints = sectors
    .map((sector, index) => {
      const x = padding.left + stepX * index
      const rsi = Number(sector.avg_rsi) || 0
      const y = padding.top + innerHeight - (rsi / 100) * innerHeight
      return `${x},${y}`
    })
    .join(' ')

  return (
    <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="h-full w-full">
      <line
        x1={padding.left}
        y1={baselineY}
        x2={chartWidth - padding.right}
        y2={baselineY}
        stroke="#d6dee2"
        strokeWidth="1"
      />
      {[0.25, 0.75].map((fraction) => {
        const y = padding.top + innerHeight * fraction
        return (
          <line
            key={fraction}
            x1={padding.left}
            y1={y}
            x2={chartWidth - padding.right}
            y2={y}
            stroke="#edf2f4"
            strokeWidth="1"
          />
        )
      })}

      {sectors.map((sector, index) => {
        const x = padding.left + stepX * index
        const change = Number(sector.avg_pct_change) || 0
        const barHeight = (Math.abs(change) / maxAbsChange) * (innerHeight / 2 - 12)
        const y = change >= 0 ? baselineY - barHeight : baselineY
        return (
          <g key={sector.sector}>
            <rect
              x={x - 32}
              y={y}
              width="64"
              height={Math.max(barHeight, 2)}
              rx="8"
              fill={change >= 0 ? '#8bd0b8' : '#df9084'}
              opacity="0.9"
            />
            <text
              x={x}
              y={chartHeight - 18}
              textAnchor="middle"
              fontSize="10"
              fontWeight="700"
              letterSpacing="0.18em"
              fill="#7d8b93"
            >
              {sector.sector.replace('Consumer Discretionary', 'Consumer')}
            </text>
            <text
              x={x}
              y={change >= 0 ? y - 8 : y + Math.max(barHeight, 2) + 14}
              textAnchor="middle"
              fontSize="11"
              fontWeight="700"
              fill={change >= 0 ? '#4f9f85' : '#c76d63'}
            >
              {`${change >= 0 ? '+' : ''}${fmt(change)}%`}
            </text>
          </g>
        )
      })}

      <polyline
        fill="none"
        stroke="#6b7f8b"
        strokeWidth="2.5"
        points={rsiPoints}
      />
      {sectors.map((sector, index) => {
        const x = padding.left + stepX * index
        const rsi = Number(sector.avg_rsi) || 0
        const y = padding.top + innerHeight - (rsi / 100) * innerHeight
        return (
          <g key={`${sector.sector}-rsi`}>
            <circle cx={x} cy={y} r="4.5" fill="#102445" />
            <circle cx={x} cy={y} r="2" fill="#f8fafb" />
          </g>
        )
      })}
    </svg>
  )
}

export default function Dashboard({ onSearch = () => {}, onOpenNews = () => {} }) {
  const { getToken, authEnabled, isSignedIn } = useFinsightAuth()
  const watchlistLocked = authEnabled && !isSignedIn
  const [data, setData] = useState(null)
  const [snapshot, setSnapshot] = useState(null)
  const [news, setNews] = useState(null)
  const [watchlistData, setWatchlistData] = useState({ watchlist: [], snapshot: null })
  const [watchlistEditing, setWatchlistEditing] = useState(false)
  const [watchlistDraft, setWatchlistDraft] = useState('')
  const [watchlistBusy, setWatchlistBusy] = useState(false)
  const [tab, setTab] = useState('gainers')

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [anomaliesRes, snapshotRes, newsRes, watchlistRes] = await Promise.all([
          authedFetch(getToken, '/anomalies', { cache: 'no-store' }),
          authedFetch(getToken, '/market-snapshot', { cache: 'no-store' }),
          authedFetch(getToken, '/market-news', { cache: 'no-store' }),
          authedFetch(getToken, '/portfolio/watchlist', { cache: 'no-store' }),
        ])

        const anomaliesJson = await anomaliesRes.json()
        const snapshotJson = await snapshotRes.json()
        const newsJson = await newsRes.json()
        const watchlistJson = await watchlistRes.json()
        setData(anomaliesJson)
        setSnapshot(snapshotJson)
        setNews(newsJson)
        setWatchlistData(watchlistJson)
      } catch {
        setData({ date: null, anomalies: [] })
        setSnapshot(null)
        setNews({ stories: [] })
        setWatchlistData({ watchlist: [], snapshot: null })
      }
    }

    loadDashboard()

    function reloadOnFocus() {
      loadDashboard()
    }

    window.addEventListener('focus', reloadOnFocus)
    document.addEventListener('visibilitychange', reloadOnFocus)

    return () => {
      window.removeEventListener('focus', reloadOnFocus)
      document.removeEventListener('visibilitychange', reloadOnFocus)
    }
  }, [])

  const signals = data?.anomalies || []
  const movers = useMemo(() => {
    const sorted = [...signals].sort((a, b) => b.pct_change - a.pct_change)
    if (tab === 'losers') return sorted.reverse().slice(0, 5)
    return sorted.slice(0, 5)
  }, [signals, tab])

  const notes = signals.slice(0, 3).map((signal, index) => {
    const summaries = [
      `Tech sector divergence noted. ${signal.symbol} showing unusual activity into the close.`,
      `${signal.symbol} printed a notable momentum signature with RSI at ${signal.rsi_14?.toFixed(1) || 'n/a'}.`,
      `${signal.symbol} remains one of the most interesting outliers in ${signal.sector}.`,
    ]
    return summaries[index] || summaries[2]
  })

  const sectorCards = snapshot?.sector_cards?.length
    ? snapshot.sector_cards.slice(0, 3).map((card) => ({
        label: card.sector,
        value: `${card.avg_rsi?.toFixed?.(1) ?? '0.0'} RSI`,
        chg: `${card.avg_pct_change >= 0 ? '+' : ''}${fmt(card.avg_pct_change)}%`,
        up: card.avg_pct_change >= 0,
        points: FALLBACK_POINTS[card.sector] || FALLBACK_POINTS.Technology,
        meta: `${card.ticker_count} tickers`,
      }))
    : [
        { label: 'Technology', value: '0.0 RSI', chg: '0.00%', up: true, points: FALLBACK_POINTS.Technology, meta: '0 tickers' },
        { label: 'Financials', value: '0.0 RSI', chg: '0.00%', up: true, points: FALLBACK_POINTS.Financials, meta: '0 tickers' },
        { label: 'Energy', value: '0.0 RSI', chg: '0.00%', up: false, points: FALLBACK_POINTS.Energy, meta: '0 tickers' },
      ]

  const benchmarkCards = snapshot?.benchmarks?.length
    ? snapshot.benchmarks.map((card) => ({
        label: card.symbol,
        sublabel: card.label,
        value: fmt(card.close),
        chg: `${card.pct_change >= 0 ? '+' : ''}${fmt(card.pct_change)}%`,
        up: card.pct_change >= 0,
        points: FALLBACK_POINTS[card.symbol] || FALLBACK_POINTS.SPY,
        meta: card.date,
        source: card.source || 'unknown',
      }))
    : [
        { label: 'SPY', sublabel: 'S&P 500', value: '--', chg: '0.00%', up: true, points: FALLBACK_POINTS.SPY, meta: 'waiting for quote', source: 'unknown' },
        { label: 'VTI', sublabel: 'Vanguard Total Market', value: '--', chg: '0.00%', up: true, points: FALLBACK_POINTS.VTI, meta: 'waiting for quote', source: 'unknown' },
      ]

  const benchmarkSource = benchmarkCards.every((card) => card.source === 'yfinance')
    ? { title: 'Live benchmark', subtitle: 'Yahoo Finance ETF snapshot' }
    : benchmarkCards.every((card) => card.source === 'twelve_data' || card.source === 'yfinance')
      ? { title: 'Live benchmark', subtitle: 'Real-time ETF snapshot' }
    : benchmarkCards.some((card) => card.source === 'warehouse_proxy')
      ? { title: 'Proxy benchmark', subtitle: 'Warehouse-derived ETF proxy' }
      : { title: 'Benchmarks', subtitle: 'Benchmark data' }

  const faangCards = snapshot?.faang?.length
    ? snapshot.faang.map((card) => ({
        symbol: card.symbol,
        company_name: card.company_name,
        close: card.close,
        pct_change: card.pct_change,
        sector: 'Mega-cap tech',
        points: FALLBACK_POINTS[card.symbol] || FALLBACK_POINTS.SPY,
      }))
    : [
        { symbol: 'AAPL', company_name: 'Apple Inc', close: null, pct_change: 0, sector: 'Mega-cap tech', points: FALLBACK_POINTS.SPY },
        { symbol: 'AMZN', company_name: 'Amazon.com Inc', close: null, pct_change: 0, sector: 'Mega-cap tech', points: FALLBACK_POINTS.SPY },
        { symbol: 'GOOGL', company_name: 'Alphabet Inc', close: null, pct_change: 0, sector: 'Mega-cap tech', points: FALLBACK_POINTS.SPY },
        { symbol: 'META', company_name: 'Meta Platforms Inc', close: null, pct_change: 0, sector: 'Mega-cap tech', points: FALLBACK_POINTS.SPY },
      ]

  const footerLeaders = snapshot?.leaders?.length ? snapshot.leaders : []
  const matrixSectors = snapshot?.sector_cards?.length ? snapshot.sector_cards : []
  const peakSector = matrixSectors.length
    ? [...matrixSectors].sort((a, b) => (Number(b.avg_rsi) || 0) - (Number(a.avg_rsi) || 0))[0]
    : null
  const stories = (news?.stories || []).slice(0, 3)
  const watchlistCards = watchlistData?.snapshot?.items?.length
    ? watchlistData.snapshot.items.map((item) => ({
        symbol: item.symbol,
        company_name: item.company_name,
        close: item.current_price,
        pct_change: item.daily_pct_change,
        sector: item.sector,
        points: item.trend_points?.length ? item.trend_points : FALLBACK_POINTS[item.symbol] || FALLBACK_POINTS.SPY,
      }))
    : faangCards

  async function refreshWatchlist() {
    const response = await authedFetch(getToken, '/portfolio/watchlist', { cache: 'no-store' })
    if (!response.ok) throw new Error('Unable to refresh watchlist')
    const payload = await response.json()
    setWatchlistData(payload)
  }

  async function addWatchlistSymbol() {
    const symbol = watchlistDraft.trim().toUpperCase()
    if (!symbol) return
    setWatchlistBusy(true)
    try {
      const response = await authedFetch(getToken, '/portfolio/watchlist', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol }),
      })
      if (!response.ok) throw new Error('Unable to add symbol')
      setWatchlistDraft('')
      await refreshWatchlist()
    } finally {
      setWatchlistBusy(false)
    }
  }

  async function removeWatchlistSymbol(symbol) {
    setWatchlistBusy(true)
    try {
      const response = await authedFetch(getToken, `/portfolio/watchlist/${symbol}`, { method: 'DELETE' })
      if (!response.ok) throw new Error('Unable to remove symbol')
      await refreshWatchlist()
    } finally {
      setWatchlistBusy(false)
    }
  }

  return (
    <div className="bg-background px-3 py-5 sm:px-5 sm:py-7 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-[1520px]">
        <div className="mb-10 grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="terminal-panel px-6 py-6 sm:px-8 sm:py-8">
            <p className="terminal-label text-outline">Terminal session 04.22.2026 // Status: active</p>
            <h1 className="mt-4 font-headline text-4xl font-extrabold uppercase tracking-tight text-slate-900 sm:text-[4rem]">
              Market Overview
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-8 text-slate-500">
              {snapshot?.date
                ? `Live benchmarks, warehouse context, and the strongest active signals as of ${snapshot.date}.`
                : 'Loading live market snapshot...'}
            </p>
          </div>
          <div className="terminal-panel px-6 py-6">
            <p className="terminal-label text-outline">Analyst Terminal</p>
            <p className="mt-3 text-sm leading-7 text-slate-500">
              Jump straight into analyst mode for a live quote, momentum screen, or a specific symbol.
            </p>
            <div className="mt-5 space-y-3">
              <button
                type="button"
                onClick={() => onSearch('NVDA price')}
                className="flex w-full items-center justify-between border-2 border-[#14181c] bg-white px-4 py-3 text-left transition-colors hover:bg-surface-container-low"
              >
                <div>
                  <p className="text-sm font-semibold text-slate-900">Latest NVDA quote</p>
                  <p className="terminal-label text-outline">Live quote</p>
                </div>
                <span className="material-symbols-outlined text-slate-500">arrow_outward</span>
              </button>
              <button
                type="button"
                onClick={() => onSearch('Which tech stocks had the highest RSI last week?')}
                className="flex w-full items-center justify-between border-2 border-[#14181c] bg-white px-4 py-3 text-left transition-colors hover:bg-surface-container-low"
              >
                <div>
                  <p className="text-sm font-semibold text-slate-900">Momentum screen</p>
                  <p className="terminal-label text-outline">Technical screen</p>
                </div>
                <span className="material-symbols-outlined text-slate-500">arrow_outward</span>
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <div className="col-span-12 space-y-8 lg:col-span-8">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {benchmarkCards.map((index, cardIndex) => (
                <div
                  key={index.label}
                  className={`terminal-panel px-5 py-5 ${
                    cardIndex === 0
                      ? 'terminal-card-accent-green'
                      : cardIndex === 1
                        ? 'terminal-card-accent-blue'
                        : cardIndex === 2
                          ? 'terminal-card-accent-red'
                          : 'terminal-card-accent-yellow'
                  }`}
                >
                  <p className="terminal-label text-outline">{index.sublabel}</p>
                  <div className="mt-3 flex items-end justify-between gap-3">
                    <p className="font-headline text-3xl font-bold text-slate-900">{index.value}</p>
                    <span className="text-sm font-semibold" style={{ color: index.up ? '#1c6b51' : '#b12d2a' }}>
                      {index.chg}
                    </span>
                  </div>
                  <p className="mt-2 terminal-label text-outline">{index.label} • {index.source === 'warehouse_proxy' ? 'Proxy' : 'Live'}</p>
                </div>
              ))}
            </div>

            <div>
              <div className="mb-4 flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
                <h2 className="font-headline text-2xl font-bold text-slate-900">Watchlist</h2>
                {watchlistLocked ? (
                  <SignInButton mode="modal">
                    <button className="terminal-button px-4 py-2">
                      Sign In
                    </button>
                  </SignInButton>
                ) : (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setWatchlistEditing((current) => !current)}
                      className="terminal-button terminal-button-secondary px-4 py-2"
                    >
                      {watchlistEditing ? 'Done' : 'Edit List'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setWatchlistEditing(true)}
                      className="terminal-button px-4 py-2"
                    >
                      Add Symbol
                    </button>
                  </div>
                )}
              </div>

              <div className="terminal-panel overflow-hidden">
                <div className="hidden grid-cols-12 gap-4 bg-surface-container-low px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-outline md:grid">
                  <div className="col-span-5">Asset &amp; symbol</div>
                  <div className="col-span-2 text-right">Last price</div>
                  <div className="col-span-2 text-right">24h change</div>
                  <div className="col-span-3 text-center">Trend</div>
                </div>
                {watchlistLocked && (
                  <div className="border-b border-surface-container px-6 py-4 text-sm text-slate-500">
                    Sign in to edit your personal watchlist. Public visitors can still browse the live market snapshot.
                  </div>
                )}
                {!watchlistLocked && watchlistEditing && (
                  <div className="border-b border-surface-container px-6 py-4">
                    <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
                      <TickerInput
                        value={watchlistDraft}
                        onChange={setWatchlistDraft}
                        widthClass="flex-1"
                      />
                      <button
                        type="button"
                        disabled={watchlistBusy || !watchlistDraft.trim()}
                        onClick={addWatchlistSymbol}
                        className="terminal-button px-4 py-3 disabled:opacity-50"
                      >
                        Add
                      </button>
                    </div>
                  </div>
                )}
                <div className="divide-y divide-surface-container">
                  {watchlistCards.map((signal) => (
                    <div
                      key={signal.symbol}
                      className="grid grid-cols-1 gap-4 px-6 py-5 text-left transition-colors hover:bg-surface-container-low/40 md:grid-cols-12"
                    >
                      <div className="md:col-span-5">
                        <p className="font-semibold text-slate-900">{signal.company_name}</p>
                        <p className="text-xs text-slate-500">Mega-cap tech • {signal.symbol}</p>
                      </div>
                      <div className="flex items-center justify-between font-semibold text-slate-900 md:col-span-2 md:block md:text-right">
                        <span className="terminal-label text-outline md:hidden">Last price</span>
                        <span>{signal.close != null ? `$${fmt(signal.close)}` : '--'}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm font-medium md:col-span-2 md:block md:text-right" style={{ color: signal.pct_change >= 0 ? '#1c6b51' : '#b12d2a' }}>
                        <span className="terminal-label text-outline md:hidden">24h change</span>
                        <span>{signal.pct_change >= 0 ? '+' : ''}{signal.pct_change?.toFixed?.(2) ?? signal.pct_change}%</span>
                      </div>
                      <div className="flex items-center justify-between md:col-span-3 md:justify-center">
                        <span className="terminal-label text-outline md:hidden">Trend</span>
                        <div className="flex items-center gap-3">
                          <div className="w-24">
                            <LineStrip points={signal.points || FALLBACK_POINTS[signal.symbol] || FALLBACK_POINTS.SPY} up={signal.pct_change >= 0} />
                          </div>
                          <span
                            className="terminal-mini-bar w-8"
                            style={{ backgroundColor: markerColor(watchlistCards.findIndex((card) => card.symbol === signal.symbol)) }}
                          />
                        </div>
                      </div>
                      {!watchlistLocked && watchlistEditing && (
                        <div className="col-span-12 flex justify-end pt-1">
                          <button
                            type="button"
                            disabled={watchlistBusy}
                            onClick={() => removeWatchlistSymbol(signal.symbol)}
                            className="material-symbols-outlined text-slate-400 transition-colors hover:text-[#c76d63] disabled:opacity-50"
                          >
                            close
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {sectorCards.map((index) => (
                <div
                  key={index.label}
                  className={`terminal-panel px-5 py-5 ${
                    index.up ? 'terminal-card-accent-green' : 'terminal-card-accent-red'
                  }`}
                >
                  <p className="terminal-label text-outline">{index.label}</p>
                  <p className="mt-3 font-headline text-4xl font-bold text-slate-900">{index.value}</p>
                  <p className="mt-3 text-sm font-semibold" style={{ color: index.up ? '#4f9f85' : '#c76d63' }}>
                    {index.chg}
                  </p>
                  <p className="mt-1 terminal-label text-outline">{index.meta}</p>
                  <div className="mt-3">
                    <LineStrip points={index.points} up={index.up} />
                  </div>
                </div>
              ))}
            </div>

            <div className="terminal-panel p-6 sm:p-8">
              <div className="mb-8 flex flex-col items-start justify-between gap-6 lg:flex-row">
                <div>
                  <h2 className="font-headline text-2xl font-bold text-slate-900">Aggregated Volatility Matrix</h2>
                  <p className="mt-2 text-sm text-slate-500">
                    Real sector move bars with an RSI overlay from the latest warehouse trading date.
                  </p>
                </div>
                <div className="flex items-center gap-5 text-xs text-slate-500">
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#8bd0b8]" />
                    <span>Avg % change</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="h-0.5 w-5 bg-[#6b7f8b]" />
                    <span>Avg RSI</span>
                  </div>
                </div>
              </div>

              <div className="relative overflow-x-auto bg-surface-container-low">
                {matrixSectors.length ? (
                  <div className="min-w-[640px]">
                    <SectorMatrixChart sectors={matrixSectors} />
                  </div>
                ) : (
                  <div className="flex h-[360px] items-center justify-center text-sm text-slate-500">
                    Sector data unavailable.
                  </div>
                )}
                    <div className="terminal-panel absolute right-4 top-4 px-4 py-3 sm:right-14 sm:top-16 sm:px-5 sm:py-4">
                  <p className="terminal-label text-outline">Highest RSI</p>
                  <p className="mt-2 font-headline text-3xl font-bold text-slate-900">
                    {peakSector ? `${fmt(peakSector.avg_rsi)} RSI` : '...'}
                  </p>
                  <p className="mt-2 terminal-label text-outline">
                    {peakSector ? peakSector.sector : 'No sector data'}
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {(footerLeaders.length ? footerLeaders : [
                { symbol: 'AAPL', company_name: 'No data', pct_change: 0 },
                { symbol: 'NVDA', company_name: 'No data', pct_change: 0 },
                { symbol: 'TSLA', company_name: 'No data', pct_change: 0 },
                { symbol: 'MSFT', company_name: 'No data', pct_change: 0 },
              ]).map((signal) => (
                <button
                  key={signal.symbol}
                  onClick={() => onSearch(`${signal.symbol} price`)}
                  className="terminal-panel px-5 py-5 text-left transition-colors hover:bg-white"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-headline text-lg font-bold text-slate-900">{signal.symbol}</p>
                    <span
                      className="text-sm font-semibold"
                      style={{ color: signal.pct_change >= 0 ? '#4f9f85' : '#c76d63' }}
                    >
                      {signal.pct_change >= 0 ? '+' : ''}
                      {signal.pct_change?.toFixed?.(1) ?? signal.pct_change}%
                    </span>
                  </div>
                  <p className="mt-4 terminal-label text-outline">{signal.company_name}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="col-span-12 space-y-6 lg:col-span-4">
            <div className="terminal-panel p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="terminal-label text-outline">Analyst Terminal</p>
                  <h2 className="mt-3 font-headline text-3xl font-bold uppercase text-slate-900">Quick Actions</h2>
                </div>
                <span className="material-symbols-outlined text-[#2a63f6]">travel_explore</span>
              </div>
              <div className="mt-5 space-y-3">
                <button
                  type="button"
                  onClick={() => onSearch('AAPL fundamentals')}
                  className="flex w-full items-center justify-between border-2 border-[#14181c] bg-white px-4 py-3 text-left text-sm font-semibold uppercase tracking-[0.14em] text-slate-900 transition-colors hover:bg-surface-container-low"
                >
                  <span>Fundamentals</span>
                  <span className="material-symbols-outlined text-[18px] text-[#2a63f6]">arrow_outward</span>
                </button>
                <button
                  type="button"
                  onClick={() => onSearch('NVDA technical analysis')}
                  className="flex w-full items-center justify-between border-2 border-[#14181c] bg-white px-4 py-3 text-left text-sm font-semibold uppercase tracking-[0.14em] text-slate-900 transition-colors hover:bg-surface-container-low"
                >
                  <span>Technicals</span>
                  <span className="material-symbols-outlined text-[18px] text-[#f4c62a]">monitoring</span>
                </button>
                <button
                  type="button"
                  onClick={() => onSearch('latest sec filings for TSLA')}
                  className="flex w-full items-center justify-between border-2 border-[#14181c] bg-white px-4 py-3 text-left text-sm font-semibold uppercase tracking-[0.14em] text-slate-900 transition-colors hover:bg-surface-container-low"
                >
                  <span>SEC Filings</span>
                  <span className="material-symbols-outlined text-[18px] text-[#d14f59]">receipt_long</span>
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <h2 className="font-headline text-2xl font-bold text-slate-900">Market News</h2>
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#1b55e2] text-[10px] font-bold text-white">
                {stories.length}
              </span>
            </div>

            <div className="space-y-4">
              {stories.map((story, index) => (
                <button
                  key={story.id || `${story.symbol}-${index}`}
                  type="button"
                  onClick={() => onOpenNews(story)}
                  className="terminal-panel block w-full p-5 text-left transition-colors hover:bg-white"
                  style={{ borderLeft: `4px solid ${index === 0 ? '#4f9f85' : '#545e76'}` }}
                >
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <span
                      className="rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-white"
                      style={{ backgroundColor: index === 0 ? '#1f8f54' : index === 1 ? '#2a63f6' : '#d14f59' }}
                    >
                      Market news
                    </span>
                    <span className="text-[10px] font-medium text-outline">{story.symbol}</span>
                  </div>
                  <p className="text-sm font-semibold leading-6 text-slate-900">{story.title}</p>
                  <p className="mt-2 text-xs leading-6 text-slate-500">
                    {story.summary || `${story.symbol} has a fresh company update in the feed.`}
                  </p>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="terminal-label text-outline">{story.source || 'News feed'}</span>
                    <span className="terminal-label text-outline">
                      {story.datetime ? new Date(story.datetime).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Latest'}
                    </span>
                  </div>
                </button>
              ))}

              {!stories.length && (
                <div className="terminal-panel p-5">
                  <p className="text-sm font-semibold text-slate-900">No news available.</p>
                  <p className="mt-2 text-xs leading-6 text-slate-500">
                    Current market news from major names will appear here when available.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
