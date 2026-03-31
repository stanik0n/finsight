export default function ResultsTable({ results }) {
  if (!results || results.length === 0) {
    return <p className="text-gray-500 text-sm text-center py-6">No results returned.</p>
  }

  const columns = Object.keys(results[0])

  // Format cell values for display
  function fmt(val) {
    if (val === null || val === undefined) return <span className="text-gray-600">—</span>
    if (typeof val === 'boolean') return val
      ? <span className="text-green-400">✓</span>
      : <span className="text-gray-600">✗</span>
    if (typeof val === 'number') {
      if (Number.isInteger(val)) return val.toLocaleString()
      return val.toFixed(2)
    }
    return String(val)
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-900 border-b border-gray-800">
            {columns.map((col) => (
              <th
                key={col}
                className="text-left px-4 py-2.5 text-xs font-medium text-gray-400 uppercase tracking-wider whitespace-nowrap"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.map((row, i) => (
            <tr
              key={i}
              className={`border-b border-gray-800 hover:bg-gray-900 transition ${
                i % 2 === 0 ? '' : 'bg-gray-950'
              }`}
            >
              {columns.map((col) => (
                <td key={col} className="px-4 py-2.5 text-gray-300 whitespace-nowrap font-mono text-xs">
                  {fmt(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="px-4 py-2 bg-gray-900 text-xs text-gray-500 border-t border-gray-800">
        {results.length} row{results.length !== 1 ? 's' : ''}
      </div>
    </div>
  )
}
