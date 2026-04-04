import { useEffect, useState } from 'react'
import { authedFetch } from '../lib/api'
import { useFinsightAuth } from '../lib/finsight-auth'

function formatArticleDate(value) {
  if (!value) return 'Latest'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'America/Chicago',
    timeZoneName: 'short',
  })
}

export default function NewsFeed({ onOpenArticle = () => {} }) {
  const { getToken } = useFinsightAuth()
  const [stories, setStories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function loadNews() {
      setLoading(true)
      setError(null)
      try {
        const response = await authedFetch(getToken, '/market-news', { cache: 'no-store' })
        const payload = await response.json().catch(() => ({}))
        if (!response.ok) {
          throw new Error(payload.detail || `HTTP ${response.status}`)
        }
        if (!cancelled) {
          setStories(payload.stories || [])
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : 'Unable to load news.')
          setStories([])
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadNews()
    return () => {
      cancelled = true
    }
  }, [getToken])

  return (
    <div className="bg-background px-3 py-5 sm:px-5 sm:py-7 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-[1520px]">
        <div className="mb-8 grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="terminal-panel px-6 py-6 sm:px-8 sm:py-8">
            <p className="terminal-label text-outline">Latest finance and trading coverage</p>
            <h1 className="mt-4 font-headline text-4xl font-extrabold uppercase tracking-tight text-slate-900 sm:text-[4rem]">
              Market News
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-8 text-slate-500">
              Brave News Search is pulling the latest 24-hour finance, trading, and stock market coverage into one feed.
            </p>
          </div>
          <div className="terminal-panel px-6 py-6">
            <p className="terminal-label text-outline">Feed status</p>
            <p className="mt-3 font-headline text-4xl font-bold text-slate-900">
              {loading ? '...' : stories.length}
            </p>
            <p className="mt-2 text-sm leading-7 text-slate-500">
              {loading ? 'Refreshing feed...' : 'articles loaded from the current 24-hour market news window.'}
            </p>
          </div>
        </div>

        {error && (
          <div className="terminal-surface-soft mb-6 px-5 py-4 text-sm text-[#9d4840]">
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading ? (
          <div className="terminal-panel px-6 py-10 text-sm text-slate-500">
            Loading latest market news...
          </div>
        ) : !stories.length ? (
          <div className="terminal-panel px-6 py-10">
            <p className="text-lg font-semibold text-slate-900">No news available.</p>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-500">
              The current feed did not return any finance articles. Try again in a few minutes.
            </p>
          </div>
        ) : (
          <div className="grid gap-5 xl:grid-cols-2">
            {stories.slice(0, 10).map((story, index) => (
              <button
                key={story.id || `${story.url}-${index}`}
                type="button"
                onClick={() => onOpenArticle(story)}
                className="terminal-panel block w-full p-6 text-left transition-colors hover:bg-white"
                style={{ borderLeft: `6px solid ${index % 4 === 0 ? '#1f8f54' : index % 4 === 1 ? '#2a63f6' : index % 4 === 2 ? '#f4c62a' : '#d14f59'}` }}
              >
                <div className="mb-3 flex flex-wrap items-center gap-3">
                  <span className="terminal-chip border-[#14181c] bg-[#14181c] px-3 py-1 text-[10px] text-white">
                    {story.source || 'Market news'}
                  </span>
                  {story.symbol && (
                    <span className="terminal-chip border-[#14181c] bg-[#eef3f6] px-3 py-1 text-[10px] text-slate-700">
                      {story.symbol}
                    </span>
                  )}
                  <span className="terminal-label text-outline">{formatArticleDate(story.datetime)}</span>
                </div>

                <h2 className="max-w-3xl font-headline text-2xl font-extrabold tracking-tight text-slate-900">
                  {story.title || 'Untitled article'}
                </h2>
                <p className="mt-4 text-sm leading-8 text-slate-600">
                  {story.summary || 'No summary available.'}
                </p>

                <div className="mt-5 flex items-center justify-between gap-3">
                  <span className="terminal-label text-outline">
                    {story.url ? 'Open article detail' : 'Story detail unavailable'}
                  </span>
                  <span className="material-symbols-outlined text-slate-500">arrow_outward</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
