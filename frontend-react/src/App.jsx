import { useState, useEffect } from 'react'
import {
  Building2, Shield, TrendingUp, AlertTriangle, ChevronDown,
  MapPin, Clock, Target, Gauge, BarChart3, Brain, CheckCircle2,
  Activity, Landmark, Info, Zap, ArrowUpRight, ArrowDownRight,
  FileText, Home, Menu, X, Sparkles, Sun, Moon, Download
} from 'lucide-react'
import MetricCard from './components/MetricCard'
import Tooltip from './components/Tooltip'
import AnimatedNumber from './components/AnimatedNumber'
import ConfidenceRing from './components/ConfidenceRing'
import PropertySummary from './components/PropertySummary'
import POIChart from './components/POIChart'

const LOCALITIES = {
  Pune: ['Baner', 'Hinjewadi', 'Kothrud'],
  Mumbai: ['Andheri West', 'Bandra West', 'Dadar'],
  Bangalore: ['Whitefield'],
  Nagpur: ['Sitabuldi'],
  Jaipur: ['Malviya Nagar'],
  Lucknow: ['Gomti Nagar'],
  Gorakhpur: ['Civil Lines', 'Golghar'],
}

const fmt = (n) => {
  if (!n && n !== 0) return '—'
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${n?.toLocaleString('en-IN')}`
}
const fmtNum = (n) => fmt(Math.round(n))
const safe = (v, fallback = '—') => (v !== undefined && v !== null && v !== '') ? v : fallback
const toLabel = (value) => String(value || '—').replace(/_/g, ' ')

const NUMERIC_RULES = {
  area:               { min: 100,  max: 100000,     integer: false, step: '0.01' },
  age:                { min: 0,    max: 120,         integer: true,  step: '1'    },
  floor:              { min: 0,    max: 300,         integer: true,  step: '1'    },
  total_floors:       { min: 0,    max: 300,         integer: true,  step: '1'    },
  rent:               { min: 0,    max: 10000000,    integer: false, step: '0.01' },
  loan_amount:        { min: 0,    max: 1000000000,  integer: false, step: '1'    },
  approved_plan_area: { min: 0,    max: 100000,      integer: false, step: '0.01' },
  vacancy_rate:       { min: 0,    max: 50,          integer: false, step: '0.1'  },
  opex_ratio:         { min: 0,    max: 60,          integer: false, step: '0.1'  },
}

const sanitizeNumericInput = (raw, { integer = false } = {}) => {
  const cleaned = String(raw ?? '').replace(/[^\d.]/g, '')
  if (!cleaned) return ''
  const parts = cleaned.split('.')
  const whole = parts[0]
  if (integer) return whole
  const decimal = parts.slice(1).join('')
  return decimal ? `${whole}.${decimal}` : whole
}

const clampNumericValue = (raw, { min, max, integer = false } = {}) => {
  if (raw === '' || raw === null || raw === undefined) return ''
  const parsed = Number.parseFloat(raw)
  if (!Number.isFinite(parsed)) return ''
  const rounded = integer ? Math.round(parsed) : parsed
  const bounded = Math.min(max ?? rounded, Math.max(min ?? rounded, rounded))
  return integer ? String(Math.trunc(bounded)) : String(Number(bounded.toFixed(2)))
}

const parseNullableNumber = (value) => {
  if (value === '' || value === null || value === undefined) return null
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) ? parsed : null
}

/* ─── Numbered Section ─── */
function Section({ num, title, icon, badge, badgeColor = 'teal', children, defaultOpen = true }) {
  const Icon = icon
  const [open, setOpen] = useState(defaultOpen)
  const bc = {
    teal:   'bg-emerald-500/15 text-emerald-300 border border-emerald-500/20',
    amber:  'bg-amber-500/15 text-amber-300 border border-amber-500/20',
    red:    'bg-red-500/15 text-red-300 border border-red-500/20',
    blue:   'bg-blue-500/15 text-blue-300 border border-blue-500/20',
    purple: 'bg-purple-500/15 text-purple-300 border border-purple-500/20',
  }
  return (
    <div className="glass rounded-2xl overflow-hidden print-section" style={{ pageBreakInside: 'avoid' }}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-5 py-4 no-print-collapse">
        <div className="flex items-center gap-3 min-w-0">
          {num && (
            <span className="num text-[0.68rem] font-bold w-6 h-6 rounded-full shrink-0 flex items-center justify-center"
              style={{ background: 'var(--bg)', border: '1px solid var(--border-h)', color: 'var(--text3)' }}>{num}</span>
          )}
          <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center transition-all"
            style={{ background: open ? 'rgba(0,212,170,0.1)' : 'var(--bg)', border: '1px solid', borderColor: open ? 'rgba(0,212,170,0.2)' : 'transparent' }}>
            <Icon size={15} className={`transition-colors ${open ? 'text-teal-400' : 'text-slate-600'}`} />
          </div>
          <span className="text-[0.95rem] font-bold truncate" style={{ color: 'var(--text)' }}>{title}</span>
          {badge && <span className={`text-[0.62rem] font-bold uppercase tracking-widest px-2.5 py-0.5 rounded-full shrink-0 ${bc[badgeColor]}`}>{badge}</span>}
        </div>
        <ChevronDown size={16} className={`text-slate-500 shrink-0 ml-3 transition-transform duration-300 no-print ${open ? 'rotate-180' : ''}`} />
      </button>
      <div className={`accordion-body ${open ? 'open' : ''}`}>
        <div className="accordion-inner">
          <div className="px-5 pb-5">{children}</div>
        </div>
      </div>
    </div>
  )
}

/* ─── Stat Row ─── */
function StatRow({ label, value, tooltipId, color, highlight }) {
  const row = (
    <div className="hover-row flex items-center justify-between py-3" style={{ borderBottom: '1px solid var(--border)' }}>
      <span className="text-[0.82rem]" style={{ color: 'var(--text3)' }}>{label}</span>
      <span className={`num text-[0.88rem] font-semibold ${color || ''}`}
        style={!color ? { color: highlight ? '#00ffcc' : 'var(--text)' } : undefined}>
        {safe(value)}
      </span>
    </div>
  )
  return tooltipId ? <Tooltip id={tooltipId} wrapperClassName="block w-full cursor-help">{row}</Tooltip> : row
}

/* ─── Factor Row ─── */
function FactorRow({ label, value, impact, tooltipId }) {
  const impactNum = parseFloat(impact) || ((value - 1) * 100)
  const isPos = impactNum >= 0
  const barW = Math.min(80, Math.abs(impactNum) * 1.1)
  return (
    <Tooltip id={tooltipId} wrapperClassName="block w-full cursor-help">
      <div className="hover-row flex items-center gap-3 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <span className="text-[0.82rem] w-48 shrink-0" style={{ color: 'var(--text3)' }}>{label}</span>
        <span className="num text-[0.84rem] font-bold w-16 text-center" style={{ color: 'var(--text)' }}>{safe(value)}</span>
        <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg)' }}>
          <div className={`h-full rounded-full ${isPos ? 'bg-gradient-to-r from-emerald-500 to-teal-300' : 'bg-gradient-to-r from-red-500 to-orange-400'}`}
            style={{ width: `${barW}%`, transition: 'width 1s ease' }} />
        </div>
        <span className={`num text-[0.82rem] font-bold w-16 text-right ${isPos ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPos ? '+' : ''}{impactNum.toFixed(1)}%
        </span>
      </div>
    </Tooltip>
  )
}

/* ─── Agent badge colours ─── */
const AGENT_COLORS = {
  location_intel:       { bg: 'rgba(56,189,248,0.12)',  border: 'rgba(56,189,248,0.35)',  text: '#38bdf8', label: 'Location Intel'     },
  property_char:        { bg: 'rgba(245,158,11,0.12)',  border: 'rgba(245,158,11,0.35)',  text: '#f59e0b', label: 'Property'           },
  legal:                { bg: 'rgba(16,185,129,0.12)',  border: 'rgba(16,185,129,0.35)',  text: '#10b981', label: 'Legal'              },
  macro_context:        { bg: 'rgba(167,139,250,0.12)', border: 'rgba(167,139,250,0.35)', text: '#a78bfa', label: 'Macro'              },
  market_dynamics:      { bg: 'rgba(251,146,60,0.12)',  border: 'rgba(251,146,60,0.35)',  text: '#fb923c', label: 'Market'             },
  fraud:                { bg: 'rgba(251,113,133,0.12)', border: 'rgba(251,113,133,0.35)', text: '#fb7185', label: 'Fraud'              },
  comparable_analysis:  { bg: 'rgba(99,102,241,0.12)',  border: 'rgba(99,102,241,0.35)',  text: '#6366f1', label: 'Comparable'         },
}
const DRIVER_DESC = {
  market_to_circle_ratio:    'Real transaction premium over the govt. circle rate — the single largest valuation driver.',
  micro_location_adjustment: 'Fine-grain POI proximity vs. expected for this micro-bucket, powered by live OSM data.',
  age_depreciation:          'Non-linear structure decay; land value preserved. LLM condition-adjusts ±5%.',
  config_factor:             'Penalty for non-standard unit size vs. locality modal area. Standard units sell faster.',
  legal_factor:              'Ownership type and title clarity discount. Freehold + clear title = 1.00.',
  floor_factor:              'Floor-level premium/penalty. Ground shops highest; high floors without lift discounted.',
  regulatory_compliance:     'India-specific multiplicative haircut for OC, litigation, attachment, and RERA gaps.',
  macro_economic_adjustment: 'Overlay of RBI repo rate, market cycle position, and seasonal demand on base value.',
}

/* ─── Driver Bar ─── */
function DriverBar({ name, impact, agent, index }) {
  const val = parseFloat(impact)
  const isPos = val >= 0
  const w = Math.min(85, Math.abs(val) * 1.1)
  const ac = AGENT_COLORS[agent] || { bg: 'rgba(100,100,100,0.10)', border: 'rgba(100,100,100,0.25)', text: 'var(--text4)', label: toLabel(agent) }
  const desc = DRIVER_DESC[name]
  return (
    <Tooltip id={name}>
      <div className="hover-row py-3 px-1" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-3">
          {/* Factor name + agent badge */}
          <div className="w-52 shrink-0 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[0.84rem] font-semibold capitalize" style={{ color: 'var(--text1)' }}>{name.replace(/_/g, ' ')}</span>
              <span className="text-[0.6rem] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full shrink-0"
                style={{ background: ac.bg, border: `1px solid ${ac.border}`, color: ac.text }}>
                {ac.label}
              </span>
            </div>
            {desc && <p className="text-[0.68rem] mt-0.5 leading-snug" style={{ color: 'var(--text3)' }}>{desc}</p>}
          </div>
          {/* Bar */}
          <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg)' }}>
            <div className={`h-full rounded-full ${isPos ? 'bg-gradient-to-r from-emerald-500 to-teal-300' : 'bg-gradient-to-r from-red-500 to-orange-400'}`}
              style={{ width: `${w}%`, transition: 'width 1.2s cubic-bezier(0.4,0,0.2,1)', transitionDelay: `${index * 100}ms` }} />
          </div>
          {/* Impact value */}
          <span className={`num text-[0.84rem] font-bold w-16 text-right shrink-0 ${isPos ? 'text-emerald-400' : 'text-red-400'}`}>
            {isPos ? <ArrowUpRight size={12} className="inline mr-0.5 -mt-0.5" /> : <ArrowDownRight size={12} className="inline mr-0.5 -mt-0.5" />}
            {impact}
          </span>
        </div>
      </div>
    </Tooltip>
  )
}

/* ─── Fraud Flag ─── */
function FraudFlag({ flag, severity, explanation, source }) {
  const cfg = {
    high: { border: 'border-l-red-500', bg: 'bg-red-950/40', badge: 'bg-red-500 text-white' },
    medium: { border: 'border-l-amber-500', bg: 'bg-amber-950/30', badge: 'bg-amber-500 text-black' },
    low: { border: 'border-l-blue-500', bg: 'bg-blue-950/30', badge: 'bg-blue-500 text-white' },
  }
  const c = cfg[severity] || cfg.low
  return (
    <div className={`border-l-[3px] ${c.border} ${c.bg} rounded-r-xl p-4 mb-3 hover:translate-x-1 transition-transform`}>
      <div className="flex items-start gap-3">
        <span className={`text-[0.55rem] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-md ${c.badge} shrink-0`}>{severity}</span>
        <div className="min-w-0">
          <h4 className="text-[0.82rem] font-semibold capitalize">{(flag || '').replace(/_/g, ' ')}</h4>
          <p className="text-[0.72rem] mt-1 leading-relaxed" style={{ color: 'var(--text3)' }}>{explanation || `Detected by ${source} agent`}</p>
          <span className="text-[0.6rem] mt-2 inline-block" style={{ color: 'var(--text4)' }}>Source: {source} agent</span>
        </div>
      </div>
    </div>
  )
}

/* ─── RPI Arc Gauge ─── */
function ArcGauge({ value, size = 155 }) {
  const color = value >= 60 ? '#00d4aa' : value >= 40 ? '#f59e0b' : '#ef4444'
  const label = value >= 80 ? 'Highly Liquid' : value >= 60 ? 'Moderately Liquid' : value >= 40 ? 'Restricted' : value >= 20 ? 'Illiquid' : 'Unsellable'
  const r = size * 0.34, circ = 2 * Math.PI * r, arcLen = circ * 0.75, offset = arcLen * (1 - value / 100)
  const cx = size / 2, cy = size / 2 + 5
  return (
    <Tooltip id="rpi">
      <div className="flex flex-col items-center">
        <svg width={size} height={size * 0.72} viewBox={`0 0 ${size} ${size * 0.72}`}>
          <defs><filter id="arcGlow"><feGaussianBlur stdDeviation="3" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
          <path d={`M ${cx - r * 0.95} ${cy + r * 0.31} A ${r} ${r} 0 1 1 ${cx + r * 0.95} ${cy + r * 0.31}`} fill="none" stroke="#0d1220" strokeWidth="9" strokeLinecap="round" />
          <path d={`M ${cx - r * 0.95} ${cy + r * 0.31} A ${r} ${r} 0 1 1 ${cx + r * 0.95} ${cy + r * 0.31}`} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round" filter="url(#arcGlow)"
            strokeDasharray={arcLen} strokeDashoffset={offset} style={{ transition: 'stroke-dashoffset 1.8s cubic-bezier(0.4,0,0.2,1)' }} />
          <text x={cx} y={cy - 2} textAnchor="middle" fill={color} fontSize="26" fontWeight="800" fontFamily="'JetBrains Mono',monospace">{value}</text>
          <text x={cx} y={cy + 14} textAnchor="middle" fill="#475569" fontSize="8.5">{label}</text>
        </svg>
      </div>
    </Tooltip>
  )
}

/* ─── Select Field ─── */
function Sel({ label, id, options, value, onChange }) {
  return (
    <div>
      <label className="block text-[0.68rem] mb-1.5 font-bold uppercase tracking-[0.12em]" style={{ color: 'var(--text4)' }}>{label}</label>
      <select value={value} onChange={e => onChange(id, e.target.value)}
        className="w-full rounded-xl px-3 py-2.5 text-[0.88rem] focus:outline-none transition-all"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text)' }}>
        {options.map(o => <option key={typeof o === 'string' ? o : o.v} value={typeof o === 'string' ? o : o.v}>{typeof o === 'string' ? o : o.l}</option>)}
      </select>
    </div>
  )
}

/* ─── Numeric Input Field ─── */
function Inp({ label, id, value, onChange, onBlur, rule = {} }) {
  return (
    <div>
      <label className="block text-[0.68rem] mb-1.5 font-bold uppercase tracking-[0.12em]" style={{ color: 'var(--text4)' }}>{label}</label>
      <input
        type="text"
        inputMode={rule.integer ? 'numeric' : 'decimal'}
        pattern={rule.integer ? '[0-9]*' : '[0-9]*[.]?[0-9]*'}
        min={rule.min}
        max={rule.max}
        step={rule.step || 'any'}
        value={value}
        onChange={e => onChange(id, e.target.value)}
        onBlur={() => onBlur(id)}
        className="w-full rounded-xl px-3 py-2.5 text-[0.92rem] num focus:outline-none transition-all"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text)' }}
      />
    </div>
  )
}

/* ─── Sidebar Section Divider ─── */
function SbDiv({ label }) {
  return (
    <div className="flex items-center gap-2 pt-1 pb-1">
      <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
      <span className="text-[0.55rem] uppercase tracking-[0.18em] font-bold shrink-0" style={{ color: 'var(--text4)' }}>{label}</span>
      <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
    </div>
  )
}

/* ─── Status Badge pill for Legal fields ─── */
function StatusBadge({ val }) {
  if (val === true)  return <span className="text-[0.7rem] font-bold text-emerald-400">✓ Yes</span>
  if (val === false) return <span className="text-[0.7rem] font-bold text-red-400">✗ No</span>
  return <span className="text-[0.7rem]" style={{ color: 'var(--text4)' }}>—</span>
}

/* ─── Sidebar Form ─── */
function SidebarForm({ form, city, locality, loading, onCity, onLocality, onField, onNumericChange, onNumericBlur, onValuate }) {
  return (
    <div className="p-5 space-y-3">
      <div className="flex items-center gap-2 mb-5">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: 'rgba(0,255,204,0.08)', border: '1px solid rgba(0,255,204,0.15)' }}>
          <Home size={13} className="text-teal-400" />
        </div>
        <span className="grad-teal text-[0.7rem] uppercase tracking-[0.16em] font-bold">Property Details</span>
      </div>

      {/* City / Locality */}
      <div>
        <label className="block text-[0.68rem] mb-1.5 font-bold uppercase tracking-[0.12em]" style={{ color: 'var(--text4)' }}>City</label>
        <select value={city} onChange={e => onCity(e.target.value)}
          className="w-full rounded-xl px-3 py-2.5 text-[0.88rem] focus:outline-none transition-all"
          style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text)' }}>
          {Object.keys(LOCALITIES).map(c => <option key={c}>{c}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-[0.68rem] mb-1.5 font-bold uppercase tracking-[0.12em]" style={{ color: 'var(--text4)' }}>Locality</label>
        <select value={locality} onChange={e => onLocality(e.target.value)}
          className="w-full rounded-xl px-3 py-2.5 text-[0.88rem] focus:outline-none transition-all"
          style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text)' }}>
          {(LOCALITIES[city] || []).map(l => <option key={l}>{l}</option>)}
        </select>
      </div>

      <SbDiv label="Basic Details" />
      <div className="grid grid-cols-2 gap-2.5">
        <Sel label="Type" id="prop_type" options={['residential', 'commercial', 'industrial']} value={form.prop_type} onChange={onField} />
        <Sel label="Sub-Type" id="sub_type" options={['apartment', 'villa', 'plot', 'shop', 'warehouse', 'office']} value={form.sub_type} onChange={onField} />
        <Inp label="Built-up Area (sqft)" id="area" value={form.area} onChange={onNumericChange} onBlur={onNumericBlur} rule={NUMERIC_RULES.area} />
        <Inp label="Age (years)" id="age" value={form.age} onChange={onNumericChange} onBlur={onNumericBlur} rule={NUMERIC_RULES.age} />
      </div>
      <Sel label="Configuration" id="config" options={[{ v: '', l: 'None / N-A' }, '1BHK', '2BHK', '3BHK', '4BHK', '5BHK']} value={form.config} onChange={onField} />

      <SbDiv label="Occupation & Title" />
      <div className="grid grid-cols-2 gap-2.5">
        <Sel label="Ownership" id="ownership" options={[{ v: 'freehold', l: 'Freehold' }, { v: 'leasehold', l: 'Leasehold' }, { v: '', l: 'Unknown' }]} value={form.ownership} onChange={onField} />
        <Sel label="Title Status" id="title_clear" options={[{ v: 'true', l: 'Clear' }, { v: 'false', l: 'Disputed' }, { v: '', l: 'Unknown' }]} value={form.title_clear} onChange={onField} />
        <Inp label="Floor" id="floor" value={form.floor} onChange={onNumericChange} onBlur={onNumericBlur} rule={NUMERIC_RULES.floor} />
        <Inp label="Total Floors" id="total_floors" value={form.total_floors} onChange={onNumericChange} onBlur={onNumericBlur} rule={NUMERIC_RULES.total_floors} />
        <Sel label="Occupancy" id="occupancy" options={['self_occupied', 'rented', 'vacant']} value={form.occupancy} onChange={onField} />
        <Inp label="Rent ₹/mo" id="rent" value={form.rent} onChange={onNumericChange} onBlur={onNumericBlur} rule={NUMERIC_RULES.rent} />
      </div>

      <SbDiv label="Legal & Compliance" />
      <div className="grid grid-cols-2 gap-2.5">
        <Sel label="RERA Registered"
          id="rera_registered"
          options={[{ v: '', l: 'Unknown' }, { v: 'true', l: 'Yes' }, { v: 'false', l: 'No' }]}
          value={form.rera_registered} onChange={onField} />
        <Sel label="Occupancy Cert. (OC)"
          id="occupancy_cert"
          options={[{ v: '', l: 'Unknown' }, { v: 'true', l: 'Yes / Obtained' }, { v: 'false', l: 'No / Missing' }]}
          value={form.occupancy_cert} onChange={onField} />
        <Sel label="Completion Cert. (CC)"
          id="completion_cert"
          options={[{ v: '', l: 'Unknown' }, { v: 'true', l: 'Yes / Obtained' }, { v: 'false', l: 'No / Missing' }]}
          value={form.completion_cert} onChange={onField} />
        <Sel label="Litigation Pending"
          id="litigation"
          options={[{ v: '', l: 'Unknown' }, { v: 'false', l: 'No' }, { v: 'true', l: 'Yes — Active' }]}
          value={form.litigation} onChange={onField} />
      </div>
      <Sel label="Encumbrance Status"
        id="encumbrance"
        options={[
          { v: '', l: 'Unknown' }, { v: 'clear', l: 'Clear / Nil' },
          { v: 'existing_mortgage', l: 'Existing Mortgage' },
          { v: 'attachment_order', l: 'Attachment Order' },
          { v: 'disputed', l: 'Disputed Claim' },
        ]}
        value={form.encumbrance} onChange={onField} />
      <Inp label="Approved Plan Area (sqft)" id="approved_plan_area"
        value={form.approved_plan_area} onChange={onNumericChange} onBlur={onNumericBlur}
        rule={NUMERIC_RULES.approved_plan_area} />

      <SbDiv label="Loan & Income Parameters" />
      <Inp label="Loan Amount Requested (₹)" id="loan_amount"
        value={form.loan_amount} onChange={onNumericChange} onBlur={onNumericBlur}
        rule={NUMERIC_RULES.loan_amount} />
      {form.occupancy === 'rented' && (
        <div className="grid grid-cols-2 gap-2.5">
          <Inp label="Vacancy Rate %" id="vacancy_rate"
            value={form.vacancy_rate} onChange={onNumericChange} onBlur={onNumericBlur}
            rule={NUMERIC_RULES.vacancy_rate} />
          <Inp label="Opex Ratio %" id="opex_ratio"
            value={form.opex_ratio} onChange={onNumericChange} onBlur={onNumericBlur}
            rule={NUMERIC_RULES.opex_ratio} />
        </div>
      )}

      <div className="pt-2">
        <button onClick={onValuate} disabled={loading} className="w-full py-3.5 rounded-xl font-bold text-[0.85rem] text-white transition-all disabled:opacity-40"
          style={{ background: loading ? 'var(--border)' : 'linear-gradient(135deg, #00d4aa, #0891b2)', boxShadow: loading ? 'none' : '0 4px 20px rgba(0,212,170,0.12)' }}>
          {loading
            ? <span className="flex items-center justify-center gap-2"><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" opacity=".25" /><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" opacity=".75" /></svg> Analyzing...</span>
            : <span className="flex items-center justify-center gap-2"><Zap size={15} /> VALUATE</span>}
        </button>
        {loading && <p className="text-[0.6rem] text-center mt-2" style={{ color: 'var(--text4)' }}>Gemma4 reasoning... ~30-60s</p>}
      </div>
    </div>
  )
}

/* ═══════════════════════ MAIN APP ═══════════════════════ */
export default function App() {
  const [city, setCity] = useState('Pune')
  const [locality, setLocality] = useState('Baner')
  const [form, setForm] = useState({
    prop_type: 'residential', sub_type: 'apartment', area: 850, age: 5,
    config: '2BHK', ownership: 'freehold', title_clear: 'true',
    floor: 4, total_floors: 14, has_lift: true,
    occupancy: 'self_occupied', rent: '',
    // Legal & compliance
    rera_registered: '', occupancy_cert: '', completion_cert: '',
    encumbrance: '', litigation: '', approved_plan_area: '',
    // Loan & income
    loan_amount: '', vacancy_rate: '', opex_ratio: '',
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [drawer, setDrawer] = useState(false)
  const [lastInput, setLastInput] = useState(null)
  const [light, setLight] = useState(false)

  useEffect(() => { document.documentElement.classList.toggle('theme-light', light) }, [light])

  const handlePrint = () => setTimeout(() => window.print(), 200)

  const handleValuate = async () => {
    setLoading(true); setError(null); setResult(null); setDrawer(false)
    const parseBool = (v) => v === 'true' ? true : v === 'false' ? false : null
    const body = {
      address: `${locality}, ${city}`, property_type: form.prop_type, sub_type: form.sub_type,
      built_up_area_sqft: parseNullableNumber(form.area),
      age_years: parseNullableNumber(form.age),
      configuration: form.config || null, ownership: form.ownership || null,
      title_clear: parseBool(form.title_clear),
      floor: parseNullableNumber(form.floor),
      total_floors: parseNullableNumber(form.total_floors),
      has_lift: form.has_lift, occupancy: form.occupancy || null,
      monthly_rent: parseNullableNumber(form.rent),
      // Legal & compliance
      rera_registered:        parseBool(form.rera_registered),
      occupancy_certificate:  parseBool(form.occupancy_cert),
      completion_certificate: parseBool(form.completion_cert),
      encumbrance_status:     form.encumbrance || null,
      litigation_pending:     parseBool(form.litigation),
      approved_plan_area_sqft: parseNullableNumber(form.approved_plan_area),
      // Loan & income
      loan_amount_requested: parseNullableNumber(form.loan_amount),
      vacancy_rate_pct:      parseNullableNumber(form.vacancy_rate),
      opex_ratio_pct:        parseNullableNumber(form.opex_ratio),
    }
    setLastInput(body)
    try {
      const resp = await fetch('/valuate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      if (!resp.ok) throw new Error((await resp.json()).detail || 'API Error')
      setResult(await resp.json())
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const handleField = (id, v) => setForm(p => ({ ...p, [id]: v }))

  const setNumericField = (id, raw) => {
    const rule = NUMERIC_RULES[id] || {}
    setForm(prev => ({ ...prev, [id]: sanitizeNumericInput(raw, rule) }))
  }

  const finalizeNumericField = (id) => {
    const rule = NUMERIC_RULES[id] || {}
    setForm((prev) => {
      const next = { ...prev, [id]: clampNumericValue(prev[id], rule) }
      if (id === 'floor' && next.total_floors !== '' && Number(next.floor) > Number(next.total_floors)) {
        next.floor = next.total_floors
      }
      if (id === 'total_floors' && next.floor !== '' && Number(next.floor) > Number(next.total_floors || 0)) {
        next.floor = next.total_floors
      }
      return next
    })
  }

  const handleCity = (newCity) => { setCity(newCity); setLocality(LOCALITIES[newCity]?.[0] || '') }

  const sidebarProps = {
    form, city, locality, loading,
    onCity: handleCity,
    onLocality: setLocality,
    onField: handleField,
    onNumericChange: setNumericField,
    onNumericBlur: finalizeNumericField,
    onValuate: handleValuate,
  }

  const d = result, ins = d?.insights || {}, tr = d?.agent_trace || {}

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg)' }}>
      <div className="print-header"><div><h1>Collateral Valuation Report</h1><p>AI-Powered Estimation Portal — Poonawalla Fincorp</p></div><div style={{ textAlign: 'right' }}><p>{lastInput?.address}</p><p>{new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</p></div></div>

      <div className={`drawer-overlay ${drawer ? 'open' : ''}`} onClick={() => setDrawer(false)} />
      <div className={`drawer-panel ${drawer ? 'open' : ''}`}>
        <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <span className="text-sm font-semibold">Property Input</span>
          <button onClick={() => setDrawer(false)}><X size={18} style={{ color: 'var(--text3)' }} /></button>
        </div>
        <SidebarForm {...sidebarProps} />
      </div>

      <header className="sticky top-0 z-50 no-print" style={{ background: light ? 'rgba(255,255,255,0.92)' : 'rgba(5,7,9,0.88)', backdropFilter: 'blur(20px)', borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center justify-between px-4 md:px-6 py-3">
          <div className="flex items-center gap-3">
            <button className="md:hidden p-1.5" onClick={() => setDrawer(true)}><Menu size={20} style={{ color: 'var(--text3)' }} /></button>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-extrabold text-xs text-white" style={{ background: 'linear-gradient(135deg, #00d4aa, #0891b2)' }}>CV</div>
            <div className="hidden sm:block">
              <h1 className="text-[0.95rem] font-extrabold tracking-tight grad-teal">Collateral Valuation Engine</h1>
              <p className="text-[0.62rem] font-medium" style={{ color: 'var(--text4)' }}>AI-Powered Estimation Portal</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {d?._meta && <span className="hidden md:inline text-[0.62rem]" style={{ color: 'var(--text4)' }}>{d._meta.pipeline_time_seconds}s</span>}
            {d && <button onClick={handlePrint} className="no-print flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[0.62rem] font-semibold transition-all hover:scale-105" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text3)' }}><Download size={12} /> PDF</button>}
            <button onClick={() => setLight(!light)} className="no-print w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-110" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
              {light ? <Moon size={14} style={{ color: 'var(--text3)' }} /> : <Sun size={14} className="text-amber-400" />}
            </button>
            <div className="flex items-center gap-1.5 rounded-full px-3 py-1" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" style={{ animation: 'pulseNeon 2s infinite' }} />
              <span className="text-[0.58rem] font-semibold text-emerald-400 tracking-wider">LIVE</span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex min-h-[calc(100vh-50px)]">
        <aside className="hidden md:block w-[300px] shrink-0 overflow-y-auto no-print" style={{ borderRight: '1px solid var(--border)', background: 'var(--bg2)' }}>
          <SidebarForm {...sidebarProps} />
        </aside>

        <main className="flex-1 overflow-y-auto">
          {error && <div className="m-5 glass text-red-400 p-4 rounded-2xl flex items-center gap-3 text-sm" style={{ borderColor: 'rgba(239,68,68,0.2)' }}><AlertTriangle size={16} />{error}</div>}

          {!d && !loading && (
            <div className="flex flex-col items-center justify-center h-[75vh] text-center px-6">
              <div className="w-20 h-20 glass rounded-3xl flex items-center justify-center mb-6"
                style={{ background: 'rgba(0,255,204,0.05)', border: '1px solid rgba(0,255,204,0.15)', boxShadow: '0 0 40px rgba(0,255,204,0.06)' }}>
                <Building2 size={34} className="text-teal-500" />
              </div>
              <h2 className="text-2xl font-extrabold mb-3 grad-teal">Collateral Valuation Engine</h2>
              <p className="text-[0.9rem] max-w-md leading-relaxed" style={{ color: 'var(--text3)' }}>
                Configure property details and click{' '}
                <strong className="text-teal-400">VALUATE</strong>{' '}
                to run the 11-agent pipeline. Hover any metric to see its formula.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
                {['Market Value', 'Distress Value', 'Liquidity Score', 'Fraud Detection', 'AI Analysis'].map((f, i) => (
                  <span key={i} className="text-[0.72rem] font-semibold px-3 py-1.5 rounded-full"
                    style={{ background: 'rgba(0,255,204,0.06)', border: '1px solid rgba(0,255,204,0.14)', color: '#00d4aa' }}>{f}</span>
                ))}
              </div>
            </div>
          )}

          {loading && (
            <div className="p-5 space-y-4">
              {[1, 2, 3].map(i => <div key={i} className="glass rounded-2xl p-6"><div className="skeleton h-3 w-24 mb-4" /><div className="skeleton h-7 w-48 mb-2" /><div className="skeleton h-2 w-32" /></div>)}
            </div>
          )}

          {d && !loading && (() => {
            const hasIncome = !!ins.income
            const sn = (base) => String(hasIncome ? base : base - 1)
            return (
            <div className="p-4 md:p-6 space-y-4">
              {/* ─── Property Summary ─── */}
              <PropertySummary input={lastInput} />

              {/* ─── 1. Key Metrics ─── */}
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                <MetricCard icon={Landmark} label="Market Value" numValue={d.market_value_range?.[0]} numFormat={fmtNum} sub={`to ${fmt(d.market_value_range?.[1])}`} color="teal" tooltipId="market_value" delay={60} />
                <MetricCard icon={AlertTriangle} label="Distress Value" numValue={d.distress_value_range?.[0]} numFormat={fmtNum} sub={`to ${fmt(d.distress_value_range?.[1])}`} color="amber" tooltipId="distress_value" delay={120} />
                <MetricCard icon={Gauge} label="RPI Score" value={<><AnimatedNumber value={d.resale_potential_index} className="text-blue-400" /><span className="text-sm" style={{ color: 'var(--text4)' }}>/100</span></>} sub={d.resale_potential_index >= 60 ? 'Moderately Liquid' : d.resale_potential_index >= 40 ? 'Restricted' : 'Illiquid'} color={d.resale_potential_index >= 60 ? 'blue' : d.resale_potential_index >= 40 ? 'amber' : 'red'} tooltipId="rpi" delay={180} />
                <MetricCard icon={Target} label="Confidence" value={<ConfidenceRing value={d.confidence_score} size={72} strokeWidth={5} />} color={d.confidence_score >= 0.8 ? 'purple' : 'amber'} tooltipId="confidence" delay={240} />
                <MetricCard icon={Clock} label="Time to Sell" value={<><AnimatedNumber value={d.estimated_time_to_sell_days?.[0]} className="text-blue-400" />–<AnimatedNumber value={d.estimated_time_to_sell_days?.[1]} className="text-blue-400" /></>} sub="days" color="blue" tooltipId="ttl" delay={300} />
              </div>

              {/* ─── 2. Recommendation ─── */}
              <Tooltip id="ltv">
                <div className="glass rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${d.collateral_recommendation?.includes('accept') ? 'bg-emerald-500/12' : 'bg-amber-500/12'}`}
                      style={{ border: `1px solid ${d.collateral_recommendation?.includes('accept') ? 'rgba(52,211,153,0.2)' : 'rgba(251,191,36,0.2)'}` }}>
                      {d.collateral_recommendation?.includes('accept') ? <CheckCircle2 size={22} className="text-emerald-400" /> : <AlertTriangle size={22} className="text-amber-400" />}
                    </div>
                    <div>
                      <div className="text-[0.65rem] font-bold uppercase tracking-widest mb-0.5" style={{ color: 'var(--text4)' }}>Collateral Decision</div>
                      <div className={`text-xl font-extrabold tracking-wide ${d.collateral_recommendation?.includes('accept') ? 'grad-teal' : 'grad-amber'}`}>
                        {(d.collateral_recommendation || '').replace(/_/g, ' ').toUpperCase()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-center">
                      <div className="text-[0.65rem] font-bold uppercase tracking-widest mb-0.5" style={{ color: 'var(--text4)' }}>Recommended LTV</div>
                      <div className="num text-3xl font-extrabold grad-teal"><AnimatedNumber value={d.recommended_ltv_pct} />%</div>
                    </div>
                    <div className="h-10 w-px" style={{ background: 'var(--border-h)' }} />
                    <div className="text-center">
                      <div className="text-[0.65rem] font-bold uppercase tracking-widest mb-0.5" style={{ color: 'var(--text4)' }}>Sale Window</div>
                      <div className="num text-xl font-extrabold" style={{ color: 'var(--text)' }}>{d.estimated_time_to_sell_days?.[0]}–{d.estimated_time_to_sell_days?.[1]} <span className="text-[0.85rem] font-medium" style={{ color: 'var(--text4)' }}>days</span></div>
                    </div>
                  </div>
                </div>
              </Tooltip>

              {/* ─── Collateral Value Matrix ─── */}
              <div className="glass rounded-2xl p-5 print-section">
                <div className="flex items-center gap-2 mb-4">
                  <Landmark size={15} className="text-teal-400" />
                  <span className="text-[0.72rem] font-bold uppercase tracking-widest grad-teal">Collateral Value Summary</span>
                  <span className="ml-auto text-[0.58rem] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/20">IBA / NHB Format</span>
                </div>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  {[
                    { label: 'Fair Market Value', sub: `${fmt(d.market_value_range?.[0])} – ${fmt(d.market_value_range?.[1])}`, val: fmt((d.market_value_range?.[0] + d.market_value_range?.[1]) / 2), border: 'rgba(0,212,170,0.25)', color: '#00d4aa', desc: 'FMV (assessed)' },
                    { label: 'Distress Sale Value', sub: `${fmt(d.distress_value_range?.[0])} – ${fmt(d.distress_value_range?.[1])}`, val: fmt((d.distress_value_range?.[0] + d.distress_value_range?.[1]) / 2), border: 'rgba(251,191,36,0.25)', color: '#f59e0b', desc: 'DSV (90-day)' },
                    { label: 'Forced Sale Value', sub: '72 % of FMV · SARFAESI floor', val: fmt(d.forced_sale_value), border: 'rgba(239,68,68,0.25)', color: '#ef4444', desc: 'FSV (immediate)' },
                    { label: 'Realizable Value', sub: 'After 5 % transaction costs', val: fmt(d.realizable_value), border: 'rgba(167,139,250,0.25)', color: '#a855f7', desc: 'Net proceeds' },
                  ].map(({ label, sub, val, border, color, desc }) => (
                    <div key={label} className="rounded-xl p-4" style={{ background: 'var(--bg)', border: `1px solid ${border}` }}>
                      <div className="text-[0.58rem] uppercase tracking-wider mb-1 font-semibold" style={{ color: 'var(--text4)' }}>{label}</div>
                      <div className="num text-base font-extrabold" style={{ color }}>{val}</div>
                      <div className="num text-[0.65rem] mt-0.5" style={{ color: 'var(--text3)' }}>{sub}</div>
                      <div className="text-[0.58rem] mt-1.5 font-semibold" style={{ color: 'var(--text4)' }}>{desc}</div>
                    </div>
                  ))}
                </div>
                {d.reconstruction_value && (
                  <div className="mt-3 rounded-xl px-4 py-3 flex items-center justify-between" style={{ background: 'var(--bg)', border: '1px solid rgba(99,102,241,0.2)' }}>
                    <div>
                      <span className="text-[0.6rem] uppercase tracking-wider font-semibold" style={{ color: 'var(--text4)' }}>Reconstruction / Insurance Replacement Value</span>
                      <p className="text-[0.65rem] mt-0.5" style={{ color: 'var(--text3)' }}>Current construction cost × age depreciation · Used for fire insurance coverage</p>
                    </div>
                    <div className="num text-base font-extrabold text-indigo-400 shrink-0 ml-4">{fmt(d.reconstruction_value)}</div>
                  </div>
                )}
              </div>

              {/* 3. Key Value Drivers */}
              <Section num="1" title="Key Value Drivers" icon={BarChart3} badge={`${d.key_drivers?.length || 0} factors`}>
                {/* AI Overview */}
                {(d.scenario_narrative?.most_likely || d.explanation) && (
                  <div className="mb-4 p-3.5 rounded-xl" style={{ background: 'rgba(0,212,170,0.06)', border: '1px solid rgba(0,212,170,0.18)' }}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[0.6rem] font-bold uppercase tracking-widest" style={{ color: '#00d4aa' }}>AI Overview</span>
                      <span className="text-[0.55rem] px-1.5 py-0.5 rounded-full font-semibold" style={{ background: 'rgba(0,212,170,0.12)', color: '#00d4aa', border: '1px solid rgba(0,212,170,0.25)' }}>Gemma4</span>
                    </div>
                    <p className="text-[0.75rem] leading-relaxed" style={{ color: 'var(--text2)' }}>
                      {d.scenario_narrative?.most_likely || d.explanation}
                    </p>
                  </div>
                )}
                {d.key_drivers?.map((dr, i) => <DriverBar key={i} index={i} name={dr.factor} impact={dr.impact} agent={dr.source_agent} />)}
              </Section>

              {/* 4. RPI & Scenarios */}
              <Section num="2" title="Resale Potential & Scenario Analysis" icon={Activity} badge={`${d.resale_potential_index}/100`} badgeColor={d.resale_potential_index >= 60 ? 'teal' : 'amber'}>
                <div className="flex items-start gap-4 mt-3">
                  <div className="flex flex-col items-center gap-2">
                    <ArcGauge value={d.resale_potential_index || 0} />
                    <span className={`level-badge ${d.resale_potential_index >= 80 ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' : d.resale_potential_index >= 60 ? 'bg-blue-500/15 text-blue-400 border border-blue-500/20' : d.resale_potential_index >= 40 ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20' : 'bg-red-500/15 text-red-400 border border-red-500/20'}`}>
                      {d.resale_potential_index >= 80 ? 'TIER S' : d.resale_potential_index >= 60 ? 'TIER A' : d.resale_potential_index >= 40 ? 'TIER B' : 'TIER C'}
                    </span>
                  </div>
                  <div className="flex-1 space-y-3">
                    <div className="text-[0.65rem] uppercase tracking-widest font-semibold mb-2" style={{ color: 'var(--text4)' }}>Three Scenarios</div>
                    {[
                      { label: 'Optimistic', range: d.scenarios?.optimistic?.range, color: '#00e676', icon: '▲' },
                      { label: 'Base Case', range: d.market_value_range, color: '#00ffcc', icon: '●' },
                      { label: 'Pessimistic', range: d.scenarios?.pessimistic?.range, color: '#ff4757', icon: '▼' },
                    ].map(s => (
                      <div key={s.label} className="flex items-center gap-3 p-2.5 rounded-xl transition-all hover:scale-[1.01]" style={{ background: `${s.color}08`, border: `1px solid ${s.color}18` }}>
                        <span style={{ color: s.color }} className="text-xs w-4 text-center">{s.icon}</span>
                        <span className="text-[0.72rem] w-20" style={{ color: 'var(--text3)' }}>{s.label}</span>
                        <div className="flex-1 h-5 rounded-lg overflow-hidden relative" style={{ background: 'var(--bg)' }}>
                          <div className="absolute inset-y-0 rounded-lg" style={{
                            left: `${((s.range?.[0] || 0) / (d.scenarios?.optimistic?.range?.[1] || 1)) * 100}%`,
                            right: `${100 - ((s.range?.[1] || 0) / (d.scenarios?.optimistic?.range?.[1] || 1)) * 100}%`,
                            background: `linear-gradient(90deg, ${s.color}22, ${s.color}44)`,
                            border: `1px solid ${s.color}33`,
                          }} />
                        </div>
                        <div className="text-right min-w-[130px]">
                          <span className="num text-[0.72rem] font-semibold" style={{ color: s.color }}>{fmt(s.range?.[0])}</span>
                          <span className="text-[0.65rem] mx-1" style={{ color: 'var(--text4)' }}>–</span>
                          <span className="num text-[0.72rem] font-semibold" style={{ color: s.color }}>{fmt(s.range?.[1])}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Section>

              {/* 5. Valuation Breakdown */}
              <Section num="3" title="Valuation Breakdown" icon={Info} badge="Master Formula" badgeColor="blue">
                <div className="mt-3 p-4 rounded-xl" style={{ background: 'var(--bg)', border: '1px solid rgba(91,140,255,0.15)' }}>
                  <p className="num text-[0.78rem] leading-loose" style={{ color: 'var(--text2)' }}>
                    <strong className="text-white">V</strong> = <span className="text-teal-400 font-bold">₹{safe(tr.location_intel?.circle_rate_per_sqft?.toLocaleString())}</span>/sqft
                    {' '}×{' '}<span className="text-teal-300 font-bold">{safe(lastInput?.built_up_area_sqft)}</span> sqft
                    {' '}×{' '}<span className="text-blue-400 font-bold">{safe(tr.location_intel?.mcr)}</span> MCR
                    {' '}×{' '}<span className="text-purple-400 font-bold">{safe(tr.location_intel?.f_loc)}</span> Loc
                    {' '}×{' '}<span className={`font-bold ${tr.property_char?.f_age < 0.85 ? 'text-red-400' : 'text-amber-400'}`}>{safe(tr.property_char?.f_age)}</span> Age
                    {' '}×{' '}<span className="text-blue-300 font-bold">{safe(tr.property_char?.f_cfg)}</span> Cfg
                    {' '}×{' '}<span className="text-emerald-400 font-bold">{safe(tr.legal?.f_legal)}</span> Legal
                    {' '}×{' '}<span className="text-blue-400 font-bold">{safe(tr.property_char?.f_floor)}</span> Floor
                    {tr.legal?.f_regulatory != null && tr.legal.f_regulatory < 1.0 && (
                      <>{' '}×{' '}<span className="text-orange-400 font-bold">{safe(tr.legal?.f_regulatory)}</span> Reg</>
                    )}
                  </p>
                  <p className="num text-[1rem] font-extrabold mt-3 grad-teal">
                    = {fmt(tr.valuation?.point_estimate)} <span className="text-[0.78rem] font-normal" style={{ color: 'var(--text3)', WebkitTextFillColor: 'var(--text3)' }}>(point estimate)</span>
                  </p>
                  <p className="num text-[0.78rem] mt-1" style={{ color: 'var(--text3)' }}>
                    ± {safe(((tr.valuation?.uncertainty || 0) * 100).toFixed(1))}% uncertainty → {fmt(d.market_value_range?.[0])} to {fmt(d.market_value_range?.[1])}
                  </p>
                  {tr.valuation?.independent_estimates && (
                    <div className="mt-3 pt-3 grid grid-cols-3 gap-2" style={{ borderTop: '1px solid var(--border)' }}>
                      {[
                        ['V1 Circle Rate', tr.valuation.independent_estimates.v1_circle_rate],
                        ['V2 Comparables', tr.valuation.independent_estimates.v2_comparables],
                        ['V3 Income Approach', tr.valuation.independent_estimates.v3_income_approach],
                      ].map(([label, val]) => val ? (
                        <div key={label} className="text-center">
                          <div className="text-[0.58rem] uppercase tracking-wider" style={{ color: 'var(--text4)' }}>{label}</div>
                          <div className="num text-[0.78rem] font-bold mt-0.5" style={{ color: 'var(--text2)' }}>{fmt(val)}</div>
                        </div>
                      ) : null)}
                    </div>
                  )}
                </div>
                <div className="mt-3">
                  <FactorRow label="Circle Rate" value={`₹${safe(tr.location_intel?.circle_rate_per_sqft?.toLocaleString())}/sqft`} impact="0" tooltipId="circle_rate" />
                  <FactorRow label="Market-to-Circle Ratio" value={safe(tr.location_intel?.mcr)} impact={((tr.location_intel?.mcr || 1) - 1) * 100} tooltipId="mcr" />
                  <FactorRow label="Micro-Location Premium" value={safe(tr.location_intel?.f_loc)} impact={((tr.location_intel?.f_loc || 1) - 1) * 100} tooltipId="f_loc" />
                  <FactorRow label="Age Depreciation" value={safe(tr.property_char?.f_age)} impact={((tr.property_char?.f_age || 1) - 1) * 100} tooltipId="f_age" />
                  <FactorRow label="Configuration Factor" value={safe(tr.property_char?.f_cfg)} impact={((tr.property_char?.f_cfg || 1) - 1) * 100} tooltipId="f_cfg" />
                  <FactorRow label="Legal Clarity (Ownership)" value={safe(tr.legal?.f_legal)} impact={((tr.legal?.f_legal || 1) - 1) * 100} tooltipId="f_legal" />
                  <FactorRow label="Floor Adjustment" value={safe(tr.property_char?.f_floor)} impact={((tr.property_char?.f_floor || 1) - 1) * 100} tooltipId="f_floor" />
                  {tr.legal?.f_regulatory != null && tr.legal.f_regulatory < 1.0 && (
                    <FactorRow label="Regulatory Compliance" value={safe(tr.legal?.f_regulatory)} impact={((tr.legal?.f_regulatory || 1) - 1) * 100} tooltipId="f_regulatory" />
                  )}
                  <StatRow label="Infrastructure Score" value={safe(tr.location_intel?.infra_score)} tooltipId="infra_score" />
                  <StatRow label="Neighbourhood Quality" value={safe(tr.location_intel?.neighborhood_quality)} tooltipId="s_nbhd" />
                  <StatRow label="Point Estimate" value={fmt(tr.valuation?.point_estimate)} highlight />
                  <StatRow label="Weighted Estimate (V1+V2+V3)" value={fmt(tr.valuation?.weighted_estimate)} />
                  <StatRow label="Uncertainty Band" value={`±${safe(((tr.valuation?.uncertainty || 0) * 100).toFixed(1))}%`} tooltipId="uncertainty" />
                </div>
              </Section>

              {/* 6. AI Explanation */}
              <Section num="4" title="AI Explanation" icon={Sparkles} badge="Gemma4 LLM" badgeColor="purple">
                <p className="text-[0.95rem] leading-[1.85] mt-3" style={{ color: 'var(--text2)' }}>{d.explanation}</p>
                {d.ltv_reasoning && (
                  <p className="text-[0.82rem] mt-4 italic px-4 py-3 rounded-xl"
                    style={{ color: 'var(--text3)', background: 'rgba(167,139,250,0.06)', border: '1px solid rgba(167,139,250,0.12)' }}>
                    <span className="text-purple-400 font-semibold not-italic">LTV rationale:</span> {d.ltv_reasoning}
                  </p>
                )}
              </Section>

              {/* 7. Infrastructure */}
              <Section num="5" title="Infrastructure Proximity" icon={MapPin} badge={`Score ${safe(ins.location?.infra_score)}`} badgeColor="blue">
                <div className="mt-2"><POIChart poiBreakdown={tr.location_intel?.poi_breakdown || ins.location?.poi_summary} /></div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {ins.location?.strengths?.map((s, i) => <span key={i} className="text-[0.62rem] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 rounded-lg">{s}</span>)}
                  {ins.location?.risks?.map((r, i) => <span key={i} className="text-[0.62rem] bg-red-500/10 text-red-400 border border-red-500/20 px-2.5 py-1 rounded-lg">{r}</span>)}
                </div>
                <div className="mt-3">
                  <StatRow label="City / Locality" value={`${safe(ins.location?.city)} / ${safe(ins.location?.locality)}`} />
                  <StatRow label="City Tier" value={`Tier ${safe(ins.location?.tier)}`} />
                  <StatRow label="Micro Bucket" value={safe(ins.location?.bucket)} />
                  <StatRow label="Demand Profile" value={safe(ins.location?.demand_profile)?.replace(/_/g, ' ')} />
                  <StatRow label="Price Trend" value={safe(ins.location?.price_trend)} color={ins.location?.price_trend === 'appreciating' ? 'text-emerald-400' : ins.location?.price_trend === 'correcting' ? 'text-red-400' : ''} />
                </div>
              </Section>

              {/* 8. Property Condition */}
              <Section num="6" title="Property Condition Assessment" icon={Building2} badge={safe(ins.property?.condition_grade)} badgeColor={ins.property?.condition_grade === 'good' || ins.property?.condition_grade === 'excellent' ? 'green' : ins.property?.condition_grade === 'fair' ? 'amber' : 'red'}>
                <div className="mt-2">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-[0.72rem]" style={{ color: 'var(--text3)' }}>Condition Score</span>
                    <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg)' }}>
                      <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${(ins.property?.condition_score || 0.5) * 100}%`, background: ins.property?.condition_score >= 0.7 ? '#00d4aa' : ins.property?.condition_score >= 0.5 ? '#f59e0b' : '#ef4444' }} />
                    </div>
                    <span className="num text-[0.72rem]" style={{ color: 'var(--text)' }}>{safe(ins.property?.condition_score)}</span>
                  </div>
                  <StatRow label="Structural Risk" value={safe(ins.property?.structural_risk)} color={ins.property?.structural_risk === 'low' ? 'text-emerald-400' : ins.property?.structural_risk === 'high' ? 'text-red-400' : 'text-amber-400'} />
                  <StatRow label="Remaining Life" value={`${safe(ins.property?.remaining_life_years)} years`} />
                  <StatRow label="Age Impact" value={`${safe(ins.property?.age_impact_pct)}%`} color="text-red-400" />
                  <StatRow label="Maintenance Estimate" value={`${safe(ins.property?.maintenance_pct)}% of value`} />
                </div>
                {ins.property?.likely_issues?.length > 0 && <div className="mt-3 space-y-1">{ins.property.likely_issues.map((s, i) => <p key={i} className="text-[0.72rem] flex items-center gap-2" style={{ color: 'var(--text3)' }}><AlertTriangle size={10} className="text-amber-500/50 shrink-0" />{s}</p>)}</div>}
              </Section>

              {/* 9. Market Dynamics */}
              <Section num="7" title="Market Dynamics" icon={TrendingUp} badge={safe(ins.market?.price_momentum)}>
                <div className="mt-2">
                  <StatRow label="Active Listings (1km)" value={safe(ins.market?.listings_nearby)} tooltipId="supply_demand" />
                  <StatRow label="Supply-Demand Score" value={safe(ins.market?.supply_demand_score)} tooltipId="supply_demand" />
                  <StatRow label="Asset Fungibility" value={safe(ins.market?.fungibility)} tooltipId="fungibility" />
                  <StatRow label="Buyer Profile" value={safe(ins.market?.buyer_profile)?.replace(/_/g, ' ')} />
                  <StatRow label="Absorption Rate" value={safe(ins.market?.absorption)} />
                  <StatRow label="Negotiation Discount" value={`${safe(ins.market?.negotiation_discount)}%`} />
                </div>
              </Section>

              {/* Income Analysis — shown only for rented properties */}
              {ins.income && (
                <Section num="8" title="Income Analysis" icon={TrendingUp} badge="Rental Capitalisation" badgeColor="teal">
                  <div className="grid grid-cols-3 gap-3 mt-3">
                    {[
                      { label: 'Gross Rental Yield', val: `${ins.income.gross_rental_yield_pct}%`, sub: 'Annual rent / FMV', color: '#00d4aa', border: 'rgba(0,212,170,0.2)' },
                      { label: 'Net Rental Yield', val: `${ins.income.net_rental_yield_pct}%`, sub: 'NOI / FMV', color: '#60a5fa', border: 'rgba(96,165,250,0.2)' },
                      ins.income.dscr ? { label: 'DSCR', val: `${ins.income.dscr}×`, sub: 'RBI min 1.25×', color: ins.income.dscr >= 1.25 ? '#00d4aa' : ins.income.dscr >= 1.0 ? '#f59e0b' : '#ef4444', border: ins.income.dscr >= 1.25 ? 'rgba(0,212,170,0.2)' : 'rgba(239,68,68,0.2)' } : null,
                    ].filter(Boolean).map(({ label, val, sub, color, border }) => (
                      <div key={label} className="rounded-xl p-4 text-center" style={{ background: 'var(--bg)', border: `1px solid ${border}` }}>
                        <div className="text-[0.58rem] uppercase tracking-wider mb-1 font-semibold" style={{ color: 'var(--text4)' }}>{label}</div>
                        <div className="num text-xl font-extrabold" style={{ color }}>{val}</div>
                        <div className="text-[0.62rem] mt-1" style={{ color: 'var(--text4)' }}>{sub}</div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3">
                    <StatRow label="Monthly Rent" value={fmt(ins.income.monthly_rent)} />
                    <StatRow label="Gross Annual Rent" value={fmt(ins.income.gross_annual_rent)} />
                    <StatRow label="Vacancy Assumed" value={`${ins.income.vacancy_rate_pct}%`} />
                    <StatRow label="Operating Expense Ratio" value={`${ins.income.opex_ratio_pct}%`} />
                    <StatRow label="Net Operating Income (NOI)" value={fmt(ins.income.noi)} highlight />
                    {ins.income.grm && <StatRow label="Gross Rent Multiplier (GRM)" value={`${ins.income.grm}×`} tooltipId="grm" />}
                    {ins.income.rcr && <StatRow label="Rent Coverage Ratio" value={`${ins.income.rcr}×`} color={ins.income.rcr >= 1.25 ? 'text-emerald-400' : 'text-amber-400'} />}
                    {ins.income.monthly_emi && <StatRow label="Estimated Monthly EMI" value={fmt(ins.income.monthly_emi)} />}
                    {ins.income.loan_amount_requested && <StatRow label="Loan Amount (Requested)" value={fmt(ins.income.loan_amount_requested)} />}
                  </div>
                  <div className="mt-3 p-3 rounded-xl" style={{ background: 'rgba(0,212,170,0.04)', border: '1px solid rgba(0,212,170,0.1)' }}>
                    <p className="text-[0.7rem]" style={{ color: 'var(--text3)' }}>
                      <span className="text-teal-400 font-semibold">Income Approach (V3):</span>{' '}
                      Value capitalised from NOI using tier-specific net cap rate. NOI = Gross Rent × (1−Vacancy) × (1−Opex).
                      {ins.income.dscr && ins.income.dscr < 1.25 && <span className="text-amber-400 font-semibold"> DSCR below 1.25× RBI guideline for CRE.</span>}
                    </p>
                  </div>
                </Section>
              )}

              {/* Investment Outlook */}
              <Section num={sn(9)} title="Investment & Macro Outlook" icon={Brain} badge={safe(ins.valuation?.market_cycle)} badgeColor="purple">
                <div className="mt-2 p-3 rounded-xl" style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
                  <p className="text-[0.78rem] leading-relaxed" style={{ color: 'var(--text2)' }}>{safe(ins.valuation?.investment_outlook, 'No outlook available')}</p>
                </div>
                <div className="mt-3">
                  <StatRow label="Market Cycle" value={safe(ins.valuation?.market_cycle)} />
                  <StatRow label="Market Sentiment" value={safe(ins.valuation?.market_sentiment)} />
                  <StatRow label="Macro Adjustment" value={`${safe(ins.valuation?.macro_adjustment)}×`} />
                  <StatRow label="Uncertainty Band" value={`±${safe(ins.valuation?.uncertainty_pct)}%`} tooltipId="uncertainty" />
                </div>
              </Section>

              {/* Legal & Compliance */}
              {ins.legal_compliance && (
                <Section num={sn(10)} title="Legal & Regulatory Compliance" icon={Shield}
                  badge={ins.legal_compliance.legal_risk_category?.toUpperCase() || 'UNKNOWN'}
                  badgeColor={ins.legal_compliance.legal_risk_category === 'green' ? 'green' : ins.legal_compliance.legal_risk_category === 'red' ? 'red' : 'amber'}>
                  <div className="grid grid-cols-3 gap-3 mt-3">
                    {[
                      ['RERA', ins.legal_compliance.rera_registered, 'N/A'],
                      ['Occupancy Cert.', ins.legal_compliance.occupancy_certificate, 'Unknown'],
                      ['Completion Cert.', ins.legal_compliance.completion_certificate, 'Unknown'],
                    ].map(([label, val, fallback]) => (
                      <div key={label} className="rounded-xl p-3 text-center" style={{
                        background: 'var(--bg)',
                        border: `1px solid ${val === true ? 'rgba(52,211,153,0.25)' : val === false ? 'rgba(239,68,68,0.25)' : 'var(--border)'}`,
                      }}>
                        <div className="text-[0.58rem] uppercase tracking-wider mb-1.5 font-semibold" style={{ color: 'var(--text4)' }}>{label}</div>
                        <span className={`text-sm font-bold ${val === true ? 'text-emerald-400' : val === false ? 'text-red-400' : ''}`} style={val == null ? { color: 'var(--text3)' } : undefined}>
                          {val === true ? '✓ Obtained' : val === false ? '✗ Missing' : fallback}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3">
                    <StatRow label="Ownership Type" value={safe(ins.legal_compliance.ownership)} />
                    <StatRow label="Title Status" value={safe(ins.legal_compliance.title_status)} color={ins.legal_compliance.title_status === 'clear' ? 'text-emerald-400' : ins.legal_compliance.title_status === 'disputed' ? 'text-red-400' : ''} />
                    <StatRow label="Encumbrance Status" value={safe(ins.legal_compliance.encumbrance_status)?.replace(/_/g, ' ')} color={ins.legal_compliance.encumbrance_status === 'clear' || ins.legal_compliance.encumbrance_status === 'unknown' ? '' : 'text-amber-400'} />
                    <StatRow label="Litigation Pending" value={ins.legal_compliance.litigation_pending === true ? 'YES — High Risk' : ins.legal_compliance.litigation_pending === false ? 'No' : 'Unknown'} color={ins.legal_compliance.litigation_pending === true ? 'text-red-400' : ins.legal_compliance.litigation_pending === false ? 'text-emerald-400' : ''} />
                    {ins.legal_compliance.plan_deviation_pct != null && (
                      <StatRow label="Plan Area Deviation" value={`${ins.legal_compliance.plan_deviation_pct}%`} color={ins.legal_compliance.plan_deviation_pct > 10 ? 'text-amber-400' : 'text-emerald-400'} />
                    )}
                    <StatRow label="Title & Ownership Factor (f_legal)" value={safe(ins.legal_compliance.f_legal)} />
                    <StatRow label="Regulatory Compliance Factor" value={safe(ins.legal_compliance.f_regulatory)} color={ins.legal_compliance.f_regulatory < 0.90 ? 'text-amber-400' : 'text-emerald-400'} />
                    <StatRow label="Combined Legal Multiplier" value={safe(ins.legal_compliance.legal_multiplier)} highlight color={ins.legal_compliance.legal_multiplier < 0.85 ? 'text-red-400' : ''} />
                  </div>
                  {ins.legal_compliance.warnings?.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {ins.legal_compliance.warnings.map((w, i) => (
                        <FraudFlag key={i} flag={w.flag} severity={w.severity} explanation={w.explanation} source="legal" />
                      ))}
                    </div>
                  )}
                </Section>
              )}

              {/* Fraud & Risk */}
              <Section num={sn(11)} title="Fraud & Risk Analysis" icon={Shield} badge={`${ins.fraud?.total_flags || 0} flags`} badgeColor={ins.fraud?.total_flags ? 'red' : 'green'}>
                <div className="grid grid-cols-3 gap-3 mt-3 mb-4">
                  {[['Rule-Based', ins.fraud?.rule_based_count, 'text-blue-400'], ['AI-Detected', ins.fraud?.llm_detected_count, 'text-purple-400'], ['Overall Risk', ins.fraud?.overall_risk, ins.fraud?.overall_risk === 'low' ? 'text-emerald-400' : 'text-red-400']].map(([l, v, c]) => (
                    <div key={l} className="rounded-xl p-3 text-center" style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
                      <span className="text-[0.55rem] uppercase tracking-wider block mb-1" style={{ color: 'var(--text4)' }}>{l}</span>
                      <span className={`text-lg font-bold num capitalize ${c}`}>{v ?? 0}</span>
                    </div>
                  ))}
                </div>
                {(!d.risk_flags?.length) ? (
                  <div className="flex items-center gap-3 p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-xl text-emerald-400 text-sm">
                    <CheckCircle2 size={18} /> All {ins.fraud?.checks_performed?.length || 7} checks passed. No anomalies detected.
                  </div>
                ) : d.risk_flags.map((fl, i) => <FraudFlag key={i} {...fl} source={fl.source_agent} />)}
                {ins.fraud?.checks_performed?.length > 0 && (
                  <div className="mt-4">
                    <span className="text-[0.58rem] uppercase tracking-wider" style={{ color: 'var(--text4)' }}>Checks performed:</span>
                    <div className="flex flex-wrap gap-1.5 mt-2">{ins.fraud.checks_performed.map((c, i) => <span key={i} className="text-[0.6rem] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-lg">{c.replace(/_/g, ' ')}</span>)}</div>
                  </div>
                )}
              </Section>

              {/* Agent Trace */}
              <Section num={sn(12)} title="Full Agent Trace — 11 Agents" icon={FileText} badge="JSON" badgeColor="purple" defaultOpen={false}>
                <pre className="mt-3 text-[0.65rem] num p-5 rounded-xl overflow-auto max-h-[600px] leading-relaxed whitespace-pre-wrap" style={{ background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text3)' }}>
                  {JSON.stringify(tr, null, 2)}
                </pre>
              </Section>
            </div>
            )
          })()}
        </main>
      </div>

      <div className="print-footer">Generated by Collateral Valuation Engine — 11-Agent AI Pipeline — {new Date().toLocaleString('en-IN')}<br />Poonawalla Fincorp — AI-Powered Estimation Portal — Confidential</div>
    </div>
  )
}
