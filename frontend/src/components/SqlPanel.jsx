import { useState } from 'react'

export default function SqlPanel({ sql, path }) {
  const [open, setOpen] = useState(false)

  if (!sql) return null

  return (
    <div className="border border-outline/15 bg-white shadow-[0_1px_0_rgba(0,0,0,0.02)]">
      <button
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-surface-container-low"
      >
        <span className="flex items-center gap-2">
          <span className="terminal-label text-slate-700">Generated SQL</span>
          <span className="terminal-chip">{path === 'hot' ? 'Live route' : 'Gold route'}</span>
        </span>
        <span className="terminal-label text-outline">{open ? 'Hide' : 'Show'}</span>
      </button>
      {open && (
        <pre className="overflow-x-auto border-t border-outline/15 bg-surface-container-lowest px-4 py-4 text-xs leading-6 text-slate-700">
          {sql}
        </pre>
      )}
    </div>
  )
}
