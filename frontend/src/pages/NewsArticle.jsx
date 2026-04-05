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
        <div className="terminal-shell">
          <div className="terminal-surface px-6 py-8 sm:px-8 sm:py-10">
          <p className="font-headline text-3xl font-bold text-slate-900">No article selected</p>
          <p className="mt-3 text-sm leading-7 text-slate-500">
            Go back to Markets and select a story from the news rail.
          </p>
          <button
            type="button"
            onClick={onBack}
            className="terminal-button mt-6 px-5 py-3"
          >
            Back to Markets
          </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background px-3 py-4 sm:px-6 sm:py-8 lg:px-8 lg:py-10">
      <div className="terminal-shell space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="terminal-button-ghost inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700"
          >
            <span className="material-symbols-outlined text-[18px]">arrow_back</span>
            Back to Markets
          </button>
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="terminal-button inline-flex items-center gap-2 px-4 py-2 text-sm"
            >
              <span className="material-symbols-outlined text-[18px]">open_in_new</span>
              Read Full Article
            </a>
          )}
        </div>

        <article className="terminal-surface px-5 py-6 sm:px-10 sm:py-10">
          <div className="mb-8 flex flex-wrap items-center gap-3">
            <span className="terminal-chip border-[#14181c] bg-[#14181c] px-3 py-1 text-[10px] text-white">
              {article.source || 'News'}
            </span>
            <span className="terminal-chip border-[#14181c] bg-[#eef3f6] px-3 py-1 text-[10px] text-slate-700">
              {article.symbol}
            </span>
            <span className="terminal-label text-outline">{formatArticleDate(article.datetime)}</span>
          </div>

          <h1 className="max-w-4xl font-headline text-[2.2rem] font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            {formatArticleTitle(article.title)}
          </h1>

          <div className="terminal-surface-soft mt-10 px-6 py-5">
            <p className="terminal-label text-outline">Article summary</p>
            <p className="mt-3 text-sm leading-8 text-slate-600">
              {article.summary || 'No summary available.'}
            </p>
          </div>

          <div className="mt-8 space-y-5">
            <p className="terminal-label text-outline">Full article</p>
            {buildArticleParagraphs(article).map((paragraph, index) => (
              <p key={`${paragraph.slice(0, 24)}-${index}`} className="max-w-4xl text-[15px] leading-8 text-slate-700 sm:text-base sm:leading-9">
                {paragraph}
              </p>
            ))}
            {article.url && (
              <div className="pt-4">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="terminal-button inline-flex items-center gap-2 px-4 py-2 text-sm"
                >
                  <span className="material-symbols-outlined text-[18px]">open_in_new</span>
                  Open Original Source
                </a>
              </div>
            )}
          </div>
        </article>
      </div>
    </div>
  )
}
