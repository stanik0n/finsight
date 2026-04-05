import { useEffect, useMemo, useState } from 'react'
import { Show, SignInButton, SignUpButton, UserButton } from '@clerk/react'
import { useFinsightAuth } from './lib/finsight-auth'
import { authedFetch } from './lib/api'
import Chat from './pages/Chat'
import Portfolio from './pages/Portfolio'
import Dashboard from './pages/Dashboard'
import NewsFeed from './pages/NewsFeed'
import NewsArticle from './pages/NewsArticle'

const NAV = [
  { id: 'dashboard', label: 'Markets', icon: 'grid_view' },
  { id: 'chat', label: 'Analysis', icon: 'analytics' },
  { id: 'portfolio', label: 'Portfolio', icon: 'account_balance_wallet' },
  { id: 'news-feed', label: 'News', icon: 'newspaper' },
]

const TICKER_STRIP = [
  { label: 'Nasdaq', value: '16,379.46', change: '+1.12%' },
  { label: 'BTC/USD', value: '67,842.10', change: '-2.15%' },
  { label: 'Gold', value: '2,362.10', change: '+0.06%' },
  { label: 'AAPL', value: '182.52', change: '+0.98%' },
  { label: 'S&P 500', value: '5,241.53', change: '+0.42%' },
  { label: 'VIX', value: '13.42', change: '-2.15%' },
]

function formatTickerStripValue(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '--'
  return value.toLocaleString('en-US', {
    minimumFractionDigits: value >= 1000 ? 2 : 2,
    maximumFractionDigits: 2,
  })
}

function formatTickerStripChange(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0.00%'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function buildLiveTickerStrip(snapshot) {
  if (Array.isArray(snapshot?.ticker_strip) && snapshot.ticker_strip.length) {
    const directItems = snapshot.ticker_strip.map((item) => ({
      label: item.label || item.symbol || 'Ticker',
      value: formatTickerStripValue(Number(item.close)),
      change: formatTickerStripChange(Number(item.pct_change)),
    }))
    const filtered = directItems.filter((item) => item.value !== '--')
    if (filtered.length) return filtered
  }

  const benchmarkItems = (snapshot?.benchmarks || []).slice(0, 4).map((item) => ({
    label: item.label || item.symbol || 'Benchmark',
    value: formatTickerStripValue(Number(item.close)),
    change: formatTickerStripChange(Number(item.pct_change)),
  }))

  const equityItems = (snapshot?.faang || []).slice(0, 2).map((item) => ({
    label: item.symbol || item.company_name || 'Equity',
    value: formatTickerStripValue(Number(item.close)),
    change: formatTickerStripChange(Number(item.pct_change)),
  }))

  const liveItems = [...benchmarkItems, ...equityItems].filter((item) => item.value !== '--')
  return liveItems.length ? liveItems : TICKER_STRIP
}

const NEWS_STORAGE_KEY = 'finsight:selected-news-article'

function readNewsFromStorage() {
  try {
    const raw = window.sessionStorage.getItem(NEWS_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function writeNewsToStorage(article) {
  try {
    if (article) {
      window.sessionStorage.setItem(NEWS_STORAGE_KEY, JSON.stringify(article))
    } else {
      window.sessionStorage.removeItem(NEWS_STORAGE_KEY)
    }
  } catch {
    return null
  }
}

function routeFromHash() {
  if (typeof window === 'undefined') {
    return { page: 'dashboard', params: new URLSearchParams() }
  }

  const rawHash = window.location.hash || '#/markets'
  const normalized = rawHash.startsWith('#') ? rawHash.slice(1) : rawHash
  const [pathname, search = ''] = normalized.split('?')
  const params = new URLSearchParams(search)

  switch (pathname) {
    case '':
    case '/':
    case '/markets':
      return { page: 'dashboard', params }
    case '/analysis':
      return { page: 'chat', params }
    case '/portfolio':
      return { page: 'portfolio', params }
    case '/news':
      return { page: 'news-feed', params }
    case '/news/article':
      return { page: 'news', params }
    default:
      return { page: 'dashboard', params: new URLSearchParams() }
  }
}

function buildHash(page, params = new URLSearchParams()) {
  const base =
    page === 'chat'
      ? '/analysis'
      : page === 'portfolio'
        ? '/portfolio'
        : page === 'news-feed'
          ? '/news'
        : page === 'news'
          ? '/news/article'
          : '/markets'

  const query = params.toString()
  return `#${base}${query ? `?${query}` : ''}`
}

function TelegramProfilePage() {
  const { authEnabled, getToken, isSignedIn } = useFinsightAuth()
  const [status, setStatus] = useState({ linked: false, pending_code: null, telegram_connect_url: null })
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!authEnabled || !isSignedIn) {
      setLoading(false)
      return
    }

    let cancelled = false

    async function loadStatus() {
      setLoading(true)
      setError(null)
      try {
        const response = await authedFetch(getToken, '/telegram/link')
        const payload = await response.json().catch(() => ({}))
        if (!response.ok) {
          throw new Error(payload.detail || `HTTP ${response.status}`)
        }
        if (!cancelled) {
          setStatus(payload || { linked: false, pending_code: null, telegram_connect_url: null })
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : 'Unable to load Telegram settings.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadStatus()
    return () => {
      cancelled = true
    }
  }, [authEnabled, getToken, isSignedIn])

  async function generateCode() {
    setBusy(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, '/telegram/link-code', { method: 'POST' })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(payload.detail || `HTTP ${response.status}`)
      }
      setStatus(payload || { linked: false, pending_code: null, telegram_connect_url: null })
      window.dispatchEvent(new CustomEvent('finsight:telegram-link-updated', { detail: payload }))
      if (payload.pending_code && typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(payload.pending_code)
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to generate a Telegram link code.')
    } finally {
      setBusy(false)
    }
  }

  async function unlinkTelegram() {
    setBusy(true)
    setError(null)
    try {
      const response = await authedFetch(getToken, '/telegram/link', { method: 'DELETE' })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(payload.detail || `HTTP ${response.status}`)
      }
      setStatus(payload.status || { linked: false, pending_code: null, telegram_connect_url: null })
      window.dispatchEvent(
        new CustomEvent('finsight:telegram-link-updated', {
          detail: payload.status || { linked: false, pending_code: null, telegram_connect_url: null },
        })
      )
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to unlink Telegram.')
    } finally {
      setBusy(false)
    }
  }

  function openTelegramConnect() {
    if (!status.telegram_connect_url) return
    window.open(status.telegram_connect_url, '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="space-y-5 px-1 py-1 text-slate-800">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Telegram</h2>
        <p className="mt-2 text-sm leading-7 text-slate-500">
          Link your Telegram chat to this FinSight account so your bot commands, notes, watchlist, and portfolio alerts stay private to you.
        </p>
      </div>

      {error && (
        <div className="terminal-surface-soft px-4 py-3 text-sm text-[#9d4840]">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="terminal-surface px-5 py-5">
        {loading ? (
          <p className="text-sm text-slate-500">Loading Telegram settings...</p>
        ) : status.linked ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="terminal-chip">Linked</span>
              {status.telegram_username && <span className="terminal-chip">@{status.telegram_username}</span>}
            </div>
            <p className="text-sm leading-7 text-slate-600">
              This Telegram chat is already connected to your account. You can use the bot for portfolio, notes, watchlist, and alert actions.
            </p>
            <button
              type="button"
              onClick={unlinkTelegram}
              disabled={busy}
              className="rounded-lg bg-surface-container px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-700 transition-colors hover:bg-surface-container-high disabled:opacity-50"
            >
              {busy ? 'Unlinking' : 'Unlink Telegram'}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="terminal-chip">{status.pending_code ? 'Ready to connect' : 'Not linked yet'}</span>
              {status.pending_code_expires_at && <span className="terminal-chip">Expires {status.pending_code_expires_at}</span>}
            </div>

            <p className="text-sm leading-7 text-slate-600">
              Best flow: generate a fresh token here, then open your bot with one tap. Telegram will send the secure token back through <span className="font-mono text-slate-700">/start</span> automatically.
            </p>

            {status.pending_code ? (
              <div className="terminal-surface-soft px-4 py-4">
                <p className="terminal-label text-outline">Current code</p>
                <p className="mt-3 font-mono text-2xl font-bold tracking-[0.24em] text-slate-900">{status.pending_code}</p>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => {
                  void generateCode()
                }}
                disabled={busy}
                className="terminal-button px-4 py-2.5 disabled:opacity-50"
              >
                {busy ? 'Generating' : status.pending_code ? 'Refresh Code' : 'Generate Code'}
              </button>
              <button
                type="button"
                onClick={openTelegramConnect}
                disabled={busy || !status.telegram_connect_url}
                className="terminal-button-ghost px-4 py-2.5 disabled:opacity-50"
              >
                Open Telegram Bot
              </button>
            </div>

            <div className="terminal-note-dropzone px-4 py-4 text-sm leading-7 text-slate-600">
              <p>Fallback if the deep link does not open correctly:</p>
              <p className="mt-2">
                Send <span className="font-mono text-slate-700">/link {status.pending_code || 'YOUR_CODE'}</span> to your FinSight bot manually.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const { authEnabled, getToken, isSignedIn } = useFinsightAuth()
  const [route, setRoute] = useState(() => routeFromHash())
  const [headerSearch, setHeaderSearch] = useState('')
  const [selectedNewsArticle, setSelectedNewsArticle] = useState(() => readNewsFromStorage())
  const [tickerStrip, setTickerStrip] = useState(TICKER_STRIP)

  const page = route.page

  const newsArticle = useMemo(() => {
    if (selectedNewsArticle) return selectedNewsArticle
    return route.page === 'news' ? readNewsFromStorage() : null
  }, [route.page, selectedNewsArticle])

  useEffect(() => {
    if (typeof window === 'undefined') return undefined
    if (!window.location.hash) {
      window.history.replaceState(null, '', buildHash('dashboard'))
    }

    function syncRoute() {
      setRoute(routeFromHash())
      if (routeFromHash().page === 'news') {
        setSelectedNewsArticle(readNewsFromStorage())
      }
    }

    syncRoute()
    window.addEventListener('hashchange', syncRoute)
    return () => window.removeEventListener('hashchange', syncRoute)
  }, [])

  useEffect(() => {
    function handleOpenPortfolio() {
      navigateTo('portfolio')
    }

    window.addEventListener('finsight:open-portfolio', handleOpenPortfolio)
    return () => window.removeEventListener('finsight:open-portfolio', handleOpenPortfolio)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadTickerStrip() {
      try {
        const response = await authedFetch(getToken, '/market-snapshot', { cache: 'no-store' })
        const payload = await response.json().catch(() => ({}))
        if (!response.ok) {
          throw new Error(payload.detail || `HTTP ${response.status}`)
        }
        if (!cancelled) {
          setTickerStrip(buildLiveTickerStrip(payload))
        }
      } catch {
        if (!cancelled) {
          setTickerStrip(TICKER_STRIP)
        }
      }
    }

    loadTickerStrip()
    const intervalId = window.setInterval(loadTickerStrip, 30 * 60 * 1000)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [getToken])

  function navigateTo(nextPage, { params, replace = false, article = null } = {}) {
    if (article !== null) {
      writeNewsToStorage(article)
      setSelectedNewsArticle(article)
    } else if (nextPage !== 'news') {
      setSelectedNewsArticle(null)
    }

    const nextHash = buildHash(nextPage, params)
    if (replace) {
      window.history.replaceState(null, '', nextHash)
      setRoute(routeFromHash())
      return
    }
    window.location.hash = nextHash
  }

  function openAnalysisWithQuestion(question) {
    const params = new URLSearchParams()
    params.set('q', question)
    navigateTo('chat', { params })
  }

  function openNewsArticle(article) {
    navigateTo('news', { article })
  }

  function submitHeaderSearch(e) {
    e.preventDefault()
    const value = headerSearch.trim()
    if (!value) return
    const normalized = /\b(price|quote|trading|stock)\b/i.test(value) ? value : `${value} price`
    openAnalysisWithQuestion(normalized)
    setHeaderSearch('')
  }

  function clearAnalysisQuestionFromRoute() {
    if (page !== 'chat' || !route.params.get('q')) return
    navigateTo('chat', { replace: true })
  }

  function AppChrome() {
    return (
      <div className="min-h-screen bg-background text-on-surface">
        <div className="fixed inset-x-0 top-0 z-50 bg-[#eef2f4] px-2 pb-2 pt-2 sm:px-4">
          <div className="terminal-shell overflow-hidden rounded-[22px] border-2 border-[#14181c] bg-white shadow-[4px_4px_0_rgba(20,24,28,0.95)]">
            <div className="terminal-ticker-strip hidden md:flex">
              <div className="terminal-ticker-run">
                {[...tickerStrip, ...tickerStrip].map((item, index) => (
                  <div key={`${item.label}-${index}`} className="terminal-ticker-item">
                    <span className="text-[#4f5964]">{item.label}</span>
                    <span className="text-[#14181c]">{item.value}</span>
                    <span style={{ color: item.change.startsWith('-') ? '#d14f59' : '#1f8f54' }}>{item.change}</span>
                  </div>
                ))}
              </div>
            </div>
            <header className="flex h-16 items-center justify-between px-4 sm:h-[74px] sm:px-6 lg:px-8">
              <div className="flex min-w-0 items-center gap-4 sm:gap-10">
                <button
                  type="button"
                  onClick={() => navigateTo('dashboard')}
                  className="shrink-0 font-headline text-lg font-extrabold tracking-tight text-slate-900 sm:text-[1.55rem]"
                >
                  FINSIGHT
                </button>
                <nav className="hidden items-center gap-7 md:flex">
                  {NAV.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => navigateTo(item.id)}
                      className="border-b-[3px] pb-1 text-[11px] font-bold uppercase tracking-[0.24em] transition-colors"
                      style={{
                        borderColor: page === item.id ? '#14181c' : 'transparent',
                        color: page === item.id ? '#14181c' : '#7e8891',
                      }}
                    >
                      {item.label}
                    </button>
                  ))}
                </nav>
              </div>
              <div className="flex items-center gap-2 sm:gap-4">
                <form onSubmit={submitHeaderSearch} className="hidden xl:block">
                  <div className="flex items-center gap-3 border-2 border-[#14181c] bg-[#fbfcfc] px-4 py-2">
                    <span className="material-symbols-outlined text-[18px] text-slate-500">search</span>
                    <input
                      value={headerSearch}
                      onChange={(e) => setHeaderSearch(e.target.value)}
                      className="w-64 bg-transparent text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none"
                      placeholder="Search stocks..."
                      autoComplete="off"
                    />
                  </div>
                </form>
                {authEnabled && (
                  <>
                    <Show when="signed-out">
                      <div className="flex items-center gap-2">
                        <SignInButton mode="modal">
                          <button className="terminal-button terminal-button-secondary px-3 py-2 sm:px-4">
                            Sign In
                          </button>
                        </SignInButton>
                        <SignUpButton mode="modal">
                          <button className="terminal-button hidden px-4 py-2 sm:inline-flex">
                            Create Account
                          </button>
                        </SignUpButton>
                      </div>
                    </Show>
                    <Show when="signed-in">
                      <div className="rounded-full border-2 border-[#14181c] bg-white p-1 shadow-[2px_2px_0_rgba(20,24,28,0.95)]">
                        <UserButton appearance={{ elements: { avatarBox: 'h-8 w-8' } }}>
                          <UserButton.MenuItems>
                            <UserButton.Action
                              label="Telegram"
                              labelIcon={<span className="material-symbols-outlined text-[16px]">sms</span>}
                              open="telegram"
                            />
                          </UserButton.MenuItems>
                          <UserButton.UserProfilePage
                            label="Telegram"
                            url="telegram"
                            labelIcon={<span className="material-symbols-outlined text-[16px]">sms</span>}
                          >
                            <TelegramProfilePage />
                          </UserButton.UserProfilePage>
                        </UserButton>
                      </div>
                    </Show>
                  </>
                )}
              </div>
            </header>
            <div className="border-t-2 border-[#14181c] px-3 py-3 md:hidden">
              <form onSubmit={submitHeaderSearch}>
                <div className="flex items-center gap-3 border-2 border-[#14181c] bg-[#fbfcfc] px-3 py-2.5">
                  <span className="material-symbols-outlined text-[18px] text-slate-500">search</span>
                  <input
                    value={headerSearch}
                    onChange={(e) => setHeaderSearch(e.target.value)}
                    className="w-full bg-transparent text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none"
                    placeholder="Search stocks..."
                    autoComplete="off"
                  />
                </div>
              </form>
            </div>
          </div>
        </div>

        <main
          className={
            page === 'chat'
              ? 'fixed inset-x-0 top-[140px] bottom-20 overflow-hidden bg-background md:top-[112px] md:bottom-0'
              : 'box-border bg-background pb-20 pt-[140px] md:pb-0 md:pt-[112px]'
          }
          style={
            page === 'chat'
              ? undefined
              : {
                  minHeight: '100vh',
                }
          }
        >
          {page === 'dashboard' && <Dashboard onSearch={openAnalysisWithQuestion} onOpenNews={openNewsArticle} />}
          {page === 'chat' && (
            <Chat
              initialQuestion={route.params.get('q') || ''}
              onInitialQuestionHandled={clearAnalysisQuestionFromRoute}
            />
          )}
          {page === 'portfolio' && <Portfolio />}
          {page === 'news-feed' && <NewsFeed onOpenArticle={openNewsArticle} />}
          {page === 'news' && <NewsArticle article={newsArticle} onBack={() => navigateTo('news-feed')} />}
        </main>

        <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t-2 border-[#14181c] bg-white/95 px-2 py-2 backdrop-blur md:hidden">
          {NAV.map((item) => {
            const active = page === item.id
            return (
              <button
                key={item.id}
                onClick={() => navigateTo(item.id)}
                className="flex flex-col items-center justify-center gap-1 rounded-none px-2 py-2 text-center transition-colors"
                style={{
                  backgroundColor: active ? '#eef3f6' : 'transparent',
                  color: active ? '#14181c' : '#7b8790',
                }}
              >
                <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                <span className="text-[10px] font-bold uppercase tracking-[0.16em]">{item.label}</span>
              </button>
            )
          })}
        </nav>
      </div>
    )
  }

  if (!authEnabled) {
    return <AppChrome />
  }

  return <AppChrome />
}
