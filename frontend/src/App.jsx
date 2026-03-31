import Chat from './pages/Chat'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-800 px-6 py-3 flex items-center gap-3">
        <span className="text-blue-400 font-bold text-xl tracking-tight">FinSight</span>
        <span className="text-gray-500 text-sm">Natural Language Analytics Engine</span>
        <span className="ml-auto text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">Phase 2 — Intelligence Layer</span>
      </header>
      <main className="flex-1">
        <Chat />
      </main>
    </div>
  )
}
