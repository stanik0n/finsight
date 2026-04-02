export default function ResultsTable({ results }) {
  if (!results || results.length === 0) {
    return <p className="py-6 text-center text-sm text-slate-500">No results returned.</p>
  }

  const columns = Object.keys(results[0])

  function fmt(value) {
    if (value === null || value === undefined) return <span className="text-slate-300">-</span>
    if (typeof value === 'boolean') return value ? 'Yes' : 'No'
    if (typeof value === 'number') return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2)
    return String(value)
  }

  return (
    <div className="overflow-x-auto border border-outline/15 bg-white shadow-[0_1px_0_rgba(0,0,0,0.02)]">
      <table className="w-full min-w-[640px] text-left">
        <thead>
          <tr className="border-b border-outline/15 bg-surface-container-lowest">
            {columns.map((column) => (
              <th key={column} className="px-4 py-3 terminal-label text-outline">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className="border-b border-outline/10 transition-colors hover:bg-surface-container-lowest"
            >
              {columns.map((column) => (
                <td key={column} className="px-4 py-3 text-xs text-slate-700">
                  {fmt(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="border-t border-outline/10 bg-surface-container-lowest px-4 py-2 terminal-label text-outline">
        {results.length} row{results.length === 1 ? '' : 's'}
      </div>
    </div>
  )
}
