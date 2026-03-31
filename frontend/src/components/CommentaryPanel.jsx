export default function CommentaryPanel({ commentary }) {
  if (!commentary) return null

  return (
    <div className="rounded-lg border border-blue-900 bg-blue-950/30 px-4 py-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs px-2 py-0.5 rounded bg-blue-900 text-blue-300 font-mono">Analysis</span>
      </div>
      <p className="text-gray-300 text-sm leading-relaxed">{commentary}</p>
    </div>
  )
}
