import { useState } from 'react'
import Chat from './pages/Chat'
import Portfolio from './pages/Portfolio'

const TABS = ['Chat', 'Portfolio']

export default function App() {
  const [tab, setTab] = useState('Chat')

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-800 px-6 py-3 flex items-center gap-3">
        <span className="text-blue-400 font-bold text-xl tracking-tight">FinSight</span>
        <span className="text-gray-500 text-sm">Natural Language Analytics Engine</span>
        <span className="ml-auto text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">Phase 4 — Portfolio & Deploy</span>
      </header>

      <nav className="border-b border-gray-800 px-6 flex gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            {t}
          </button>
        ))}
      </nav>

      <main className="flex-1">
        {tab === 'Chat' && <Chat />}
        {tab === 'Portfolio' && <Portfolio />}
      </main>
    </div>
  )
}
