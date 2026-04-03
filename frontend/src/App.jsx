import { useState } from 'react'
import { Show, SignInButton, SignUpButton, UserButton } from '@clerk/react'
import { useFinsightAuth } from './lib/finsight-auth'
import Chat from './pages/Chat'
import Portfolio from './pages/Portfolio'
import Dashboard from './pages/Dashboard'
import NewsArticle from './pages/NewsArticle'

const NAV = [
  { id: 'dashboard', label: 'Markets', icon: 'grid_view' },
  { id: 'chat', label: 'Analysis', icon: 'analytics' },
  { id: 'portfolio', label: 'Portfolio', icon: 'account_balance_wallet' },
]

export default function App() {
  const { authEnabled, isSignedIn } = useFinsightAuth()
  const [page, setPage] = useState('dashboard')
  const [analysisQuestion, setAnalysisQuestion] = useState('')
  const [headerSearch, setHeaderSearch] = useState('')
  const [selectedNewsArticle, setSelectedNewsArticle] = useState(null)

  function openAnalysisWithQuestion(question) {
    setAnalysisQuestion(question)
    setPage('chat')
  }

  function openNewsArticle(article) {
    setSelectedNewsArticle(article)
    setPage('news')
  }

  function submitHeaderSearch(e) {
    e.preventDefault()
    const value = headerSearch.trim()
    if (!value) return
    const normalized = /\b(price|quote|trading|stock)\b/i.test(value) ? value : `${value} price`
    openAnalysisWithQuestion(normalized)
    setHeaderSearch('')
  }

  function AppChrome() {
    return (
      <div className="min-h-screen bg-background text-on-surface">
        <header className="fixed inset-x-0 top-0 z-50 flex h-16 items-center justify-between border-b border-outline/20 bg-white/80 px-8 backdrop-blur-xl">
          <div className="flex items-center gap-10">
            <span className="font-headline text-xl font-extrabold tracking-tight text-slate-900">
              FINSIGHT
            </span>
            <nav className="hidden items-center gap-7 md:flex">
              {NAV.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setPage(item.id)}
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
          <div className="flex items-center gap-4">
            <form onSubmit={submitHeaderSearch} className="hidden lg:block">
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
                      <button className="rounded-lg border border-outline/20 bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-700 transition-colors hover:bg-surface-container-low">
                        Sign In
                      </button>
                    </SignInButton>
                    <SignUpButton mode="modal">
                      <button className="rounded-lg bg-slate-800 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white transition-colors hover:bg-slate-900">
                        Create Account
                      </button>
                    </SignUpButton>
                  </div>
                </Show>
                <Show when="signed-in">
                  <div className="rounded-full border border-outline/15 bg-white p-1">
                    <UserButton appearance={{ elements: { avatarBox: 'h-8 w-8' } }} />
                  </div>
                </Show>
              </>
            )}
          </div>
        </header>

        <aside className="fixed left-0 top-16 flex h-[calc(100vh-64px)] w-64 flex-col border-r border-outline/15 bg-surface-container-low py-8">
          <nav className="flex-1 space-y-1">
            {NAV.map((item) => {
              const active = page === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => setPage(item.id)}
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
          className="bg-background"
          style={{
            marginLeft: '256px',
            paddingTop: '64px',
            minHeight: '100vh',
            ...(page === 'chat' ? { height: '100vh', overflow: 'hidden' } : {}),
          }}
        >
          {page === 'dashboard' && <Dashboard onSearch={openAnalysisWithQuestion} onOpenNews={openNewsArticle} />}
          {page === 'chat' && <Chat initialQuestion={analysisQuestion} onInitialQuestionHandled={() => setAnalysisQuestion('')} />}
          {page === 'portfolio' && <Portfolio />}
          {page === 'news' && <NewsArticle article={selectedNewsArticle} onBack={() => setPage('dashboard')} />}
        </main>
      </div>
    )
  }

  if (!authEnabled) {
    return <AppChrome />
  }

  return <AppChrome />
}
