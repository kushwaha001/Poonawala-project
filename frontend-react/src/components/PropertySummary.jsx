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
    <div className="glass rounded-2xl px-5 py-3 flex items-center gap-2 flex-wrap animate-fadeInUp mb-5">
      <span className="text-[0.62rem] text-slate-600 uppercase tracking-widest font-semibold mr-2">Subject Property</span>
      <div className="h-4 w-px bg-[#1a2035]" />
      {pills.map((p, i) => (
        <div key={i} className="flex items-center gap-1.5 bg-[#0a0e17] border border-[#1a2035] rounded-lg px-2.5 py-1">
          <p.icon size={11} className="text-slate-600" />
          <span className="text-[0.72rem] text-slate-300 capitalize">{p.text}</span>
        </div>
      ))}
    </div>
  )
}
