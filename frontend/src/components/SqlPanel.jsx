import { useState } from 'react'

export default function SqlPanel({ sql, path }) {
  const [open, setOpen] = useState(false)

  if (!sql) return null

  return (
    <div className="border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-900 text-sm hover:bg-gray-800 transition"
      >
        <span className="flex items-center gap-2 text-gray-400">
          <span className="text-green-400 font-mono text-xs">SQL</span>
          Generated query
          <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${
            path === 'hot'
              ? 'bg-orange-900 text-orange-300'
              : 'bg-blue-900 text-blue-300'
          }`}>
            {path === 'hot' ? '⚡ Hot' : '❄ Cold'}
          </span>
        </span>
        <span className="text-gray-600 text-xs">{open ? '▲ hide' : '▼ show'}</span>
      </button>
      {open && (
        <pre className="px-4 py-3 bg-gray-950 text-sm font-mono text-green-300 overflow-x-auto whitespace-pre-wrap">
          {sql}
        </pre>
      )}
    </div>
  )
}
