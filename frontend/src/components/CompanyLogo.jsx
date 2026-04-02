const LOGO_DEV_TOKEN = import.meta.env.VITE_LOGO_DEV_TOKEN

function initialsFor(symbol = '') {
  return symbol.toUpperCase().slice(0, 4)
}

function buildLogoUrl(symbol, size) {
  if (!LOGO_DEV_TOKEN || !symbol) return null
  const ticker = encodeURIComponent(symbol.toUpperCase())
  const params = new URLSearchParams({
    token: LOGO_DEV_TOKEN,
    size: String(size),
    format: 'png',
    retina: 'true',
    fallback: 'monogram',
  })
  return `https://img.logo.dev/ticker/${ticker}?${params.toString()}`
}

export default function CompanyLogo({ symbol, alt, size = 40, className = '' }) {
  const url = buildLogoUrl(symbol, size * 2)
  const fallbackText = initialsFor(symbol)
  const shape = {
    width: `${size}px`,
    height: `${size}px`,
  }

  if (!url) {
    return (
      <div
        className={`flex items-center justify-center bg-surface-container-low terminal-label text-slate-700 ${className}`.trim()}
        style={shape}
        aria-label={alt || `${symbol} logo`}
      >
        {fallbackText}
      </div>
    )
  }

  return (
    <div
      className={`overflow-hidden border border-outline/10 bg-white ${className}`.trim()}
      style={shape}
    >
      <img
        src={url}
        alt={alt || `${symbol} logo`}
        width={size}
        height={size}
        loading="lazy"
        className="h-full w-full object-contain p-1"
        onError={(event) => {
          event.currentTarget.style.display = 'none'
          const parent = event.currentTarget.parentElement
          if (parent) {
            parent.className = `flex items-center justify-center bg-surface-container-low terminal-label text-slate-700 ${className}`.trim()
            parent.textContent = fallbackText
          }
        }}
      />
    </div>
  )
}
