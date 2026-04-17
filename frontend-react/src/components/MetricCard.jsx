import Tooltip from './Tooltip'
import AnimatedNumber from './AnimatedNumber'

const accents = {
  teal: 'accent-top-teal neon-teal',
  amber: 'accent-top-amber neon-amber',
  red: 'accent-top-red neon-red',
  blue: 'accent-top-blue neon-blue',
  purple: 'accent-top-purple neon-purple',
}
const textColors = {
  teal: 'text-[#00ffcc]',
  amber: 'text-[#ffb800]',
  red: 'text-[#ff4757]',
  blue: 'text-[#5b8cff]',
  purple: 'text-[#a78bfa]',
}

export default function MetricCard({ icon, label, value, sub, color = 'teal', tooltipId, numValue, numFormat, delay = 0 }) {
  const Icon = icon
  return (
    <div className={`glass accent-top ${accents[color]} rounded-2xl p-5 hover:-translate-y-1.5 hover:scale-[1.02] transition-all duration-300 animate-fadeInUp opacity-0`}
         style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}>
      <Tooltip id={tooltipId}>
        <div className="flex items-center gap-2 mb-3">
          <Icon size={13} className="text-slate-600" />
          <span className="text-[0.58rem] text-slate-500 uppercase tracking-[0.14em] font-semibold">{label}</span>
        </div>
      </Tooltip>
      <div className={`text-[1.4rem] font-bold leading-tight ${textColors[color]}`}>
        {numValue !== undefined ? <AnimatedNumber value={numValue} format={numFormat} className={textColors[color]} /> : value}
      </div>
      {sub && <div className="text-[0.7rem] text-slate-500 mt-1.5">{sub}</div>}
    </div>
  )
}
