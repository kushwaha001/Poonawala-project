import Tooltip from './Tooltip'

const POI_META = {
  metro: { label: 'Metro / Rail', icon: '🚇', max: 5 },
  highway: { label: 'Highway', icon: '🛣️', max: 5 },
  school: { label: 'School', icon: '🏫', max: 3 },
  hospital: { label: 'Hospital', icon: '🏥', max: 5 },
  commercial: { label: 'Mall / Market', icon: '🛍️', max: 5 },
  it_park: { label: 'IT Park', icon: '🏢', max: 5 },
}

function DistBar({ label, icon, distance, max }) {
  const pct = Math.max(2, Math.min(100, (1 - distance / max) * 100))
  const color = distance <= 1 ? '#00d4aa' : distance <= 2.5 ? '#f59e0b' : '#ef4444'
  const glow = distance <= 1 ? 'rgba(0,212,170,0.25)' : distance <= 2.5 ? 'rgba(245,158,11,0.25)' : 'rgba(239,68,68,0.2)'
  return (
    <div className="hover-row flex items-center gap-3 py-2.5">
      <span className="text-lg w-7 text-center">{icon}</span>
      <span className="text-[0.82rem] font-medium w-30 shrink-0" style={{ color: 'var(--text2)' }}>{label}</span>
      <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg)' }}>
        <div className="h-full rounded-full transition-all duration-1000"
          style={{ width: `${pct}%`, background: color, boxShadow: `0 0 8px ${glow}` }} />
      </div>
      <span className="num text-[0.82rem] font-semibold w-14 text-right" style={{ color }}>{distance} km</span>
    </div>
  )
}

export default function POIChart({ poiBreakdown }) {
  if (!poiBreakdown) return null
  const entries = Object.entries(POI_META).map(([key, meta]) => ({
    ...meta, key, distance: poiBreakdown[`${key}_dist_km`] ?? poiBreakdown[key] ?? 5,
  }))

  return (
    <Tooltip id="infra_score">
      <div className="space-y-0.5">
        {entries.map(e => <DistBar key={e.key} label={e.label} icon={e.icon} distance={e.distance} max={e.max} />)}
      </div>
    </Tooltip>
  )
}
