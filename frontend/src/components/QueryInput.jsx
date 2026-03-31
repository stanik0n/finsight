export default function QueryInput({ onSubmit, loading }) {
  function handleSubmit(e) {
    e.preventDefault()
    const q = e.target.question.value.trim()
    if (q) onSubmit(q)
  }

  const examples = [
    'Which tech stocks had the highest RSI last week?',
    'Show me energy stocks with volume spikes in the last 30 days',
    'Which stocks closed above their 50-day SMA yesterday?',
    'What were the top 5 gainers in Healthcare this month?',
  ]

  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          name="question"
          type="text"
          placeholder="Ask about any stock or sector..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
          disabled={loading}
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
        >
          {loading ? 'Querying…' : 'Ask'}
        </button>
      </form>

      <div className="flex flex-wrap gap-2">
        {examples.map((ex) => (
          <button
            key={ex}
            onClick={() => onSubmit(ex)}
            disabled={loading}
            className="text-xs px-3 py-1.5 rounded-full border border-gray-700 hover:border-blue-500 hover:text-blue-400 text-gray-400 transition disabled:opacity-40"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  )
}
