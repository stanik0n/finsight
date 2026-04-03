import { useEffect, useMemo, useState } from 'react'
import { Show, SignInButton, SignUpButton, UserButton } from '@clerk/react'
import { useFinsightAuth } from './lib/finsight-auth'
import { authedFetch } from './lib/api'
import Chat from './pages/Chat'
import Portfolio from './pages/Portfolio'
import Dashboard from './pages/Dashboard'
import NewsArticle from './pages/NewsArticle'

const NAV = [
  { id: 'dashboard', label: 'Markets', icon: 'grid_view' },
  { id: 'chat', label: 'Analysis', icon: 'analytics' },
  { id: 'portfolio', label: 'Portfolio', icon: 'account_balance_wallet' },
]

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
        : page === 'news'
          ? '/news'
          : '/markets'

  const query = params.toString()
  return `#${base}${query ? `?${query}` : ''}`
}

export default function App() {
  const { authEnabled, getToken, isSignedIn } = useFinsightAuth()
  const [route, setRoute] = useState(() => routeFromHash())
  const [headerSearch, setHeaderSearch] = useState('')
  const [telegramBusy, setTelegramBusy] = useState(false)
  const [selectedNewsArticle, setSelectedNewsArticle] = useState(() => readNewsFromStorage())

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

  async function generateTelegramLinkCodeFromProfile() {
    if (!authEnabled || !isSignedIn) return
    window.dispatchEvent(new CustomEvent('finsight:open-portfolio'))
    window.dispatchEvent(new CustomEvent('finsight:telegram-link-busy', { detail: true }))
    setTelegramBusy(true)
    try {
      const response = await authedFetch(getToken, '/telegram/link-code', {
        method: 'POST',
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(payload.detail || `HTTP ${response.status}`)
      }
      if (payload.pending_code && typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(payload.pending_code)
      }
      window.dispatchEvent(new CustomEvent('finsight:telegram-link-updated', { detail: payload }))
    } catch (error) {
      window.dispatchEvent(
        new CustomEvent('finsight:telegram-link-error', {
          detail: error instanceof Error ? error.message : 'Unable to generate Telegram code.',
        })
      )
    } finally {
      window.dispatchEvent(new CustomEvent('finsight:telegram-link-busy', { detail: false }))
      setTelegramBusy(false)
    }
  }

  function clearAnalysisQuestionFromRoute() {
    if (page !== 'chat' || !route.params.get('q')) return
    navigateTo('chat', { replace: true })
  }

  function AppChrome() {
    return (
      <div className="min-h-screen bg-background text-on-surface">
        <header className="fixed inset-x-0 top-0 z-50 flex h-14 items-center justify-between border-b border-outline/20 bg-white/80 px-4 backdrop-blur-xl sm:h-16 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4 sm:gap-10">
            <button
              type="button"
              onClick={() => navigateTo('dashboard')}
              className="font-headline text-lg font-extrabold tracking-tight text-slate-900 sm:text-xl"
            >
              FINSIGHT
            </button>
            <nav className="hidden items-center gap-7 md:flex">
              {NAV.map((item) => (
                <button
                  key={item.id}
                  onClick={() => navigateTo(item.id)}
                  className="border-b pb-1 text-[11px] font-bold uppercase tracking-[0.24em] transition-colors"
                  style={{
                    borderColor: page === item.id ? '#556067' : 'transparent',
                    color: page === item.id ? '#243036' : '#87939a',
                  }}
                >
                  {item.label}
                </button>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <form onSubmit={submitHeaderSearch} className="hidden xl:block">
              <div className="flex items-center gap-3 border border-outline/20 bg-surface-container-lowest px-4 py-2">
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
                      <button className="rounded-lg border border-outline/20 bg-white px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-700 transition-colors hover:bg-surface-container-low sm:px-4 sm:text-xs sm:tracking-[0.18em]">
                        Sign In
                      </button>
                    </SignInButton>
                    <SignUpButton mode="modal">
                      <button className="hidden rounded-lg bg-slate-800 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white transition-colors hover:bg-slate-900 sm:block">
                        Create Account
                      </button>
                    </SignUpButton>
                  </div>
                </Show>
                <Show when="signed-in">
                  <div className="rounded-full border border-outline/15 bg-white p-1">
                    <UserButton appearance={{ elements: { avatarBox: 'h-8 w-8' } }}>
                      <UserButton.MenuItems>
                        <UserButton.Action
                          label={telegramBusy ? 'Generating Telegram Code...' : 'Generate Telegram Code'}
                          labelIcon={<span className="material-symbols-outlined text-[16px]">sms</span>}
                          onClick={() => {
                            void generateTelegramLinkCodeFromProfile()
                          }}
                        />
                      </UserButton.MenuItems>
                    </UserButton>
                  </div>
                </Show>
              </>
            )}
          </div>
        </header>

        <aside className="fixed left-0 top-16 hidden h-[calc(100vh-64px)] w-64 flex-col border-r border-outline/15 bg-surface-container-low py-8 md:flex">
          <nav className="flex-1 space-y-1">
            {NAV.map((item) => {
              const active = page === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => navigateTo(item.id)}
                  className="flex w-full items-center gap-3 px-6 py-3 text-left transition-all"
                  style={{
                    backgroundColor: active ? '#ffffff' : 'transparent',
                    borderLeft: active ? '2px solid #556067' : '2px solid transparent',
                    color: active ? '#243036' : '#66737a',
                  }}
                >
                  <span className="material-symbols-outlined text-[18px]">{item.icon}</span>
                  <span className="terminal-label text-[11px]">{item.label}</span>
                </button>
              )
            })}
          </nav>
        </aside>

        <main
          className="bg-background pb-20 pt-14 md:ml-64 md:pb-0 md:pt-16"
          style={{
            minHeight: '100vh',
          }}
        >
          {page === 'dashboard' && <Dashboard onSearch={openAnalysisWithQuestion} onOpenNews={openNewsArticle} />}
          {page === 'chat' && (
            <Chat
              initialQuestion={route.params.get('q') || ''}
              onInitialQuestionHandled={clearAnalysisQuestionFromRoute}
            />
          )}
          {page === 'portfolio' && <Portfolio />}
          {page === 'news' && <NewsArticle article={newsArticle} onBack={() => navigateTo('dashboard')} />}
        </main>

        <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-3 border-t border-outline/20 bg-white/95 px-2 py-2 backdrop-blur md:hidden">
          {NAV.map((item) => {
            const active = page === item.id
            return (
              <button
                key={item.id}
                onClick={() => navigateTo(item.id)}
                className="flex flex-col items-center justify-center gap-1 rounded-xl px-2 py-2 text-center transition-colors"
                style={{
                  backgroundColor: active ? '#eef3f6' : 'transparent',
                  color: active ? '#243036' : '#7b8790',
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
