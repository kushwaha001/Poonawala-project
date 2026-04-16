import Tooltip from './Tooltip'
import AnimatedNumber from './AnimatedNumber'

const accents = {
  teal:   'accent-top-teal neon-teal',
  amber:  'accent-top-amber neon-amber',
  red:    'accent-top-red neon-red',
  blue:   'accent-top-blue neon-blue',
  purple: 'accent-top-purple neon-purple',
}
const gradients = {
  teal:   'grad-teal',
  amber:  'grad-amber',
  red:    'grad-red',
  blue:   'grad-blue',
  purple: 'grad-purple',
}

export default function MetricCard({ icon, label, value, sub, color = 'teal', tooltipId, numValue, numFormat, delay = 0 }) {
  const Icon = icon
  return (
    <div
      className={`glass accent-top ${accents[color]} rounded-2xl p-5 hover:-translate-y-2 hover:scale-[1.03] transition-all duration-300 animate-fadeInUp opacity-0`}
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'forwards' }}
    >
      <Tooltip id={tooltipId}>
        <div className="flex items-center gap-2 mb-3">
          <Icon size={14} className="text-slate-500" />
          <span className="text-[0.65rem] text-slate-400 uppercase tracking-[0.16em] font-bold">{label}</span>
        </div>
      </Tooltip>
      <div className={`text-[1.75rem] font-extrabold leading-tight ${gradients[color]}`}>
        {numValue !== undefined
          ? <AnimatedNumber value={numValue} format={numFormat} className={gradients[color]} />
          : value}
      </div>
      {sub && <div className="text-[0.78rem] text-slate-500 mt-2 font-medium">{sub}</div>}
    </div>
  )
}
