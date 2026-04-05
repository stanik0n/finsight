import { useEffect, useMemo, useRef, useState } from 'react'
import { SignInButton } from '@clerk/react'
import CommentaryPanel from '../components/CommentaryPanel'
import { authedFetch } from '../lib/api'
import { useFinsightAuth } from '../lib/finsight-auth'

const EXAMPLES = [
  'Which tech stocks had the highest RSI last week?',
  'Show me energy stocks with volume spikes in the last 30 days',
  'Which stocks closed above their 50-day SMA yesterday?',
  'Top 5 gainers in Healthcare this month?',
]

const ANALYSIS_MODES = [
  {
    label: 'Live Quotes',
    icon: 'show_chart',
    hint: 'Intraday prices and current tape',
    prompt: '',
    placeholder: 'Enter a ticker for a live quote...',
  },
  {
    label: 'Technical Screens',
    icon: 'query_stats',
    hint: 'RSI, SMA, movers, and momentum scans',
    prompt: 'Which tech stocks had the highest RSI last week?',
  },
  {
    label: 'Portfolio',
    icon: 'account_balance_wallet',
    hint: 'Saved holdings and concentration reads',
    prompt: 'How is my portfolio?',
  },
  {
    label: 'Watchlist',
    icon: 'visibility',
    hint: 'Tracked names and alert context',
    prompt: 'Any watchlist alerts I should know about?',
  },
  {
    label: 'News',
    icon: 'article',
    hint: 'Market stories and article follow-up',
    prompt: 'What market news matters most right now?',
  },
]

function formatTimestamp(value) {
  if (!value) return 'N/A'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'America/Chicago',
    timeZoneName: 'short',
  })
}

function formatCurrency(value) {
  return `$${Number(value).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function formatPercent(value) {
  return `${value >= 0 ? '+' : ''}${Number(value).toFixed(2)}%`
}

function metricCards(entry) {
  if (!entry?.results?.length) return []

  const first = entry.results[0]
  const values = []

  if (entry.path === 'portfolio') {
    if (typeof first.total_value === 'number') {
      values.push({
        label: 'Total Value',
        value: formatCurrency(first.total_value),
        sublabel: `${first.position_count || entry.row_count || 0} saved holdings`,
      })
    }

    if (typeof first.total_pnl_pct === 'number') {
      values.push({
        label: 'Total Return',
        value: formatPercent(first.total_pnl_pct),
        sublabel:
          typeof first.total_pnl === 'number'
            ? `${first.total_pnl >= 0 ? '+' : '-'}${formatCurrency(Math.abs(first.total_pnl))} unrealized`
            : 'Unrealized P&L',
      })
    }

    if (first.top_position_symbol) {
      values.push({
        label: 'Largest Position',
        value: first.top_position_symbol,
        sublabel:
          typeof first.top_position_weight_pct === 'number'
            ? `${first.top_position_weight_pct.toFixed(1)}% of portfolio`
            : 'Top portfolio weight',
      })
    }

    if (typeof first.weighted_daily_change_pct === 'number') {
      values.push({
        label: 'Daily Move',
        value: formatPercent(first.weighted_daily_change_pct),
        sublabel: 'Weighted portfolio change',
      })
    }

    if (!values.length) {
      values.push({
        label: 'Portfolio',
        value: `${first.position_count || entry.row_count || 0}`,
        sublabel: 'Saved holdings',
      })
    }

    return values
  }

  if (typeof first.close === 'number') {
    values.push({
      label: 'Current Close',
      value: formatCurrency(first.close),
      sublabel: first.symbol || entry.path?.toUpperCase() || 'QUERY',
    })
  }

  if (entry.path === 'hot' && first.timestamp) {
    values.push({
      label: 'Last Update',
      value: formatTimestamp(first.timestamp),
      sublabel: 'Latest intraday bar',
    })
  }

  if (entry.path === 'hot' && typeof first.vwap === 'number') {
    values.push({
      label: 'VWAP',
      value: formatCurrency(first.vwap),
      sublabel: 'Volume-weighted price',
    })
  }

  if (entry.path === 'hot' && typeof first.volume === 'number') {
    values.push({
      label: 'Volume',
      value: first.volume.toLocaleString('en-US'),
      sublabel: 'Latest bar shares',
    })
  }

  if (!values.length) {
      values.push({
        label: 'Rows Returned',
        value: String(entry.row_count ?? entry.results.length),
        sublabel:
          entry.path === 'hot'
            ? 'Live path'
            : entry.path === 'hybrid'
              ? 'Hybrid path'
              : entry.path === 'portfolio'
                ? 'Portfolio path'
                : entry.path === 'watchlist'
                  ? 'Watchlist path'
                  : entry.path === 'news'
                    ? 'News path'
                    : 'Historical path',
      })
    }

  if (typeof first.rsi_14 === 'number') {
    values.push({
      label: 'RSI',
      value: first.rsi_14.toFixed(1),
      sublabel: first.rsi_14 > 70 ? 'Overbought' : first.rsi_14 < 30 ? 'Oversold' : 'Neutral',
    })
  } else if (typeof first.pct_change === 'number') {
    values.push({
      label: 'Daily Change',
      value: formatPercent(first.pct_change),
      sublabel: 'Latest session',
    })
  }

  return values
}

function fallbackCommentary(entry) {
  if (!entry) return ''
  if (entry.commentary) return entry.commentary
  if (entry.row_count === 0) {
    return `No matching results were found for "${entry.question}". Try broadening the time range, changing the sector, or asking a less restrictive version of the same question.`
  }
  return ''
}

export default function Chat({ initialQuestion = '', onInitialQuestionHandled = () => {} }) {
  const { getToken, authEnabled, isSignedIn } = useFinsightAuth()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [streamStatus, setStreamStatus] = useState(null)
  const [draftQuestion, setDraftQuestion] = useState('')
  const [inputPlaceholder, setInputPlaceholder] = useState('Ask about the market...')
  const inputRef = useRef(null)
  const messagesContainerRef = useRef(null)
  const messagesEndRef = useRef(null)

  const chatLockedToPublic = authEnabled && !isSignedIn

  function questionNeedsAccount(question) {
    const q = (question || '').toLowerCase()
    return (
      /\bportfolio\b/.test(q) ||
      /\bwatchlist\b/.test(q) ||
      /\bmy holdings\b/.test(q) ||
      /\bmy positions\b/.test(q) ||
      /\bmy notes\b/.test(q) ||
      /\bhow is my portfolio\b/.test(q)
    )
  }

  const visibleModes = useMemo(
    () => ANALYSIS_MODES.filter((item) => !chatLockedToPublic || !['Portfolio', 'Watchlist'].includes(item.label)),
    [chatLockedToPublic],
  )

  const visibleExamples = useMemo(
    () => EXAMPLES.filter((example) => !chatLockedToPublic || !questionNeedsAccount(example)),
    [chatLockedToPublic],
  )

  useEffect(() => {
    authedFetch(getToken, '/stream-status').then((r) => r.json()).then(setStreamStatus).catch(() => null)
  }, [])

  useEffect(() => {
    if (!initialQuestion?.trim()) return
    handleQuestion(initialQuestion)
    onInitialQuestionHandled()
  }, [initialQuestion])

  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return
    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'smooth',
    })
  }, [history, loading])

  async function handleQuestion(question) {
    if (!question.trim()) return
    if (chatLockedToPublic && questionNeedsAccount(question)) {
      setError('Sign in to ask about your portfolio, watchlist, or saved notes. Public market and news analysis still works.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await authedFetch(getToken, '/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(detail.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setHistory((current) => [...current, data])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleModeClick(item) {
    if (item.placeholder) {
      setDraftQuestion('')
      setInputPlaceholder(item.placeholder)
      window.requestAnimationFrame(() => {
        inputRef.current?.focus()
      })
      return
    }
    handleQuestion(item.prompt)
  }

  function submitForm(e) {
    e.preventDefault()
    const question = draftQuestion.trim()
    if (!question) return
    handleQuestion(question)
    setDraftQuestion('')
    setInputPlaceholder('Ask about the market...')
  }

  const latestEntry = history[history.length - 1]
  const cards = useMemo(() => metricCards(latestEntry), [latestEntry])
  const latestResult = latestEntry?.results?.[0]
  const isPortfolioView = latestEntry?.path === 'portfolio'
  const isSingleSymbolView = Boolean(
    !isPortfolioView &&
      (latestEntry?.results?.length === 1 ||
        (latestEntry?.results?.length &&
          latestEntry.results.every((row) => row.symbol === latestResult?.symbol))),
  )
  const routeLabel =
    latestEntry?.path === 'hot'
      ? 'Live'
      : latestEntry?.path === 'hybrid'
        ? 'Hybrid'
        : latestEntry?.path === 'portfolio'
          ? 'Portfolio'
          : latestEntry?.path === 'watchlist'
            ? 'Watchlist'
            : latestEntry?.path === 'news'
              ? 'News'
          : latestEntry?.path === 'cold'
              ? 'Historical'
              : 'Standby'
  const sidebarCards = cards.slice(0, 3)

  return (
    <div className="box-border h-full overflow-hidden bg-background px-3 py-4 sm:px-5 sm:py-5 lg:px-8 lg:py-6">
      <div className="terminal-shell h-full">
        <div className="flex h-full min-h-0 flex-col md:flex-row overflow-hidden">
      <aside className="hidden h-full min-h-0 w-60 bg-transparent pl-2 pr-2 py-4 lg:block xl:w-64">
        <div className="flex h-full flex-col overflow-y-auto border-r-2 border-[#14181c] pr-2">
          <div className="terminal-surface px-4 py-4">
            <p className="terminal-label mb-3 text-outline">Analysis Modes</p>
            <div className="space-y-1">
                {visibleModes.map((item, index) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => handleModeClick(item)}
                    className={`flex w-full items-center gap-3 border-2 px-3 py-3 text-left transition-colors ${
                      index === 1
                        ? 'border-[#14181c] bg-surface-container-low text-slate-900 shadow-[2px_2px_0_rgba(20,24,28,0.75)]'
                        : 'border-transparent text-slate-600'
                    } hover:bg-surface-container-low`}
                  >
                  <span className="material-symbols-outlined text-[18px]">{item.icon}</span>
                  <div className="min-w-0">
                    <p className="terminal-label text-[11px]">{item.label}</p>
                    <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{item.hint}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="terminal-surface px-4 py-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="terminal-label text-outline">Recent Sessions</p>
              <span className="terminal-label text-outline">{history.length}</span>
            </div>
            <div className="space-y-2">
              {history.length === 0 ? (
                <p className="text-xs text-slate-500">No sessions yet.</p>
              ) : (
                [...history].reverse().slice(0, 6).map((entry, index) => (
                  <div
                    key={`${entry.question}-${index}`}
                    className="terminal-surface-soft px-4 py-3"
                  >
                    <p className="line-clamp-2 text-xs font-medium leading-relaxed text-slate-700">
                      {entry.question}
                    </p>
                      <p className="mt-2 terminal-label text-outline">
                        {entry.path === 'hot'
                          ? 'Live route'
                          : entry.path === 'hybrid'
                            ? 'Hybrid route'
                            : entry.path === 'portfolio'
                              ? 'Portfolio route'
                              : entry.path === 'watchlist'
                                ? 'Watchlist route'
                                : entry.path === 'news'
                                  ? 'News route'
                                  : 'Historical route'}
                      </p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="terminal-surface px-4 py-4">
            <p className="terminal-label text-outline">Session shortcuts</p>
            <div className="mt-3 space-y-2">
              {visibleExamples.slice(0, 3).map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => handleQuestion(example)}
                  className="block w-full border-2 border-[#14181c] bg-white px-3 py-3 text-left text-xs leading-relaxed text-slate-600 transition-colors hover:bg-surface-container-low"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          {chatLockedToPublic && (
            <div className="terminal-surface px-4 py-4">
              <p className="terminal-label text-outline">Private account features</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-500">
                Sign in to ask about your saved portfolio, watchlist, notes, and Telegram-linked data.
              </p>
              <div className="mt-3">
                <SignInButton mode="modal">
                  <button className="terminal-button px-3 py-2">
                    Sign In
                  </button>
                </SignInButton>
              </div>
            </div>
          )}

        </div>
      </aside>

      <section className="flex min-h-0 flex-1 overflow-hidden bg-surface">
      <div className="flex h-full min-h-0 flex-1 flex-col xl:flex-row">
          <div className="relative flex min-w-0 flex-1 flex-col xl:border-r-2 xl:border-[#14181c] xl:px-8">
            <div
              ref={messagesContainerRef}
              className="flex-1 overflow-y-auto px-4 pb-[180px] pt-6 sm:px-6 sm:pb-[220px] sm:pt-8 lg:px-8 lg:pb-[250px] lg:pt-10"
            >
              <div className="mb-8 grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
                <div>
                  <span className="inline-flex border-2 border-[#14181c] bg-white px-4 py-1 terminal-label text-outline shadow-[2px_2px_0_rgba(20,24,28,0.7)]">
                    March 31, 2026
                  </span>
                  <h1 className="mt-5 font-headline text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
                    Analysis
                  </h1>
                  <p className="font-headline text-3xl font-semibold tracking-tight text-[#c7d3df] sm:text-5xl">
                    Market and portfolio questions
                  </p>
                  <p className="mt-4 max-w-3xl text-sm leading-8 text-slate-500">
                    Ask natural language questions across live markets, warehouse context, and your saved
                    portfolio from one continuous analyst canvas.
                  </p>
                </div>

                <div className="terminal-surface p-6">
                  <p className="terminal-label text-outline">Suggested questions</p>
                  <div className="mt-4 space-y-3">
                    {visibleExamples.slice(0, 3).map((example) => (
                      <button
                        key={example}
                        type="button"
                        onClick={() => handleQuestion(example)}
                        className="block w-full border-2 border-[#14181c] bg-white px-4 py-3 text-left text-sm text-slate-700 transition-colors hover:bg-surface-container-low"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {history.length === 0 && !loading && (
                <div className="terminal-panel terminal-card-accent-blue px-8 py-12 text-center">
                  <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center border-2 border-[#14181c] bg-[#eef3f6] text-slate-700 shadow-[3px_3px_0_rgba(20,24,28,0.9)]">
                    <span className="material-symbols-outlined text-3xl">psychology</span>
                  </div>
                  <p className="font-headline text-4xl font-extrabold tracking-tight text-slate-900">
                    Ask a question
                  </p>
                  <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-slate-500">
                    FinSight will route each question across live, historical, hybrid, or portfolio context and
                    return a clean analyst-style answer.
                  </p>
                </div>
              )}

              <div className="mt-8 space-y-10">
                {history.map((entry, index) => (
                  <div key={`${entry.question}-${index}`} className="space-y-5">
                    <div className="mr-0 ml-auto max-w-2xl">
                      <div className="mb-2 flex items-center justify-end gap-2">
                        <span className="terminal-label text-outline">Question</span>
                        <span className="h-1.5 w-1.5 border border-outline/60" />
                      </div>
                      <div className="terminal-surface-soft px-6 py-6">
                        <p className="text-sm leading-relaxed text-slate-700">{entry.question}</p>
                      </div>
                    </div>

                    <div className="terminal-surface p-6">
                      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 bg-primary" />
                          <span className="terminal-label text-slate-700">Response</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <span className="terminal-chip">
                              {entry.path === 'hot'
                                ? 'Live route'
                                : entry.path === 'hybrid'
                                  ? 'Hybrid route'
                                  : entry.path === 'portfolio'
                                    ? 'Portfolio route'
                                    : entry.path === 'watchlist'
                                      ? 'Watchlist route'
                                      : entry.path === 'news'
                                        ? 'News route'
                                        : 'Historical route'}
                            </span>
                          {entry.row_count === 0 && <span className="terminal-chip">No matches</span>}
                        </div>
                      </div>
                      <div className="terminal-surface-soft px-5 py-5">
                        <CommentaryPanel commentary={fallbackCommentary(entry)} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {loading && (
                <div className="terminal-surface max-w-4xl px-6 py-6">
                  <div className="mb-3 flex items-center gap-2">
                    <span className="h-1.5 w-1.5 bg-primary" />
                    <span className="terminal-label text-slate-700">Response</span>
                  </div>
                  <p className="text-sm text-slate-500">Analyzing market data and composing commentary...</p>
                </div>
              )}

              {error && (
                <div className="terminal-surface-soft mt-8 max-w-4xl px-5 py-4 text-sm text-[#8c3d38]">
                  <strong>Error:</strong> {error}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <div className="absolute inset-x-0 bottom-0 z-20 px-4 pb-4 pt-6 sm:px-6 sm:pb-6 lg:px-8 lg:pb-8 lg:pt-10">
              <div className="terminal-surface mx-auto max-w-5xl bg-[rgba(248,250,251,0.96)] px-6 py-5 backdrop-blur-md">
                <form onSubmit={submitForm}>
                  <div className="flex items-center gap-4">
                      <input
                        ref={inputRef}
                        value={draftQuestion}
                        onChange={(e) => setDraftQuestion(e.target.value)}
                        disabled={loading}
                        className="flex-1 bg-transparent py-3 text-sm font-medium text-slate-700 placeholder:text-slate-400 focus:outline-none disabled:opacity-50"
                        placeholder={inputPlaceholder}
                        autoComplete="off"
                      />
                    <button
                      type="submit"
                      disabled={loading}
                      className="material-symbols-outlined border-2 border-[#14181c] bg-[#1b55e2] p-2 text-white shadow-[3px_3px_0_rgba(20,24,28,0.9)] transition-colors hover:bg-[#2a63f6] disabled:opacity-50"
                    >
                      arrow_upward
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>

          <aside className="hidden h-full min-h-0 w-80 shrink-0 overflow-y-auto bg-transparent px-8 py-8 xl:block">
            <div className="space-y-6">
              <div className="terminal-surface px-6 py-6">
                <div className="flex items-start justify-between gap-6">
                  <div className="min-w-0">
                    <p className="terminal-label text-outline">{isPortfolioView ? 'Portfolio' : 'Symbol'}</p>
                    <h2 className="mt-2 font-headline text-3xl font-extrabold leading-none tracking-tight text-slate-900">
                      {isPortfolioView ? 'Holdings' : isSingleSymbolView ? (latestResult?.symbol || '—') : 'Basket'}
                    </h2>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="terminal-label text-outline">{isPortfolioView ? 'Total Value' : 'Current Price'}</p>
                    <p className="mt-2 font-headline text-xl font-bold leading-none text-slate-900">
                      {isPortfolioView && typeof latestResult?.total_value === 'number'
                        ? formatCurrency(latestResult.total_value)
                        : isSingleSymbolView && typeof latestResult?.close === 'number'
                          ? formatCurrency(latestResult.close)
                          : '—'}
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex items-start justify-between gap-6">
                  <div className="min-w-0">
                      <p className="terminal-label text-outline">
                        {isPortfolioView
                          ? `${latestResult?.position_count || latestEntry?.row_count || 0} saved positions`
                          : latestEntry?.path === 'watchlist'
                            ? latestEntry?.row_count
                              ? `${latestEntry.row_count} active watchlist alerts`
                              : 'No active watchlist alerts'
                            : latestEntry?.path === 'news'
                              ? latestEntry?.row_count
                                ? `${latestEntry.row_count} current market stories`
                                : 'No market stories'
                          : isSingleSymbolView
                            ? latestResult?.company_name || (latestEntry?.path === 'hot' ? 'Latest intraday quote' : 'No query yet')
                            : latestEntry?.row_count
                              ? `${latestEntry.row_count} matching symbols`
                              : 'No query yet'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="terminal-label text-[#567963]">
                      {isPortfolioView && typeof latestResult?.total_pnl_pct === 'number'
                        ? `${formatPercent(latestResult.total_pnl_pct)} total return`
                        : isSingleSymbolView && typeof latestResult?.pct_change === 'number'
                          ? formatPercent(latestResult.pct_change)
                          : isSingleSymbolView && typeof latestResult?.vwap === 'number'
                            ? `VWAP ${formatCurrency(latestResult.vwap)}`
                            : isSingleSymbolView
                              ? 'No move data'
                              : 'Multi-symbol result'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="terminal-surface px-6 py-6">
                <p className="terminal-label text-outline">Route</p>
                <p className="mt-2 font-headline text-2xl font-bold text-slate-900">{routeLabel}</p>
                  <p className="mt-2 text-sm text-slate-500">
                    {latestEntry?.path === 'hot'
                      ? 'Using the intraday feed.'
                      : latestEntry?.path === 'hybrid'
                        ? 'Combining live and historical context.'
                        : latestEntry?.path === 'portfolio'
                          ? 'Using your saved holdings.'
                          : latestEntry?.path === 'watchlist'
                            ? 'Using tracked names and watchlist alerts.'
                            : latestEntry?.path === 'news'
                              ? 'Using the market news feed.'
                          : latestEntry?.path === 'cold'
                              ? 'Using the historical warehouse.'
                              : 'Ask a question to see route details.'}
                  </p>
              </div>

              <div className="space-y-4">
                {sidebarCards.length === 0 ? (
                  <div className="terminal-surface px-6 py-6">
                    <p className="terminal-label text-outline">Metrics</p>
                    <p className="mt-2 text-sm text-slate-500">
                      {latestEntry?.row_count === 0
                        ? 'No rows matched this query.'
                        : 'Real query metrics will appear here.'}
                    </p>
                  </div>
                ) : (
                  sidebarCards.map((card) => (
                  <div key={card.label} className="terminal-surface px-6 py-6">
                      <p className="terminal-label text-outline">{card.label}</p>
                      <p className="mt-2 font-headline text-2xl font-bold text-slate-900">{card.value}</p>
                      <p className="mt-2 text-sm text-slate-500">{card.sublabel}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </aside>
        </div>
      </section>
        </div>
      </div>
    </div>
  )
}
