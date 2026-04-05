import { useEffect, useRef, useState } from 'react'
import { SignInButton, SignUpButton } from '@clerk/react'
import CompanyLogo from '../components/CompanyLogo'
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

const SECTOR_COLORS = ['#7dbda7', '#b5a8d6', '#d8a07a', '#9eb7cb', '#c7b48a', '#d68585']
const EMPTY_FORM = { symbol: '', shares: '', avg_cost: '' }
const EMPTY_WATCHLIST_FORM = { symbol: '' }
const EMPTY_NOTE_FORM = { symbol: '', note_type: 'thesis', note_title: '', review_date: '', note_text: '' }
const DEFAULT_PREFERENCES = {
  concentration_alerts_enabled: true,
  concentration_threshold_pct: 35,
  rsi_alerts_enabled: true,
  overbought_rsi_threshold: 70,
  oversold_rsi_threshold: 30,
  daily_move_alerts_enabled: true,
  daily_move_threshold_pct: 5,
  telegram_daily_brief_enabled: true,
  telegram_alerts_enabled: true,
}
const NOTE_TYPE_LABELS = {
  thesis: 'Thesis',
  risk: 'Risk Rule',
  exit: 'Exit Trigger',
  review: 'Review Note',
  note: 'General Note',
}
const NOTE_LANE_ORDER = ['thesis', 'risk', 'review', 'exit', 'note']

function fmt(n, d = 2) {
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })
}

function TickerInput({ value, onChange, placeholder = 'Ticker or name', inputClassName = 'w-full border border-outline/20 bg-white px-3 py-3 text-sm text-slate-700 focus:outline-none sm:w-48' }) {
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
    if (event.key === 'Enter') {
      event.preventDefault()
      event.stopPropagation()
      if (open && suggestions.length) {
        selectTicker(suggestions[highlighted])
      }
      return
    }

    if (!open || !suggestions.length) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      event.stopPropagation()
      setHighlighted((current) => Math.min(current + 1, suggestions.length - 1))
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      event.stopPropagation()
      setHighlighted((current) => Math.max(current - 1, 0))
    }
    if (event.key === 'Escape') {
      event.stopPropagation()
      setOpen(false)
    }
  }

  return (
    <div ref={containerRef} className="relative w-full sm:w-auto">
      <input
        className={inputClassName}
        placeholder={placeholder}
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
        <ul className="absolute left-0 top-full z-50 mt-1 w-full overflow-hidden border border-outline/15 bg-white shadow-[0_12px_30px_rgba(148,163,184,0.18)] sm:w-80">
          {suggestions.map((ticker, index) => (
            <li key={ticker.symbol}>
              <button
                type="button"
                onMouseDown={(event) => {
                  event.preventDefault()
                  event.stopPropagation()
                }}
                onClick={(event) => {
                  event.preventDefault()
                  event.stopPropagation()
                  selectTicker(ticker)
                }}
                onMouseEnter={() => setHighlighted(index)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm"
                style={{ backgroundColor: index === highlighted ? '#f0f4f6' : '#ffffff' }}
              >
                <span className="terminal-label min-w-[56px] text-slate-700">{ticker.symbol}</span>
                <span className="flex-1 truncate text-slate-700">{ticker.name}</span>
                <span className="terminal-label text-outline">{ticker.sector.split(' ')[0]}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function SectorDonut({ sectors }) {
  if (!sectors?.length) return null
  const circumference = 2 * Math.PI * 16
  let cumulative = 0

  return (
    <svg className="h-full w-full -rotate-90" viewBox="0 0 36 36">
      <circle cx="18" cy="18" r="16" fill="none" stroke="#e2e8ec" strokeWidth="3.5" />
      {sectors.map((sector, index) => {
        const dash = (sector.pct / 100) * circumference
        const offset = -cumulative
        cumulative += dash
        return (
          <circle
            key={sector.sector}
            cx="18"
            cy="18"
            r="16"
            fill="none"
            stroke={SECTOR_COLORS[index % SECTOR_COLORS.length]}
            strokeDasharray={`${dash} ${circumference}`}
            strokeDashoffset={offset}
            strokeWidth="3.5"
          />
        )
      })}
    </svg>
  )
}

function insightTone(value) {
  return value >= 0 ? '#4f9f85' : '#c76d63'
}

function alertAccent(alert) {
  if (alert.alert_type?.includes('oversold')) return '#545e76'
  if (alert.severity === 'high') return '#b12d2a'
  if (alert.alert_type?.includes('overbought')) return '#1c6b51'
  return '#545e76'
}

function WatchlistSparkline({ points = [], up = true }) {
  if (!points.length) {
    return <div className="h-10 w-24 rounded-md bg-surface-container-low" />
  }

  const max = Math.max(...points)
  const min = Math.min(...points)
  const coords = points.map((value, index) => {
    const x = (index / Math.max(points.length - 1, 1)) * 100
    const y = 36 - ((value - min) / (max - min || 1)) * 24
    return `${x},${y}`
  })

  return (
    <svg viewBox="0 0 100 40" className="h-10 w-24">
      <polyline
        fill="none"
        stroke="#e2e8ec"
        strokeWidth="1.25"
        points="0,34 100,34"
      />
      <polyline
        fill="none"
        stroke={up ? '#74c9af' : '#d17b73'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={coords.join(' ')}
      />
    </svg>
  )
}

function noteAccent(noteType) {
  switch (noteType) {
    case 'thesis':
      return '#54f06a'
    case 'risk':
      return '#f4c62a'
    case 'exit':
      return '#7a8cff'
    case 'review':
      return '#2a63f6'
    default:
      return '#9ea8b6'
  }
}

function noteUrgency(title) {
  const normalized = (title || '').trim().toLowerCase()
  if (!normalized) return null
  if (/^(p0|p1|urgent|now)\b/.test(normalized)) return { label: 'High urgency', color: '#7a8cff' }
  if (/^(p2|next|soon)\b/.test(normalized)) return { label: 'Medium urgency', color: '#f4c62a' }
  if (/^(p3|p4|later|backlog)\b/.test(normalized)) return { label: 'Low urgency', color: '#54f06a' }
  return null
}

export default function Portfolio() {
  const { getToken, authEnabled, isSignedIn } = useFinsightAuth()
  const portfolioLocked = authEnabled && !isSignedIn
  const hasLoadedPortfolioRef = useRef(false)
  const clearLockedStateTimerRef = useRef(null)
  const [holdings, setHoldings] = useState([])
  const [form, setForm] = useState(EMPTY_FORM)
  const [watchlistForm, setWatchlistForm] = useState(EMPTY_WATCHLIST_FORM)
  const [noteForm, setNoteForm] = useState(EMPTY_NOTE_FORM)
  const [result, setResult] = useState(null)
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES)
  const [watchlist, setWatchlist] = useState([])
  const [watchlistSnapshot, setWatchlistSnapshot] = useState(null)
  const [notes, setNotes] = useState([])
  const [alerts, setAlerts] = useState({ portfolio: [], watchlist: [] })
  const [loading, setLoading] = useState(false)
  const [savingPreferences, setSavingPreferences] = useState(false)
  const [preferencesOpen, setPreferencesOpen] = useState(false)
  const [telegramLink, setTelegramLink] = useState({ linked: false, pending_code: null })
  const [telegramBusy, setTelegramBusy] = useState(false)
  const [draggedNoteId, setDraggedNoteId] = useState(null)
  const [dragOverLane, setDragOverLane] = useState(null)
  const [error, setError] = useState(null)

  const notesByLane = NOTE_LANE_ORDER.reduce((accumulator, lane) => {
    accumulator[lane] = notes.filter((note) => (note.note_type || 'note') === lane)
    return accumulator
  }, {})

  useEffect(() => {
    if (portfolioLocked) {
      setLoading(false)
      setError(null)
      clearLockedStateTimerRef.current = window.setTimeout(() => {
        setHoldings([])
        setResult(null)
        setWatchlist([])
        setWatchlistSnapshot(null)
        setNotes([])
        setAlerts({ portfolio: [], watchlist: [] })
        setTelegramLink({ linked: false, pending_code: null })
        hasLoadedPortfolioRef.current = false
      }, 1500)
      return
    }

    if (clearLockedStateTimerRef.current) {
      window.clearTimeout(clearLockedStateTimerRef.current)
      clearLockedStateTimerRef.current = null
    }

    if (!hasLoadedPortfolioRef.current) {
      hasLoadedPortfolioRef.current = true
      loadPortfolio()
    }
    return () => {
      if (clearLockedStateTimerRef.current) {
        window.clearTimeout(clearLockedStateTimerRef.current)
        clearLockedStateTimerRef.current = null
      }
    }
  }, [portfolioLocked])

  useEffect(() => {
    function handleTelegramLinkUpdated(event) {
      setTelegramLink(event.detail || { linked: false, pending_code: null })
      setError(null)
    }

    function handleTelegramLinkError(event) {
      setError(event.detail || 'Unable to generate Telegram link code.')
    }

    function handleTelegramLinkBusy(event) {
      setTelegramBusy(Boolean(event.detail))
    }

    window.addEventListener('finsight:telegram-link-updated', handleTelegramLinkUpdated)
    window.addEventListener('finsight:telegram-link-error', handleTelegramLinkError)
    window.addEventListener('finsight:telegram-link-busy', handleTelegramLinkBusy)
    return () => {
      window.removeEventListener('finsight:telegram-link-updated', handleTelegramLinkUpdated)
      window.removeEventListener('finsight:telegram-link-error', handleTelegramLinkError)
      window.removeEventListener('finsight:telegram-link-busy', handleTelegramLinkBusy)
    }
  }, [])

  function applyAlertPayload(nextAlerts = []) {
    setAlerts({
      portfolio: nextAlerts.filter((alert) => (alert.source_scope || 'portfolio') === 'portfolio'),
      watchlist: nextAlerts.filter((alert) => alert.source_scope === 'watchlist'),
    })
  }

  async function loadPortfolio() {
    setLoading(true)
    setError(null)
    try {
      const requests = [
        authedFetch(getToken, '/portfolio/holdings'),
        authedFetch(getToken, '/portfolio'),
        authedFetch(getToken, '/portfolio/alert-preferences'),
        authedFetch(getToken, '/portfolio/watchlist'),
        authedFetch(getToken, '/portfolio/alerts'),
        authedFetch(getToken, '/notes'),
      ]
      if (authEnabled && isSignedIn) {
        requests.push(authedFetch(getToken, '/telegram/link'))
      }

      const [
        holdingsResponse,
        portfolioResponse,
        preferencesResponse,
        watchlistResponse,
        alertsResponse,
        notesResponse,
        telegramLinkResponse,
      ] = await Promise.all(requests)

      if (!holdingsResponse.ok) {
        const detail = await holdingsResponse.json().catch(() => ({ detail: holdingsResponse.statusText }))
        throw new Error(detail.detail || `HTTP ${holdingsResponse.status}`)
      }

      if (!portfolioResponse.ok) {
        const detail = await portfolioResponse.json().catch(() => ({ detail: portfolioResponse.statusText }))
        throw new Error(detail.detail || `HTTP ${portfolioResponse.status}`)
      }

      if (!preferencesResponse.ok) {
        const detail = await preferencesResponse.json().catch(() => ({ detail: preferencesResponse.statusText }))
        throw new Error(detail.detail || `HTTP ${preferencesResponse.status}`)
      }
      if (!watchlistResponse.ok) {
        const detail = await watchlistResponse.json().catch(() => ({ detail: watchlistResponse.statusText }))
        throw new Error(detail.detail || `HTTP ${watchlistResponse.status}`)
      }
      if (!alertsResponse.ok) {
        const detail = await alertsResponse.json().catch(() => ({ detail: alertsResponse.statusText }))
        throw new Error(detail.detail || `HTTP ${alertsResponse.status}`)
      }
      if (!notesResponse.ok) {
        const detail = await notesResponse.json().catch(() => ({ detail: notesResponse.statusText }))
        throw new Error(detail.detail || `HTTP ${notesResponse.status}`)
      }
      if (telegramLinkResponse && !telegramLinkResponse.ok) {
        const detail = await telegramLinkResponse.json().catch(() => ({ detail: telegramLinkResponse.statusText }))
        throw new Error(detail.detail || `HTTP ${telegramLinkResponse.status}`)
      }

      const holdingsJson = await holdingsResponse.json()
      const portfolioJson = await portfolioResponse.json()
      const preferencesJson = await preferencesResponse.json()
      const watchlistJson = await watchlistResponse.json()
      const alertsJson = await alertsResponse.json()
      const notesJson = await notesResponse.json()
      const telegramLinkJson = telegramLinkResponse ? await telegramLinkResponse.json() : { linked: false, pending_code: null }
      setHoldings(holdingsJson.holdings || [])
      setResult(portfolioJson)
      setPreferences({ ...DEFAULT_PREFERENCES, ...(preferencesJson || {}) })
      setWatchlist(watchlistJson.watchlist || [])
      setWatchlistSnapshot(watchlistJson.snapshot || null)
      setAlerts(alertsJson.grouped_alerts || { portfolio: [], watchlist: [] })
      setNotes(notesJson.notes || [])
      setTelegramLink(telegramLinkJson || { linked: false, pending_code: null })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function addHolding() {
    const symbol = form.symbol.trim().toUpperCase()
    const shares = parseFloat(form.shares)
    const avgCost = parseFloat(form.avg_cost)
    if (!symbol || Number.isNaN(shares) || Number.isNaN(avgCost) || shares <= 0 || avgCost <= 0) return
    setLoading(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, '/portfolio/holdings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, shares, avg_cost: avgCost }),
      })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(detail.detail || `HTTP ${response.status}`)
      }

      const payload = await response.json()
      setResult(payload.portfolio)
      setHoldings(payload.portfolio?.holdings || [])
      setForm(EMPTY_FORM)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function removeHolding(symbol) {
    setLoading(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, `/portfolio/holdings/${symbol}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(detail.detail || `HTTP ${response.status}`)
      }

      const payload = await response.json()
      setResult(payload.portfolio)
      setHoldings(payload.portfolio?.holdings || [])
      setAlerts((current) => ({
        portfolio: (current.portfolio || []).filter((alert) => alert.symbol !== symbol),
        watchlist: current.watchlist || [],
      }))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function calculate() {
    if (!holdings.length) return
    await loadPortfolio()
  }

  function updatePreference(key, value) {
    setPreferences((current) => ({
      ...current,
      [key]: value,
    }))
  }

  async function savePreferences() {
    setSavingPreferences(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, '/portfolio/alert-preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(detail.detail || `HTTP ${response.status}`)
      }
      const payload = await response.json()
      setPreferences({ ...DEFAULT_PREFERENCES, ...(payload.preferences || {}) })
      if (payload.count != null) applyAlertPayload(payload.alerts || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingPreferences(false)
    }
  }

  async function addWatchlistSymbol() {
    const symbol = watchlistForm.symbol.trim().toUpperCase()
    if (!symbol) return
    setLoading(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, '/portfolio/watchlist', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol }),
      })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(detail.detail || `HTTP ${response.status}`)
      }
      const payload = await response.json()
      setWatchlist(payload.watchlist || [])
      setWatchlistSnapshot(payload.snapshot || null)
      applyAlertPayload(payload.alerts || [])
      setWatchlistForm(EMPTY_WATCHLIST_FORM)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function removeWatchlistSymbol(symbol) {
    setLoading(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, `/portfolio/watchlist/${symbol}`, { method: 'DELETE' })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(detail.detail || `HTTP ${response.status}`)
      }
      const payload = await response.json()
      setWatchlist(payload.watchlist || [])
      setWatchlistSnapshot(payload.snapshot || null)
      applyAlertPayload(payload.alerts || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function addNote() {
    const symbol = noteForm.symbol.trim().toUpperCase()
    const noteText = noteForm.note_text.trim()
    const noteType = noteForm.note_type
    const noteTitle = noteForm.note_title.trim()
    const reviewDate = noteForm.review_date.trim()
    if (!symbol || !noteText) return
    setLoading(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, '/notes', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          note_type: noteType,
          note_title: noteTitle || null,
          review_date: reviewDate || null,
          note_text: noteText,
        }),
      })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(detail.detail || `HTTP ${response.status}`)
      }
      const payload = await response.json()
      setNotes(payload.notes || [])
      setNoteForm(EMPTY_NOTE_FORM)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function removeNote(noteId) {
    setLoading(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, `/notes/${noteId}`, { method: 'DELETE' })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(detail.detail || `HTTP ${response.status}`)
      }
      const payload = await response.json()
      setNotes(payload.notes || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function moveNote(note, nextLane) {
    if (!note || !nextLane || nextLane === note.note_type) return
    setLoading(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, '/notes', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          note_id: note.note_id,
          symbol: note.symbol,
          note_type: nextLane,
          note_title: note.note_title || null,
          review_date: note.review_date || null,
          note_text: note.note_text,
        }),
      })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(detail.detail || `HTTP ${response.status}`)
      }
      const payload = await response.json()
      setNotes(payload.notes || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleNoteDragStart(note, event) {
    setDraggedNoteId(note.note_id)
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/plain', String(note.note_id))
    }
  }

  function handleNoteDragEnd() {
    setDraggedNoteId(null)
    setDragOverLane(null)
  }

  function handleLaneDragOver(lane, event) {
    event.preventDefault()
    if (dragOverLane !== lane) setDragOverLane(lane)
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
  }

  function handleLaneDrop(lane, event) {
    event.preventDefault()
    const droppedId = draggedNoteId || Number(event.dataTransfer?.getData('text/plain'))
    setDragOverLane(null)
    setDraggedNoteId(null)
    if (!droppedId) return
    const note = notes.find((entry) => entry.note_id === droppedId)
    if (!note || note.note_type === lane) return
    void moveNote(note, lane)
  }

  async function generateTelegramLinkCode() {
    setTelegramBusy(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, '/telegram/link-code', { method: 'POST' })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(detail.detail || `HTTP ${response.status}`)
      }
      const payload = await response.json()
      setTelegramLink(payload)
      if (payload.pending_code && typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(payload.pending_code)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setTelegramBusy(false)
    }
  }

  async function unlinkTelegram() {
    setTelegramBusy(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, '/telegram/link', { method: 'DELETE' })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(detail.detail || `HTTP ${response.status}`)
      }
      const payload = await response.json()
      setTelegramLink(payload.status || { linked: false, pending_code: null })
    } catch (err) {
      setError(err.message)
    } finally {
      setTelegramBusy(false)
    }
  }

  const allAlerts = [...(alerts.portfolio || []), ...(alerts.watchlist || [])]
  const topPosition = result?.portfolio_insights?.top_position
  const topGainer = result?.portfolio_insights?.top_gainer
  const topLoser = result?.portfolio_insights?.top_loser

  function preventImplicitSubmit(event) {
    if (event.key !== 'Enter') return
    const tagName = event.target?.tagName
    if (tagName === 'TEXTAREA') return
    event.preventDefault()
    event.stopPropagation()
  }

  function preventNativeSubmit(event) {
    event.preventDefault()
    event.stopPropagation()
  }

  return (
    <div
      className="min-h-screen bg-background px-3 py-4 sm:px-5 sm:py-7 lg:px-8 lg:py-8"
      onKeyDownCapture={preventImplicitSubmit}
      onSubmitCapture={preventNativeSubmit}
    >
      <div className="terminal-shell">
        <div className="mb-10 flex flex-col items-start justify-between gap-6 md:flex-row md:items-start">
          <div className="terminal-panel w-full px-6 py-6 sm:px-8 sm:py-8">
            <p className="terminal-label text-outline">Portfolio terminal // personal workspace</p>
            <h1 className="mt-4 font-headline text-4xl font-extrabold uppercase tracking-tight text-slate-900 sm:text-[4rem]">
              Portfolio
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-8 text-slate-500">
              Track positions, monitor portfolio risk, and keep your notes attached to the names you already own or still plan to buy.
            </p>
          </div>
          {result && (
            <div className="flex w-full flex-wrap items-center gap-3 md:w-auto md:justify-end">
              <span className="terminal-chip">Prices as of {result.as_of_date}</span>
              <button
                type="button"
                onClick={calculate}
                disabled={loading}
                className="terminal-button px-4 py-3 disabled:opacity-50"
              >
                {loading ? 'Refreshing' : 'Refresh'}
              </button>
            </div>
          )}
        </div>

        <div className="terminal-panel px-6 py-6">
          <h2 className="font-headline text-2xl font-bold uppercase tracking-tight text-slate-900">Add Position</h2>
          <div className="mt-5 flex flex-wrap items-end gap-4">
            <div className="w-full sm:w-auto">
              <p className="terminal-label mb-2 text-outline">Ticker</p>
              <div className={portfolioLocked ? 'pointer-events-none opacity-60' : ''}>
                <TickerInput
                  value={form.symbol}
                  onChange={(value) => setForm((current) => ({ ...current, symbol: value }))}
                  inputClassName="w-full border-2 border-[#2a63f6] bg-[#eef4ff] px-3 py-3 text-sm font-semibold text-slate-800 shadow-[3px_3px_0_rgba(42,99,246,0.18)] focus:outline-none sm:w-48"
                />
              </div>
            </div>
            <div className="w-full sm:w-auto">
              <p className="terminal-label mb-2 text-outline">Shares</p>
              <input
                type="number"
                min="0"
                step="any"
                className="w-full border-2 border-[#2a63f6] bg-[#eef4ff] px-3 py-3 text-sm font-semibold text-slate-800 shadow-[3px_3px_0_rgba(42,99,246,0.18)] focus:outline-none sm:w-36"
                value={form.shares}
                disabled={portfolioLocked}
                onChange={(event) => setForm((current) => ({ ...current, shares: event.target.value }))}
                placeholder="0.00"
              />
            </div>
            <div className="w-full sm:w-auto">
              <p className="terminal-label mb-2 text-outline">Avg Cost</p>
              <input
                type="number"
                min="0"
                step="any"
                className="w-full border-2 border-[#2a63f6] bg-[#eef4ff] px-3 py-3 text-sm font-semibold text-slate-800 shadow-[3px_3px_0_rgba(42,99,246,0.18)] focus:outline-none sm:w-40"
                value={form.avg_cost}
                disabled={portfolioLocked}
                onChange={(event) => setForm((current) => ({ ...current, avg_cost: event.target.value }))}
                placeholder="$0.00"
              />
            </div>
            <button
              type="button"
              onClick={() => {
                void addHolding()
              }}
              disabled={portfolioLocked}
              className="terminal-button w-full px-6 py-3 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
            >
              {portfolioLocked ? 'Sign In To Add' : 'Add Position'}
            </button>
          </div>
        </div>

        {portfolioLocked && (
          <div className="terminal-surface mt-8 px-6 py-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="max-w-3xl">
                <p className="terminal-label text-outline">Private workspace</p>
                <h2 className="mt-3 font-headline text-2xl font-bold text-slate-900">Browse the product, then sign in to save your portfolio</h2>
                <p className="mt-3 text-sm leading-7 text-slate-500">
                  Markets and Analysis stay open to explore. Holdings, watchlists, notes, alerts, and Telegram linking are tied to your account and only load after sign-in.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <SignInButton mode="modal">
                  <button type="button" className="terminal-button-ghost px-4 py-3">
                    Sign In
                  </button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <button type="button" className="terminal-button px-4 py-3">
                    Create Account
                  </button>
                </SignUpButton>
              </div>
            </div>
          </div>
        )}

        {holdings.length > 0 && (
          <div className="terminal-surface mt-8 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5">
              <h2 className="font-headline text-2xl font-bold text-slate-900">Primary Holdings</h2>
              <span className="terminal-chip">{holdings.length} tracked</span>
            </div>
            <div className="hidden grid-cols-12 gap-4 bg-surface-container-low px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-outline md:grid">
              <div className="col-span-4">Asset &amp; symbol</div>
              <div className="col-span-2 text-right">Shares</div>
              <div className="col-span-2 text-right">Avg cost</div>
              <div className="col-span-2 text-right">Last price</div>
              <div className="col-span-2 text-right">Actions</div>
            </div>
            <div className="divide-y divide-surface-container">
              {result?.positions?.map((position) => (
                <div key={position.symbol} className="grid grid-cols-1 gap-4 px-6 py-5 hover:bg-surface-container-low/50 md:grid-cols-12">
                  <div className="flex items-center gap-4 md:col-span-4">
                    <CompanyLogo symbol={position.symbol} alt={`${position.symbol} logo`} size={40} />
                    <div>
                      <p className="font-semibold text-slate-900">{position.company_name}</p>
                      <p className="text-xs text-slate-500">{position.sector} • {position.symbol}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-sm font-medium text-slate-700 md:col-span-2 md:block md:text-right">
                    <span className="terminal-label text-outline md:hidden">Shares</span>
                    <span>{fmt(position.shares, 0)}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm text-slate-700 md:col-span-2 md:block md:text-right">
                    <span className="terminal-label text-outline md:hidden">Avg cost</span>
                    <span>${fmt(position.avg_cost)}</span>
                  </div>
                  <div className="flex items-center justify-between md:col-span-2 md:block md:text-right">
                    <span className="terminal-label text-outline md:hidden">Last price</span>
                    <div className="text-right">
                    <p className="font-semibold text-slate-900">${fmt(position.current_price)}</p>
                    <p className="mt-1 text-xs font-medium" style={{ color: insightTone(position.pnl_pct) }}>
                      {position.pnl_pct >= 0 ? '+' : ''}{fmt(position.pnl_pct)}%
                    </p>
                    </div>
                  </div>
                  <div className="flex justify-end md:col-span-2 md:text-right">
                    <button
                      type="button"
                      onClick={() => removeHolding(position.symbol)}
                      className="material-symbols-outlined text-slate-400 transition-colors hover:text-[#c76d63]"
                    >
                      close
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!portfolioLocked && error && (
          <div className="mt-8 border border-[#d8b0aa] bg-[#fff4f2] px-5 py-4 text-sm text-[#9d4840]">
            <strong>Error:</strong> {error}
          </div>
        )}

        {!portfolioLocked && result && (
          <div className="mt-8 space-y-8">
            <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
              {[
                { label: 'Total Value', value: `$${fmt(result.total_value)}`, sub: `${result.positions.length} positions` },
                { label: 'Total Cost', value: `$${fmt(result.total_cost)}`, sub: 'Average cost basis' },
                {
                  label: 'Total P&L',
                  value: `${result.total_pnl >= 0 ? '+' : ''}$${fmt(result.total_pnl)}`,
                  sub: `${result.total_pnl_pct >= 0 ? '+' : ''}${fmt(result.total_pnl_pct)}% return`,
                },
                {
                  label: 'Active Alerts',
                  value: `${allAlerts.length}`,
                  sub: 'Portfolio + watchlist',
                },
              ].map((card, cardIndex) => (
                <div
                  key={card.label}
                  className={`terminal-panel px-6 py-6 shadow-none ${
                    cardIndex === 0
                      ? 'terminal-card-accent-blue'
                      : cardIndex === 1
                        ? 'terminal-card-accent-yellow'
                        : cardIndex === 2
                          ? result.total_pnl >= 0
                            ? 'terminal-card-accent-green'
                            : 'terminal-card-accent-red'
                          : 'terminal-card-accent-red'
                  }`}
                >
                  <p className="terminal-label text-outline">{card.label}</p>
                  <p className="mt-4 font-headline text-4xl font-bold text-slate-900">{card.value}</p>
                  <p className="mt-2 text-sm text-slate-500">{card.sub}</p>
                </div>
              ))}
            </div>

            <div className="terminal-surface">
              <button
                type="button"
                onClick={() => setPreferencesOpen((current) => !current)}
                className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left"
              >
                <div>
                  <p className="terminal-label text-outline">Alert preferences</p>
                  <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-500">
                    Tune how portfolio alerts fire and whether Telegram should send your daily brief or push urgent signals.
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <span className="terminal-chip">{preferencesOpen ? 'Expanded' : 'Collapsed'}</span>
                  <span className="material-symbols-outlined text-slate-500">
                    {preferencesOpen ? 'expand_less' : 'expand_more'}
                  </span>
                </div>
              </button>

              {preferencesOpen && (
                <div className="border-t border-outline/10 px-6 py-6">
                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={savePreferences}
                      disabled={savingPreferences}
                      className="bg-slate-700 px-5 py-2.5 terminal-label text-white transition-colors hover:bg-slate-800 disabled:opacity-50"
                    >
                      {savingPreferences ? 'Saving' : 'Save Preferences'}
                    </button>
                  </div>

                  <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
                    <div className="terminal-surface-soft px-5 py-5">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="terminal-label text-outline">Concentration alerts</p>
                          <p className="mt-2 text-sm text-slate-500">Warn when one position becomes too dominant.</p>
                        </div>
                        <label className="flex items-center gap-2 text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={preferences.concentration_alerts_enabled}
                            onChange={(event) => updatePreference('concentration_alerts_enabled', event.target.checked)}
                          />
                          Enabled
                        </label>
                      </div>
                      <div className="mt-4">
                        <p className="terminal-label mb-2 text-outline">Threshold %</p>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          step="0.1"
                          className="w-32 border border-outline/20 bg-white px-3 py-3 text-sm text-slate-700 focus:outline-none"
                          value={preferences.concentration_threshold_pct}
                          onChange={(event) =>
                            updatePreference('concentration_threshold_pct', Number(event.target.value || 0))
                          }
                        />
                      </div>
                    </div>

                    <div className="terminal-surface-soft px-5 py-5">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="terminal-label text-outline">Daily move alerts</p>
                          <p className="mt-2 text-sm text-slate-500">Flag unusually large moves in owned names.</p>
                        </div>
                        <label className="flex items-center gap-2 text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={preferences.daily_move_alerts_enabled}
                            onChange={(event) => updatePreference('daily_move_alerts_enabled', event.target.checked)}
                          />
                          Enabled
                        </label>
                      </div>
                      <div className="mt-4">
                        <p className="terminal-label mb-2 text-outline">Move threshold %</p>
                        <input
                          type="number"
                          min="0"
                          step="0.1"
                          className="w-32 border border-outline/20 bg-white px-3 py-3 text-sm text-slate-700 focus:outline-none"
                          value={preferences.daily_move_threshold_pct}
                          onChange={(event) => updatePreference('daily_move_threshold_pct', Number(event.target.value || 0))}
                        />
                      </div>
                    </div>

                    <div className="terminal-surface-soft px-5 py-5">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="terminal-label text-outline">RSI alerts</p>
                          <p className="mt-2 text-sm text-slate-500">Surface overbought and oversold positions automatically.</p>
                        </div>
                        <label className="flex items-center gap-2 text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={preferences.rsi_alerts_enabled}
                            onChange={(event) => updatePreference('rsi_alerts_enabled', event.target.checked)}
                          />
                          Enabled
                        </label>
                      </div>
                      <div className="mt-4 grid grid-cols-2 gap-4">
                        <div>
                          <p className="terminal-label mb-2 text-outline">Overbought RSI</p>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            step="1"
                            className="w-full border border-outline/20 bg-white px-3 py-3 text-sm text-slate-700 focus:outline-none"
                            value={preferences.overbought_rsi_threshold}
                            onChange={(event) =>
                              updatePreference('overbought_rsi_threshold', Number(event.target.value || 0))
                            }
                          />
                        </div>
                        <div>
                          <p className="terminal-label mb-2 text-outline">Oversold RSI</p>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            step="1"
                            className="w-full border border-outline/20 bg-white px-3 py-3 text-sm text-slate-700 focus:outline-none"
                            value={preferences.oversold_rsi_threshold}
                            onChange={(event) =>
                              updatePreference('oversold_rsi_threshold', Number(event.target.value || 0))
                            }
                          />
                        </div>
                      </div>
                    </div>

                    <div className="terminal-surface-soft px-5 py-5">
                      <p className="terminal-label text-outline">Telegram delivery</p>
                      <p className="mt-2 text-sm text-slate-500">
                        Control whether FinSight sends daily briefs and push alerts to your bot chat.
                      </p>
                      <div className="mt-5 space-y-4">
                        <label className="flex items-center justify-between gap-4 text-sm text-slate-700">
                          <span>Daily morning brief</span>
                          <input
                            type="checkbox"
                            checked={preferences.telegram_daily_brief_enabled}
                            onChange={(event) => updatePreference('telegram_daily_brief_enabled', event.target.checked)}
                          />
                        </label>
                        <label className="flex items-center justify-between gap-4 text-sm text-slate-700">
                          <span>Push alert delivery</span>
                          <input
                            type="checkbox"
                            checked={preferences.telegram_alerts_enabled}
                            onChange={(event) => updatePreference('telegram_alerts_enabled', event.target.checked)}
                          />
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
              <div className="col-span-12 space-y-6 lg:col-span-8">
                <div className="flex min-h-[44px] flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
                  <h2 className="font-headline text-2xl font-bold text-slate-900">Primary Watchlist</h2>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={loadPortfolio}
                      className="terminal-button-ghost px-4 py-2 text-xs"
                    >
                      Edit List
                    </button>
                    <button
                      type="button"
                      onClick={() => document.getElementById('portfolio-watchlist-input')?.focus()}
                      className="terminal-button px-4 py-2 text-xs"
                    >
                      Add Symbol
                    </button>
                  </div>
                </div>
                <div className="terminal-surface overflow-hidden lg:h-[392px]">
                  <div className="hidden grid-cols-12 gap-4 bg-surface-container-low px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-outline md:grid">
                    <div className="col-span-5">Asset &amp; symbol</div>
                    <div className="col-span-2 text-right">Last price</div>
                    <div className="col-span-2 text-right">24h change</div>
                    <div className="col-span-2 text-center">Trend</div>
                    <div className="col-span-1 text-right">Actions</div>
                  </div>
                  <div className="border-b border-surface-container px-6 py-4">
                    <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-end">
                      <div className="flex-1">
                        <TickerInput
                          value={watchlistForm.symbol}
                          onChange={(value) => setWatchlistForm({ symbol: value })}
                          widthClass="w-full"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          void addWatchlistSymbol()
                        }}
                        className="terminal-button px-4 py-3 sm:w-auto"
                      >
                        Add
                      </button>
                    </div>
                  </div>
                  <div className="divide-y divide-surface-container lg:h-[258px] lg:overflow-y-auto">
                    {watchlist.length ? watchlist.map((item) => {
                      const liveItem = watchlistSnapshot?.items?.find((entry) => entry.symbol === item.symbol)
                      const dailyChange = liveItem?.daily_pct_change ?? 0
                      return (
                        <div key={item.symbol} className="grid grid-cols-1 gap-4 px-6 py-5 hover:bg-surface-container-low/40 md:grid-cols-12">
                          <div className="flex items-center gap-4 md:col-span-5">
                            <CompanyLogo symbol={item.symbol} alt={`${item.symbol} logo`} size={40} />
                            <div>
                              <p className="font-semibold text-slate-900">{liveItem?.company_name || item.symbol}</p>
                              <p className="text-xs text-slate-500">{liveItem?.sector || 'Tracked name'} • {item.symbol}</p>
                            </div>
                          </div>
                          <div className="flex items-center justify-between font-semibold text-slate-900 md:col-span-2 md:block md:text-right">
                            <span className="terminal-label text-outline md:hidden">Last price</span>
                            <span>{liveItem?.current_price != null ? `$${fmt(liveItem.current_price)}` : '--'}</span>
                          </div>
                          <div className="flex items-center justify-between text-sm font-medium md:col-span-2 md:block md:text-right" style={{ color: insightTone(dailyChange) }}>
                            <span className="terminal-label text-outline md:hidden">24h change</span>
                            <span>{liveItem?.daily_pct_change != null ? `${dailyChange >= 0 ? '+' : ''}${fmt(dailyChange)}%` : '--'}</span>
                          </div>
                          <div className="flex items-center justify-between md:col-span-2 md:justify-center">
                            <span className="terminal-label text-outline md:hidden">Trend</span>
                            <WatchlistSparkline
                              points={liveItem?.trend_points || []}
                              up={dailyChange >= 0}
                            />
                          </div>
                          <div className="flex justify-end md:col-span-1 md:text-right">
                            <button
                              onClick={() => removeWatchlistSymbol(item.symbol)}
                              type="button"
                              className="material-symbols-outlined text-slate-400 transition-colors hover:text-[#c76d63]"
                            >
                              close
                            </button>
                          </div>
                        </div>
                      )
                    }) : (
                      <div className="px-6 py-8 text-sm text-slate-500">No watchlist names yet. Add a ticker to start tracking it.</div>
                    )}
                  </div>
                </div>

              </div>

              <div className="col-span-12 space-y-6 lg:col-span-4">
                <div className="flex min-h-[44px] items-center justify-between">
                  <h2 className="font-headline text-2xl font-bold text-slate-900">Portfolio Signals</h2>
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#d14f59] text-[10px] font-bold text-white">
                    {allAlerts.length}
                  </span>
                </div>
                <div className="terminal-surface flex flex-col overflow-hidden lg:h-[392px]">
                  <div className="max-h-[170px] overflow-y-auto border-b border-surface-container px-5 py-5">
                    {allAlerts.length ? (
                      <div className="space-y-3">
                        {allAlerts.map((alert) => (
                          <div
                            key={alert.alert_id}
                            className="rounded-sm border-l-[4px] border-[#14181c] bg-white/80 px-3 py-3"
                            style={{ borderLeftColor: alertAccent(alert) }}
                          >
                            <div className="mb-2 flex items-start justify-between gap-3">
                              <span
                                className="rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wider"
                                style={{ backgroundColor: `${alertAccent(alert)}14`, color: alertAccent(alert) }}
                              >
                                {alert.alert_type.replaceAll('_', ' ')}
                              </span>
                              <span className="text-[10px] font-medium text-outline">{alert.symbol || alert.source_scope}</span>
                            </div>
                            <p className="text-sm font-semibold text-slate-900">{alert.title}</p>
                            <p className="mt-2 text-xs leading-6 text-slate-500">{alert.message}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">No active alerts right now.</p>
                    )}
                  </div>
                  <div className="flex-1 px-6 py-6">
                    <h3 className="terminal-label text-outline">Position overview</h3>
                    <div className="mt-5 space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-500">Largest position</span>
                        <span className="font-semibold text-slate-900">{topPosition?.symbol || '--'}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-500">Top winner</span>
                        <span className="font-semibold" style={{ color: insightTone(topGainer?.pnl_pct || 0) }}>
                          {topGainer?.symbol || '--'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-500">Top loser</span>
                        <span className="font-semibold" style={{ color: insightTone(topLoser?.pnl_pct || 0) }}>
                          {topLoser?.symbol || '--'}
                        </span>
                      </div>
                      <div className="pt-4">
                        <p className="text-xs font-bold uppercase tracking-wider text-outline">Concentration profile</p>
                        <p className="mt-3 font-headline text-4xl font-bold text-slate-900">
                          {result.portfolio_insights?.concentration?.top_position_weight_pct != null
                            ? `${fmt(result.portfolio_insights.concentration.top_position_weight_pct, 1)}%`
                            : '--'}
                        </p>
                        <p className="mt-2 text-sm text-slate-500">
                          {result.portfolio_insights?.concentration?.level || 'Balanced'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="col-span-12">
                <div className="terminal-panel p-6">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <h3 className="font-headline text-2xl font-bold text-slate-900">Notes Board</h3>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="terminal-chip">{notes.length} notes saved</span>
                    </div>
                  </div>
                  <div className="mt-6 grid gap-6 2xl:grid-cols-[minmax(340px,0.62fr)_minmax(0,2.38fr)]">
                    <div className="terminal-panel-soft space-y-3 px-4 py-4">
                      <TickerInput
                        value={noteForm.symbol}
                        onChange={(value) => setNoteForm((current) => ({ ...current, symbol: value }))}
                        placeholder="Ticker this note belongs to"
                        inputClassName="w-full border-2 border-[#2a63f6] bg-[#eef4ff] px-3 py-3 text-sm font-semibold text-slate-800 shadow-[3px_3px_0_rgba(42,99,246,0.18)] focus:outline-none"
                      />
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div>
                          <p className="terminal-label mb-2 text-outline">Note Lane</p>
                          <select
                            className="terminal-input-muted"
                            value={noteForm.note_type}
                            onChange={(event) => setNoteForm((current) => ({ ...current, note_type: event.target.value }))}
                          >
                            {Object.entries(NOTE_TYPE_LABELS).map(([value, label]) => (
                              <option key={value} value={value}>{label}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <p className="terminal-label mb-2 text-outline">Review Date</p>
                          <input
                            type="date"
                            className="terminal-input-muted"
                            value={noteForm.review_date}
                            onChange={(event) => setNoteForm((current) => ({ ...current, review_date: event.target.value }))}
                          />
                        </div>
                      </div>
                      <input
                        className="terminal-input-muted"
                        placeholder="Title, e.g. P1 now | Cut if guidance slips"
                        value={noteForm.note_title}
                        onChange={(event) => setNoteForm((current) => ({ ...current, note_title: event.target.value }))}
                      />
                      <textarea
                        className="terminal-input-muted min-h-[150px] w-full resize-none sm:min-h-[180px]"
                        placeholder="Write the thesis, trigger, risk rule, or review note for this ticker."
                        value={noteForm.note_text}
                        onChange={(event) => setNoteForm((current) => ({ ...current, note_text: event.target.value }))}
                      />
                      <div className="flex items-center justify-end">
                        <button
                          type="button"
                          onClick={() => {
                            void addNote()
                          }}
                          className="terminal-button px-4 py-2.5"
                        >
                          Save Note
                        </button>
                      </div>
                    </div>

                    <div className="pb-2">
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                        {NOTE_LANE_ORDER.map((lane) => (
                          <div
                            key={lane}
                            className={`rounded-xl bg-transparent p-1 ${dragOverLane === lane ? 'terminal-lane-active' : ''}`}
                            onDragOver={(event) => handleLaneDragOver(lane, event)}
                            onDragEnter={(event) => handleLaneDragOver(lane, event)}
                            onDragLeave={() => {
                              if (dragOverLane === lane) setDragOverLane(null)
                            }}
                            onDrop={(event) => handleLaneDrop(lane, event)}
                          >
                            <div className="terminal-lane-header" style={{ backgroundColor: `${noteAccent(lane)}22` }}>
                              <div>
                                <p className="terminal-label text-[#14181c]">{NOTE_TYPE_LABELS[lane]}</p>
                                <p className="mt-2 text-sm text-slate-600">{notesByLane[lane].length} cards</p>
                              </div>
                              <span className="terminal-chip border-[#14181c]/20 bg-white text-[#14181c]">{String(notesByLane[lane].length).padStart(2, '0')}</span>
                            </div>

                            <div className="mt-4 space-y-3">
                              {notesByLane[lane].length ? notesByLane[lane].map((note) => {
                                const urgency = noteUrgency(note.note_title)
                                return (
                                  <div
                                    key={note.note_id}
                                    className={`terminal-note-card px-4 py-4 ${draggedNoteId === note.note_id ? 'terminal-note-card-dragging' : ''}`}
                                    draggable
                                    onDragStart={(event) => handleNoteDragStart(note, event)}
                                    onDragEnd={handleNoteDragEnd}
                                    style={{ borderTop: `3px solid ${urgency?.color || noteAccent(note.note_type)}` }}
                                  >
                                    <div className="flex items-start justify-between gap-3">
                                      <div className="flex flex-wrap items-center gap-2">
                                        <span className="terminal-chip">{note.symbol}</span>
                                        {urgency && (
                                          <span className="terminal-chip border-0 text-white" style={{ backgroundColor: urgency.color }}>
                                            {urgency.label}
                                          </span>
                                        )}
                                        {note.note_title && <span className="terminal-chip">{note.note_title}</span>}
                                      </div>
                                      <button
                                        onClick={() => removeNote(note.note_id)}
                                        type="button"
                                        className="material-symbols-outlined text-slate-400 transition-colors hover:text-[#c76d63]"
                                      >
                                        close
                                      </button>
                                    </div>

                                    {note.review_date && (
                                      <p className="mt-3 terminal-label text-outline">Review on {note.review_date}</p>
                                    )}
                                    <p className="mt-3 text-sm leading-7 text-slate-600">{note.note_text}</p>
                                  </div>
                                )
                              }) : (
                                <div className="terminal-note-dropzone px-4 py-5 text-sm text-slate-500">
                                  {dragOverLane === lane ? 'Drop note here.' : 'No notes in this lane yet.'}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
              <div className="terminal-panel terminal-card-accent-yellow px-6 py-6">
                <p className="terminal-label text-outline">Concentration Risk</p>
                <p className="mt-4 font-headline text-4xl font-bold text-slate-900">
                  {result.portfolio_insights?.concentration?.top_position_weight_pct != null
                    ? `${fmt(result.portfolio_insights.concentration.top_position_weight_pct, 1)}%`
                    : '--'}
                </p>
                <p className="mt-2 text-sm text-slate-500">
                {result.portfolio_insights?.top_position
                    ? `${result.portfolio_insights.top_position.symbol} is your largest position`
                    : 'No positions yet'}
                </p>
                <p className="mt-3 terminal-label text-outline">
                  {result.portfolio_insights?.concentration?.level || 'Balanced'}
                </p>
              </div>

              <div className="terminal-panel terminal-card-accent-green px-6 py-6">
                <p className="terminal-label text-outline">Top Winner</p>
                <p className="mt-4 font-headline text-4xl font-bold text-slate-900">
                  {result.portfolio_insights?.top_gainer?.symbol || '--'}
                </p>
                <p
                  className="mt-2 text-sm font-semibold"
                  style={{ color: insightTone(result.portfolio_insights?.top_gainer?.pnl_pct ?? 0) }}
                >
                  {result.portfolio_insights?.top_gainer
                    ? `${result.portfolio_insights.top_gainer.pnl_pct >= 0 ? '+' : ''}${fmt(result.portfolio_insights.top_gainer.pnl_pct)}%`
                    : 'No data yet'}
                </p>
                <p className="mt-3 text-sm text-slate-500">
                  {result.portfolio_insights?.top_gainer?.company_name || 'Add holdings to calculate'}
                </p>
              </div>

              <div className="terminal-panel terminal-card-accent-red px-6 py-6">
                <p className="terminal-label text-outline">Top Loser</p>
                <p className="mt-4 font-headline text-4xl font-bold text-slate-900">
                  {result.portfolio_insights?.top_loser?.symbol || '--'}
                </p>
                <p
                  className="mt-2 text-sm font-semibold"
                  style={{ color: insightTone(result.portfolio_insights?.top_loser?.pnl_pct ?? 0) }}
                >
                  {result.portfolio_insights?.top_loser
                    ? `${result.portfolio_insights.top_loser.pnl_pct >= 0 ? '+' : ''}${fmt(result.portfolio_insights.top_loser.pnl_pct)}%`
                    : 'No data yet'}
                </p>
                <p className="mt-3 text-sm text-slate-500">
                  {result.portfolio_insights?.top_loser?.company_name || 'Add holdings to calculate'}
                </p>
              </div>
            </div>

            {result.missing_symbols?.length > 0 && (
              <div className="terminal-surface-soft px-5 py-4 text-sm text-[#9d4840]">
                <strong>Missing symbols:</strong> {result.missing_symbols.join(', ')} could not be priced from the warehouse.
              </div>
            )}

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
              <div className="terminal-panel px-6 py-6 lg:col-span-4">
                <p className="terminal-label text-outline">Sector allocation</p>
                <div className="mt-6 flex flex-col items-start gap-6 sm:flex-row sm:items-center">
                  <div className="relative h-32 w-32 shrink-0">
                    <SectorDonut sectors={result.sector_exposure} />
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <p className="font-headline text-2xl font-bold text-slate-900">{result.sector_exposure.length}</p>
                      <p className="terminal-label text-outline">Sectors</p>
                    </div>
                  </div>
                  <div className="flex-1 space-y-3">
                    {result.sector_exposure.map((sector, index) => (
                      <div key={sector.sector} className="flex items-center justify-between">
                        <span className="flex items-center gap-2 text-sm text-slate-700">
                          <span
                            className="h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: SECTOR_COLORS[index % SECTOR_COLORS.length] }}
                          />
                          {sector.sector}
                        </span>
                        <span className="font-semibold text-slate-700">{sector.pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="terminal-panel lg:col-span-8">
                <div className="border-b border-outline/10 px-6 py-4">
                  <p className="font-headline text-2xl font-bold text-slate-900">Detailed holdings</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[760px]">
                    <thead>
                      <tr className="border-b-2 border-[#14181c] bg-[#eef3f6]">
                        {['Ticker', 'Shares', 'Avg Cost', 'Price', 'P&L', 'Return'].map((heading) => (
                          <th key={heading} className="px-6 py-3 text-left terminal-label text-outline">
                            {heading}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.positions.map((position) => (
                        <tr key={position.symbol} className="border-b border-outline/15 bg-white transition-colors hover:bg-[#f4f8fb]">
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-4">
                              <CompanyLogo symbol={position.symbol} alt={`${position.symbol} logo`} size={40} />
                              <div>
                                <p className="font-headline text-lg font-bold text-slate-900">{position.company_name}</p>
                                <p className="terminal-label text-outline">{position.sector}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-700">{fmt(position.shares, 0)}</td>
                          <td className="px-6 py-4 text-sm text-slate-700">${fmt(position.avg_cost)}</td>
                          <td className="px-6 py-4 text-sm font-semibold text-slate-900">${fmt(position.current_price)}</td>
                          <td className="px-6 py-4 text-sm font-semibold" style={{ color: position.pnl >= 0 ? '#4f9f85' : '#c76d63' }}>
                            {position.pnl >= 0 ? '+' : ''}${fmt(position.pnl)}
                          </td>
                          <td className="px-6 py-4 text-sm font-semibold" style={{ color: position.pnl_pct >= 0 ? '#4f9f85' : '#c76d63' }}>
                            {position.pnl_pct >= 0 ? '+' : ''}{fmt(position.pnl_pct)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {holdings.length === 0 && (
          <div className="terminal-panel mt-16 flex flex-col items-center justify-center border-dashed px-8 py-20 text-center">
            <div className="mb-6 flex h-16 w-16 items-center justify-center border-2 border-[#14181c] bg-[#eef3f6] text-slate-700 shadow-[3px_3px_0_rgba(20,24,28,0.9)]">
              <span className="material-symbols-outlined text-3xl">account_balance_wallet</span>
            </div>
            <p className="font-headline text-3xl font-bold text-slate-900">No Positions Yet</p>
            <p className="mt-3 max-w-lg text-sm leading-7 text-slate-500">
              Add your holdings above to calculate portfolio value, profit and loss, and sector exposure inside the terminal.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
