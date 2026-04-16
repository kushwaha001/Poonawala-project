export default function ConfidenceRing({ value, size = 90, strokeWidth = 7 }) {
  const pct = Math.min(1, Math.max(0, value))
  const color = pct >= 0.85 ? '#8b5cf6' : pct >= 0.65 ? '#f59e0b' : '#ef4444'
  const label = pct >= 0.85 ? 'High' : pct >= 0.65 ? 'Medium' : pct >= 0.45 ? 'Low' : 'Unreliable'
  const r = (size - strokeWidth) / 2
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct)
  const center = size / 2

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="drop-shadow-lg">
        <defs>
          <filter id="ringGlow">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <circle cx={center} cy={center} r={r} fill="none" stroke="#111827" strokeWidth={strokeWidth} />
        <circle cx={center} cy={center} r={r} fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={offset}
          transform={`rotate(-90 ${center} ${center})`} filter="url(#ringGlow)"
          style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.4,0,0.2,1)' }} />
        <text x={center} y={center - 4} textAnchor="middle" fill={color} fontSize="20" fontWeight="800"
          fontFamily="'JetBrains Mono', monospace">{Math.round(pct * 100)}%</text>
        <text x={center} y={center + 14} textAnchor="middle" fill="#64748b" fontSize="9" fontWeight="500">{label}</text>
      </svg>
    </div>
  )
}
