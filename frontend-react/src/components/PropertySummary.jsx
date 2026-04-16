import { Building2, MapPin, Calendar, Ruler, Lock, Home } from 'lucide-react'

export default function PropertySummary({ input }) {
  if (!input) return null
  const pills = [
    { icon: MapPin, text: input.address },
    { icon: Building2, text: `${input.configuration || ''} ${input.sub_type}`.trim() },
    { icon: Ruler, text: `${input.built_up_area_sqft} sqft` },
    { icon: Calendar, text: `${input.age_years} years old` },
    input.ownership && { icon: Lock, text: input.ownership },
    input.floor != null && input.floor >= 0 && { icon: Home, text: `Floor ${input.floor}/${input.total_floors || '?'}` },
  ].filter(Boolean)

  return (
    <div className="glass rounded-2xl px-5 py-3.5 flex items-center gap-2.5 flex-wrap animate-fadeInUp mb-5">
      <span className="grad-teal text-[0.65rem] uppercase tracking-[0.16em] font-bold mr-1">Subject Property</span>
      <div className="h-4 w-px" style={{ background: 'var(--border-h)' }} />
      {pills.map((p, i) => (
        <div key={i} className="flex items-center gap-1.5 rounded-lg px-3 py-1.5" style={{ background: 'rgba(0,255,204,0.04)', border: '1px solid rgba(0,255,204,0.12)' }}>
          <p.icon size={12} className="text-teal-500" />
          <span className="text-[0.78rem] font-medium capitalize" style={{ color: 'var(--text2)' }}>{p.text}</span>
        </div>
      ))}
    </div>
  )
}
