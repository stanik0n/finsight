export default function CommentaryPanel({ commentary }) {
  if (!commentary) return null

  return (
    <div className="border-l border-primary/35 bg-surface-container px-5 py-5">
      <div className="mb-3 flex items-center gap-2">
        <span className="h-1.5 w-1.5 bg-primary" />
        <span className="terminal-label text-slate-700">Analyst Commentary</span>
      </div>
      <p className="text-sm leading-7 text-slate-600">{commentary}</p>
    </div>
  )
}
