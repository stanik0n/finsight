function formatArticleDate(value) {
  if (!value) return 'Latest'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'America/Chicago',
    timeZoneName: 'short',
  })
}

function formatArticleTitle(value) {
  if (!value) return 'Untitled article'
  return value
    .replace(/\s*-\s*(OilPrice\.com|Market Commentary|News Commentary).*$/i, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function buildArticleParagraphs(article) {
  const raw = (article?.body_text || article?.summary || '')
    .replace(/\s+/g, ' ')
    .replace(/\s*\.\.\.\s*/g, '... ')
    .trim()

  if (!raw) return []

  const cleaned = raw
    .replace(/Companies mentioned in this release include:\s*/gi, '\n\nCompanies mentioned: ')
    .replace(/\)\s*,/g, '),')
    .replace(/([a-z])([A-Z][a-z])/g, '$1 $2')

  const sentenceChunks = cleaned
    .split(/(?<=[.!?])\s+(?=[A-Z(])/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)

  const paragraphs = []
  let current = []

  for (const chunk of sentenceChunks) {
    current.push(chunk)
    const currentText = current.join(' ')
    const shouldBreak =
      current.length >= 3 ||
      currentText.length > 360 ||
      /Companies mentioned:/i.test(chunk)

    if (shouldBreak) {
      paragraphs.push(currentText)
      current = []
    }
  }

  if (current.length) {
    paragraphs.push(current.join(' '))
  }

  return paragraphs
}

export default function NewsArticle({ article, onBack }) {
  if (!article) {
    return (
      <div className="min-h-screen bg-background px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10">
        <div className="mx-auto max-w-5xl rounded-xl bg-white px-6 py-8 shadow-sm sm:px-8 sm:py-10">
          <p className="font-headline text-3xl font-bold text-slate-900">No article selected</p>
          <p className="mt-3 text-sm leading-7 text-slate-500">
            Go back to Markets and select a story from the news rail.
          </p>
          <button
            type="button"
            onClick={onBack}
            className="mt-6 rounded-lg bg-slate-800 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-slate-900"
          >
            Back to Markets
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10">
      <div className="mx-auto max-w-5xl space-y-6">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-lg border border-outline/15 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-surface-container-low"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span>
          Back to Markets
        </button>

        <article className="rounded-2xl bg-white px-6 py-8 shadow-sm sm:px-10 sm:py-10">
          <div className="mb-8 flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
              {article.source || 'News'}
            </span>
            <span className="rounded-full bg-surface-container-low px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-700">
              {article.symbol}
            </span>
            <span className="terminal-label text-outline">{formatArticleDate(article.datetime)}</span>
          </div>

          <h1 className="max-w-4xl font-headline text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            {formatArticleTitle(article.title)}
          </h1>

          <div className="mt-10 rounded-xl bg-surface-container-low px-6 py-5">
            <p className="terminal-label text-outline">Article summary</p>
            <p className="mt-3 text-sm leading-8 text-slate-600">
              {article.summary || 'No summary available.'}
            </p>
          </div>

          <div className="mt-8 space-y-5">
            <p className="terminal-label text-outline">Full article</p>
            {buildArticleParagraphs(article).map((paragraph, index) => (
              <p key={`${paragraph.slice(0, 24)}-${index}`} className="max-w-4xl text-base leading-9 text-slate-700">
                {paragraph}
              </p>
            ))}
          </div>
        </article>
      </div>
    </div>
  )
}
