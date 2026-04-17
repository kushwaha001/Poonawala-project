import { useState, useEffect, useRef } from 'react'
import {
  Building2, Shield, TrendingUp, AlertTriangle, ChevronDown,
  MapPin, Clock, Target, Gauge, BarChart3, Brain, CheckCircle2,
  Activity, Landmark, Info, Zap, ArrowUpRight, ArrowDownRight,
  FileText, Home, Menu, X, Sparkles, Sun, Moon, Download,
  MessageSquare, Send, Bot, User
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
  area: { min: 100, max: 100000, integer: false, step: '0.01' },
  age: { min: 0, max: 120, integer: true, step: '1' },
  floor: { min: 0, max: 300, integer: true, step: '1' },
  total_floors: { min: 0, max: 300, integer: true, step: '1' },
  rent: { min: 0, max: 10000000, integer: false, step: '0.01' },
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

/* ─── Numbered Section (always visible, accordion for collapse) ─── */
function Section({ num, title, icon, badge, badgeColor = 'teal', children, defaultOpen = true }) {
  const Icon = icon
  const [open, setOpen] = useState(defaultOpen)
  const inner = useRef(null)
  const [h, setH] = useState(0)
  useEffect(() => { if (inner.current) setH(inner.current.scrollHeight) }, [open, children])
  const bc = { teal: 'bg-emerald-500/10 text-emerald-400', amber: 'bg-amber-500/10 text-amber-400', red: 'bg-red-500/10 text-red-400', blue: 'bg-blue-500/10 text-blue-400', green: 'bg-emerald-500/10 text-emerald-400', purple: 'bg-purple-500/10 text-purple-400' }
  return (
    <div className="glass rounded-2xl overflow-hidden print-section" style={{ pageBreakInside: 'avoid' }}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-5 py-4 group no-print-collapse">
        <div className="flex items-center gap-3">
          {num && <span className="num text-[0.65rem] font-bold w-6 h-6 rounded-full flex items-center justify-center" style={{ background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text3)' }}>{num}</span>}
          <div className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors" style={{ background: open ? 'rgba(0,212,170,0.08)' : 'var(--bg)' }}>
            <Icon size={14} className={`transition-colors ${open ? 'text-emerald-400' : 'text-slate-600'}`} />
          </div>
          <span className="text-[0.85rem] font-semibold" style={{ color: 'var(--text)' }}>{title}</span>
          {badge && <span className={`text-[0.58rem] font-bold uppercase tracking-widest px-2.5 py-0.5 rounded-full ${bc[badgeColor]}`}>{badge}</span>}
        </div>
        <ChevronDown size={15} className={`text-slate-600 transition-transform duration-300 no-print ${open ? 'rotate-180' : ''}`} />
      </button>
      <div className="section-body overflow-hidden transition-all duration-500 ease-out" style={{ maxHeight: open ? h + 40 : 0, opacity: open ? 1 : 0 }}>
        <div ref={inner} className="px-5 pb-5">{children}</div>
      </div>
    </div>
  )
}

/* ─── Stat Row ─── */
function StatRow({ label, value, tooltipId, color, highlight }) {
  const row = (
    <div className="hover-row flex items-center justify-between py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
      <span className="text-[0.78rem]" style={{ color: 'var(--text3)' }}>{label}</span>
      <span className={`num text-[0.82rem] font-medium ${color || ''}`} style={!color ? { color: highlight ? 'var(--color-teal)' : 'var(--text)' } : undefined}>
        {safe(value)}
      </span>
    </div>
  )
  return tooltipId ? <Tooltip id={tooltipId} wrapperClassName="block w-full cursor-help">{row}</Tooltip> : row
}

/* ─── Factor Row (for Valuation Breakdown) ─── */
function FactorRow({ label, value, impact, tooltipId }) {
  const impactNum = parseFloat(impact) || ((value - 1) * 100)
  const isPos = impactNum >= 0
  const barW = Math.min(80, Math.abs(impactNum) * 1.1)
  return (
    <Tooltip id={tooltipId} wrapperClassName="block w-full cursor-help">
      <div className="hover-row flex items-center gap-3 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <span className="text-[0.78rem] w-44 shrink-0" style={{ color: 'var(--text3)' }}>{label}</span>
        <span className="num text-[0.8rem] font-semibold w-14 text-center" style={{ color: 'var(--text)' }}>{safe(value)}</span>
        <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg)' }}>
          <div className={`h-full rounded-full ${isPos ? 'bg-gradient-to-r from-emerald-500 to-teal-400' : 'bg-gradient-to-r from-red-500 to-orange-400'}`}
            style={{ width: `${barW}%`, transition: 'width 1s ease' }} />
        </div>
        <span className={`num text-[0.75rem] font-semibold w-16 text-right ${isPos ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPos ? '+' : ''}{impactNum.toFixed(1)}%
        </span>
      </div>
    </Tooltip>
  )
}

/* ─── Driver Bar ─── */
function DriverBar({ name, impact, agent, index }) {
  const val = parseFloat(impact)
  const isPos = val >= 0
  const w = Math.min(85, Math.abs(val) * 1.1)
  return (
    <Tooltip id={name}>
      <div className="hover-row flex items-center gap-3 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <span className="text-[0.75rem] w-40 shrink-0 capitalize truncate" style={{ color: 'var(--text3)' }}>{name.replace(/_/g, ' ')}</span>
        <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg)' }}>
          <div className={`h-full rounded-full ${isPos ? 'bg-gradient-to-r from-emerald-500 to-teal-400' : 'bg-gradient-to-r from-red-500 to-orange-400'}`}
            style={{ width: `${w}%`, transition: 'width 1.2s cubic-bezier(0.4,0,0.2,1)', transitionDelay: `${index * 100}ms` }} />
        </div>
        <span className={`num text-[0.78rem] font-semibold w-16 text-right ${isPos ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPos ? <ArrowUpRight size={11} className="inline mr-0.5 -mt-0.5" /> : <ArrowDownRight size={11} className="inline mr-0.5 -mt-0.5" />}
          {impact}
        </span>
        <span className="text-[0.58rem] w-24 text-right truncate" style={{ color: 'var(--text4)' }}>{toLabel(agent)}</span>
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

/* ═══════════════════════ CHATBOT WIDGET ═══════════════════════ */
function ChatBot({ onFieldsExtracted, onValuationResult }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I\'m the Poonawalla valuation assistant. Tell me about a property and I\'ll run an estimate — for example: "Value a 3BHK flat in Baner, Pune, 950 sqft, 6 years old."' }
  ])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async () => {
    const text = input.trim()
    if (!text || thinking) return
    const userMsg = { role: 'user', content: text }
    const newHistory = [...messages, userMsg]
    setMessages(newHistory)
    setInput('')
    setThinking(true)

    try {
      const resp = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: messages.slice(1) }),
      })
      const data = await resp.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])

      if (data.extracted_fields && Object.keys(data.extracted_fields).length > 0) {
        onFieldsExtracted(data.extracted_fields)
      }
      if (data.valuation_result) {
        onValuationResult(data.valuation_result, data.extracted_fields)
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Connection error — please try again or use the form directly.' }])
    } finally {
      setThinking(false)
    }
  }

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full flex items-center justify-center shadow-xl transition-all hover:scale-110 no-print"
        style={{ background: 'linear-gradient(135deg, #00d4aa, #0891b2)', boxShadow: '0 4px 24px rgba(0,212,170,0.35)' }}
        title="Open Valuation Chatbot"
      >
        {open ? <X size={22} className="text-white" /> : <MessageSquare size={22} className="text-white" />}
      </button>

      {/* Chat panel */}
      {open && (
        <div
          className="fixed bottom-24 right-6 z-50 w-[360px] max-h-[520px] flex flex-col rounded-2xl overflow-hidden shadow-2xl no-print"
          style={{ background: 'var(--bg2)', border: '1px solid var(--border)' }}
        >
          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3" style={{ borderBottom: '1px solid var(--border)', background: 'linear-gradient(135deg, rgba(0,212,170,0.08), rgba(8,145,178,0.08))' }}>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #00d4aa, #0891b2)' }}>
              <Bot size={16} className="text-white" />
            </div>
            <div>
              <div className="text-[0.82rem] font-bold" style={{ color: 'var(--text)' }}>Valuation Assistant</div>
              <div className="text-[0.58rem]" style={{ color: 'var(--text4)' }}>Powered by Gemma4 · 11-Agent Pipeline</div>
            </div>
            <div className="ml-auto flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" style={{ animation: 'pulseNeon 2s infinite' }} />
              <span className="text-[0.55rem] text-emerald-400 font-semibold">LIVE</span>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ minHeight: 0, maxHeight: 360 }}>
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${m.role === 'user' ? 'bg-blue-500/20' : 'bg-emerald-500/20'}`}>
                  {m.role === 'user' ? <User size={11} className="text-blue-400" /> : <Bot size={11} className="text-emerald-400" />}
                </div>
                <div className={`max-w-[78%] px-3 py-2 rounded-xl text-[0.78rem] leading-relaxed ${m.role === 'user' ? 'bg-blue-500/15 text-blue-100 rounded-tr-sm' : 'rounded-tl-sm'}`}
                  style={m.role !== 'user' ? { background: 'var(--bg-card)', color: 'var(--text2)', border: '1px solid var(--border)' } : {}}>
                  {m.content}
                </div>
              </div>
            ))}
            {thinking && (
              <div className="flex gap-2">
                <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0">
                  <Bot size={11} className="text-emerald-400" />
                </div>
                <div className="px-3 py-2 rounded-xl rounded-tl-sm text-[0.78rem]" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text4)' }}>
                  <span className="inline-flex gap-1">
                    <span className="animate-bounce" style={{ animationDelay: '0ms' }}>·</span>
                    <span className="animate-bounce" style={{ animationDelay: '150ms' }}>·</span>
                    <span className="animate-bounce" style={{ animationDelay: '300ms' }}>·</span>
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="p-3" style={{ borderTop: '1px solid var(--border)' }}>
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-xl px-3 py-2 text-[0.78rem] focus:outline-none"
                style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text)' }}
                placeholder="Describe a property..."
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && send()}
                disabled={thinking}
              />
              <button
                onClick={send}
                disabled={thinking || !input.trim()}
                className="w-9 h-9 rounded-xl flex items-center justify-center transition-all disabled:opacity-40"
                style={{ background: 'linear-gradient(135deg, #00d4aa, #0891b2)' }}
              >
                <Send size={14} className="text-white" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}


/* ═══════════════════════ MAIN APP ═══════════════════════ */
export default function App() {
  const [city, setCity] = useState('Pune')
  const [locality, setLocality] = useState('Baner')
  const [form, setForm] = useState({ prop_type: 'residential', sub_type: 'apartment', area: 850, age: 5, config: '2BHK', ownership: 'freehold', title_clear: 'true', floor: 4, total_floors: 14, has_lift: true, occupancy: 'self_occupied', rent: 0, rera: '', builder: '' })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [drawer, setDrawer] = useState(false)
  const [lastInput, setLastInput] = useState(null)
  const [light, setLight] = useState(false)

  useEffect(() => { document.documentElement.classList.toggle('theme-light', light) }, [light])

  const handlePrint = () => setTimeout(() => window.print(), 200)

  const handleFieldsExtracted = (fields) => {
    if (fields.city) setCity(fields.city)
    if (fields.locality) setLocality(fields.locality)
    setForm(prev => ({
      ...prev,
      ...(fields.property_type ? { prop_type: fields.property_type } : {}),
      ...(fields.sub_type ? { sub_type: fields.sub_type } : {}),
      ...(fields.built_up_area_sqft != null ? { area: String(fields.built_up_area_sqft) } : {}),
      ...(fields.age_years != null ? { age: String(fields.age_years) } : {}),
      ...(fields.configuration ? { config: fields.configuration } : {}),
      ...(fields.floor != null ? { floor: String(fields.floor) } : {}),
      ...(fields.total_floors != null ? { total_floors: String(fields.total_floors) } : {}),
      ...(fields.has_lift != null ? { has_lift: fields.has_lift } : {}),
      ...(fields.ownership ? { ownership: fields.ownership } : {}),
      ...(fields.title_clear != null ? { title_clear: String(fields.title_clear) } : {}),
      ...(fields.monthly_rent != null ? { rent: String(fields.monthly_rent) } : {}),
      ...(fields.occupancy ? { occupancy: fields.occupancy } : {}),
      ...(fields.rera_registered != null ? { rera: String(fields.rera_registered) } : {}),
      ...(fields.builder_name ? { builder: fields.builder_name } : {}),
    }))
  }

  const handleChatValuation = (valResult, fields) => {
    setResult(valResult)
    if (fields) {
      const addr = `${fields.locality || ''}, ${fields.city || ''}`.trim().replace(/^,\s*/, '')
      setLastInput({
        address: addr,
        property_type: fields.property_type || 'residential',
        sub_type: fields.sub_type,
        built_up_area_sqft: fields.built_up_area_sqft,
        age_years: fields.age_years,
      })
    }
  }

  const handleValuate = async () => {
    setLoading(true); setError(null); setResult(null); setDrawer(false)
    const body = {
      address: `${locality}, ${city}`, property_type: form.prop_type, sub_type: form.sub_type,
      built_up_area_sqft: parseNullableNumber(form.area),
      age_years: parseNullableNumber(form.age),
      configuration: form.config || null, ownership: form.ownership || null,
      title_clear: form.title_clear === 'true' ? true : form.title_clear === 'false' ? false : null,
      floor: parseNullableNumber(form.floor),
      total_floors: parseNullableNumber(form.total_floors),
      has_lift: form.has_lift, occupancy: form.occupancy || null, monthly_rent: parseNullableNumber(form.rent),
      rera_registered: form.rera === 'true' ? true : form.rera === 'false' ? false : null,
      builder_name: form.builder || null,
    }
    setLastInput(body)
    try {
      const resp = await fetch('/valuate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      if (!resp.ok) throw new Error((await resp.json()).detail || 'API Error')
      setResult(await resp.json())
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const f = (id, v) => setForm(p => ({ ...p, [id]: v }))

  const setNumericField = (id, raw) => {
    const rule = NUMERIC_RULES[id] || {}
    f(id, sanitizeNumericInput(raw, rule))
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

  const Sel = ({ label, id, options }) => (
    <div>
      <label className="block text-[0.6rem] mb-1 font-medium uppercase tracking-[0.1em]" style={{ color: 'var(--text4)' }}>{label}</label>
      <select value={form[id]} onChange={e => f(id, e.target.value)} className="w-full rounded-xl px-3 py-2.5 text-[0.8rem] focus:outline-none transition-all" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text)' }}>
        {options.map(o => <option key={typeof o === 'string' ? o : o.v} value={typeof o === 'string' ? o : o.v}>{typeof o === 'string' ? o : o.l}</option>)}
      </select>
    </div>
  )
  const Inp = ({ label, id, ...p }) => {
    const rule = NUMERIC_RULES[id] || {}
    return (
    <div>
      <label className="block text-[0.6rem] mb-1 font-medium uppercase tracking-[0.1em]" style={{ color: 'var(--text4)' }}>{label}</label>
      <input
        type="text"
        inputMode={rule.integer ? 'numeric' : 'decimal'}
        pattern={rule.integer ? '[0-9]*' : '[0-9]*[.]?[0-9]*'}
        min={rule.min}
        max={rule.max}
        step={rule.step || 'any'}
        value={form[id]}
        onChange={e => setNumericField(id, e.target.value)}
        onBlur={() => finalizeNumericField(id)}
        className="w-full rounded-xl px-3 py-2.5 text-[0.8rem] num focus:outline-none transition-all"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text)' }}
        {...p}
      />
    </div>
  )
  }

  const d = result, ins = d?.insights || {}, tr = d?.agent_trace || {}

  const SidebarForm = () => (
    <div className="p-5 space-y-3">
      <div className="flex items-center gap-2 mb-4"><Home size={13} style={{ color: 'var(--text4)' }} /><span className="text-[0.62rem] uppercase tracking-[0.14em] font-semibold" style={{ color: 'var(--text4)' }}>Property Details</span></div>
      <div>
        <label className="block text-[0.6rem] mb-1 font-medium uppercase tracking-[0.1em]" style={{ color: 'var(--text4)' }}>City</label>
        <select value={city} onChange={e => { setCity(e.target.value); setLocality(LOCALITIES[e.target.value]?.[0] || '') }} className="w-full rounded-xl px-3 py-2.5 text-[0.8rem] focus:outline-none transition-all" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text)' }}>
          {Object.keys(LOCALITIES).map(c => <option key={c}>{c}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-[0.6rem] mb-1 font-medium uppercase tracking-[0.1em]" style={{ color: 'var(--text4)' }}>Locality</label>
        <select value={locality} onChange={e => setLocality(e.target.value)} className="w-full rounded-xl px-3 py-2.5 text-[0.8rem] focus:outline-none transition-all" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text)' }}>
          {(LOCALITIES[city] || []).map(l => <option key={l}>{l}</option>)}
        </select>
      </div>
      <div style={{ height: 1, background: 'var(--border)' }} />
      <div className="grid grid-cols-2 gap-2.5">
        <Sel label="Type" id="prop_type" options={['residential', 'commercial', 'industrial']} />
        <Sel label="Sub-Type" id="sub_type" options={['apartment', 'villa', 'plot', 'shop', 'warehouse', 'office']} />
        <Inp label="Area (sqft)" id="area" />
        <Inp label="Age (years)" id="age" />
      </div>
      <Sel label="Config" id="config" options={[{ v: '', l: 'None' }, '1BHK', '2BHK', '3BHK', '4BHK', '5BHK']} />
      <div style={{ height: 1, background: 'var(--border)' }} />
      <div className="grid grid-cols-2 gap-2.5">
        <Sel label="Ownership" id="ownership" options={[{ v: 'freehold', l: 'Freehold' }, { v: 'leasehold', l: 'Leasehold' }, { v: '', l: 'Unknown' }]} />
        <Sel label="Title" id="title_clear" options={[{ v: 'true', l: 'Clear' }, { v: 'false', l: 'Disputed' }, { v: '', l: 'Unknown' }]} />
        <Inp label="Floor" id="floor" />
        <Inp label="Total Floors" id="total_floors" />
        <Sel label="Occupancy" id="occupancy" options={['self_occupied', 'rented', 'vacant']} />
        <Inp label="Rent ₹/mo" id="rent" />
      </div>
      <div style={{ height: 1, background: 'var(--border)' }} />
      <Sel label="RERA Status" id="rera" options={[{ v: '', l: 'Unknown' }, { v: 'true', l: 'Registered' }, { v: 'false', l: 'Not Registered' }]} />
      <div>
        <label className="block text-[0.6rem] mb-1 font-medium uppercase tracking-[0.1em]" style={{ color: 'var(--text4)' }}>Builder / Developer</label>
        <input type="text" placeholder="e.g. Godrej, DLF, Lodha..." value={form.builder} onChange={e => f('builder', e.target.value)} className="w-full rounded-xl px-3 py-2.5 text-[0.8rem] focus:outline-none transition-all" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text)' }} />
      </div>
      <div className="pt-2">
        <button onClick={handleValuate} disabled={loading} className="w-full py-3.5 rounded-xl font-bold text-[0.85rem] text-white transition-all disabled:opacity-40"
          style={{ background: loading ? 'var(--border)' : 'linear-gradient(135deg, #00d4aa, #0891b2)', boxShadow: loading ? 'none' : '0 4px 20px rgba(0,212,170,0.12)' }}>
          {loading ? <span className="flex items-center justify-center gap-2"><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" opacity=".25" /><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" opacity=".75" /></svg> Analyzing...</span> : <span className="flex items-center justify-center gap-2"><Zap size={15} /> VALUATE</span>}
        </button>
        {loading && <p className="text-[0.6rem] text-center mt-2" style={{ color: 'var(--text4)' }}>Gemma4 reasoning... ~30-60s</p>}
      </div>
    </div>
  )

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg)' }}>
      <div className="print-header"><div><h1>Collateral Valuation Report</h1><p>AI-Powered Estimation Portal — Poonawalla Fincorp</p></div><div style={{ textAlign: 'right' }}><p>{lastInput?.address}</p><p>{new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</p></div></div>

      <div className={`drawer-overlay ${drawer ? 'open' : ''}`} onClick={() => setDrawer(false)} />
      <div className={`drawer-panel ${drawer ? 'open' : ''}`}>
        <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <span className="text-sm font-semibold">Property Input</span>
          <button onClick={() => setDrawer(false)}><X size={18} style={{ color: 'var(--text3)' }} /></button>
        </div>
        <SidebarForm />
      </div>

      <header className="sticky top-0 z-50 no-print" style={{ background: light ? 'rgba(255,255,255,0.92)' : 'rgba(5,7,9,0.88)', backdropFilter: 'blur(20px)', borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center justify-between px-4 md:px-6 py-3">
          <div className="flex items-center gap-3">
            <button className="md:hidden p-1.5" onClick={() => setDrawer(true)}><Menu size={20} style={{ color: 'var(--text3)' }} /></button>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-extrabold text-xs text-white" style={{ background: 'linear-gradient(135deg, #00d4aa, #0891b2)' }}>CV</div>
            <div className="hidden sm:block">
              <h1 className="text-[0.85rem] font-bold tracking-tight" style={{ color: 'var(--text)' }}>Collateral Valuation Engine</h1>
              <p className="text-[0.58rem]" style={{ color: 'var(--text4)' }}>AI-Powered Estimation Portal</p>
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
          <SidebarForm />
        </aside>

        <main className="flex-1 overflow-y-auto">
          {error && <div className="m-5 glass text-red-400 p-4 rounded-2xl flex items-center gap-3 text-sm" style={{ borderColor: 'rgba(239,68,68,0.2)' }}><AlertTriangle size={16} />{error}</div>}

          {!d && !loading && (
            <div className="flex flex-col items-center justify-center h-[75vh] text-center px-6">
              <div className="w-16 h-16 glass rounded-2xl flex items-center justify-center mb-5"><Building2 size={28} style={{ color: 'var(--text4)' }} /></div>
              <h2 className="text-lg font-bold mb-2" style={{ color: 'var(--text2)' }}>Collateral Valuation Engine</h2>
              <p className="text-[0.82rem] max-w-md leading-relaxed" style={{ color: 'var(--text3)' }}>Configure property details and click <strong className="text-teal-400">VALUATE</strong> to run the 11-agent pipeline. Hover over any metric to see its formula.</p>
            </div>
          )}

          {loading && (
            <div className="p-5 space-y-4">
              {[1, 2, 3].map(i => <div key={i} className="glass rounded-2xl p-6"><div className="skeleton h-3 w-24 mb-4" /><div className="skeleton h-7 w-48 mb-2" /><div className="skeleton h-2 w-32" /></div>)}
            </div>
          )}

          {d && !loading && (
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
                    <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${d.collateral_recommendation?.includes('accept') ? 'bg-emerald-500/10' : 'bg-amber-500/10'}`}>
                      {d.collateral_recommendation?.includes('accept') ? <CheckCircle2 size={20} className="text-emerald-400" /> : <AlertTriangle size={20} className="text-amber-400" />}
                    </div>
                    <div>
                      <div className="text-[0.58rem] uppercase tracking-widest" style={{ color: 'var(--text4)' }}>Collateral Decision</div>
                      <div className={`text-lg font-bold ${d.collateral_recommendation?.includes('accept') ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {(d.collateral_recommendation || '').replace(/_/g, ' ').toUpperCase()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-center"><div className="text-[0.58rem] uppercase tracking-widest" style={{ color: 'var(--text4)' }}>LTV</div><div className="num text-2xl font-bold text-teal-400"><AnimatedNumber value={d.recommended_ltv_pct} />%</div></div>
                    <div className="h-10 w-px" style={{ background: 'var(--border)' }} />
                    <div className="text-center"><div className="text-[0.58rem] uppercase tracking-widest" style={{ color: 'var(--text4)' }}>Sale Window</div><div className="num text-lg font-bold">{d.estimated_time_to_sell_days?.[0]}–{d.estimated_time_to_sell_days?.[1]} <span className="text-sm" style={{ color: 'var(--text4)' }}>days</span></div></div>
                  </div>
                </div>
              </Tooltip>

              {/* ─── ALL SECTIONS SEQUENTIAL (no tabs) ─── */}

              {/* 3. Key Value Drivers */}
              <Section num="1" title="Key Value Drivers" icon={BarChart3} badge={`${d.key_drivers?.length || 0} factors`}>
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

              {/* 5. Valuation Breakdown (FIXED) */}
              <Section num="3" title="Valuation Breakdown" icon={Info} badge="Master Formula" badgeColor="blue">
                <div className="mt-2 p-4 rounded-xl" style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
                  <p className="num text-[0.72rem] leading-relaxed" style={{ color: 'var(--text2)' }}>
                    <strong style={{ color: 'var(--text)' }}>V</strong> = <span className="text-teal-400">₹{safe(tr.location_intel?.circle_rate_per_sqft?.toLocaleString())}</span>/sqft
                    × <span className="text-teal-400">{safe(lastInput?.built_up_area_sqft)}</span> sqft
                    × <span className="text-blue-400">{safe(tr.location_intel?.mcr)}</span> MCR
                    × <span className="text-purple-400">{safe(tr.location_intel?.f_loc)}</span> Loc
                    × <span className={tr.property_char?.f_age < 0.85 ? 'text-red-400' : 'text-amber-400'}>{safe(tr.property_char?.f_age)}</span> Age
                    × <span className="text-blue-400">{safe(tr.property_char?.f_cfg)}</span> Cfg
                    × <span className="text-emerald-400">{safe(tr.legal?.f_legal)}</span> Legal
                    × <span className="text-blue-400">{safe(tr.property_char?.f_floor)}</span> Floor
                    {tr.valuation?.f_regulatory != null && tr.valuation?.f_regulatory !== 1 && (
                      <> × <span className={tr.valuation.f_regulatory > 1 ? 'text-emerald-400' : 'text-red-400'}>{safe(tr.valuation?.f_regulatory)}</span> RERA</>
                    )}
                  </p>
                  <p className="num text-[0.82rem] font-bold mt-2" style={{ color: 'var(--text)' }}>
                    = {fmt(tr.valuation?.point_estimate)} <span className="text-[0.72rem] font-normal" style={{ color: 'var(--text3)' }}>(point estimate)</span>
                  </p>
                  <p className="num text-[0.72rem] mt-1" style={{ color: 'var(--text3)' }}>
                    ± {safe(((tr.valuation?.uncertainty || 0) * 100).toFixed(1))}% uncertainty = {fmt(d.market_value_range?.[0])} to {fmt(d.market_value_range?.[1])}
                  </p>
                </div>
                <div className="mt-3">
                  <FactorRow label="Circle Rate" value={`₹${safe(tr.location_intel?.circle_rate_per_sqft?.toLocaleString())}/sqft`} impact="0" tooltipId="circle_rate" />
                  <FactorRow label="Market-to-Circle Ratio" value={safe(tr.location_intel?.mcr)} impact={((tr.location_intel?.mcr || 1) - 1) * 100} tooltipId="mcr" />
                  <FactorRow label="Micro-Location Premium" value={safe(tr.location_intel?.f_loc)} impact={((tr.location_intel?.f_loc || 1) - 1) * 100} tooltipId="f_loc" />
                  <FactorRow label="Age Depreciation" value={safe(tr.property_char?.f_age)} impact={((tr.property_char?.f_age || 1) - 1) * 100} tooltipId="f_age" />
                  <FactorRow label="Configuration Factor" value={safe(tr.property_char?.f_cfg)} impact={((tr.property_char?.f_cfg || 1) - 1) * 100} tooltipId="f_cfg" />
                  <FactorRow label="Legal Clarity" value={safe(tr.legal?.f_legal)} impact={((tr.legal?.f_legal || 1) - 1) * 100} tooltipId="f_legal" />
                  <FactorRow label="Floor Adjustment" value={safe(tr.property_char?.f_floor)} impact={((tr.property_char?.f_floor || 1) - 1) * 100} tooltipId="f_floor" />
                  {tr.valuation?.f_regulatory != null && (
                    <FactorRow label="RERA Regulatory" value={safe(tr.valuation?.f_regulatory)} impact={((tr.valuation?.f_regulatory || 1) - 1) * 100} tooltipId="f_regulatory" />
                  )}
                  <StatRow label="Infrastructure Score" value={safe(tr.location_intel?.infra_score)} tooltipId="infra_score" />
                  <StatRow label="Neighbourhood Quality" value={safe(tr.location_intel?.neighborhood_quality)} tooltipId="s_nbhd" />
                  <StatRow label="Point Estimate" value={fmt(tr.valuation?.point_estimate)} highlight />
                  <StatRow label="Uncertainty Band" value={`±${safe(((tr.valuation?.uncertainty || 0) * 100).toFixed(1))}%`} tooltipId="uncertainty" />
                </div>
              </Section>

              {/* 6. AI Explanation */}
              <Section num="4" title="AI Explanation" icon={Sparkles} badge="Gemma4 LLM" badgeColor="purple">
                <p className="text-[0.85rem] leading-[1.8] mt-2" style={{ color: 'var(--text2)' }}>{d.explanation}</p>
                {d.ltv_reasoning && <p className="text-[0.72rem] mt-3 italic" style={{ color: 'var(--text3)' }}>LTV rationale: {d.ltv_reasoning}</p>}
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

              {/* 10. Investment Outlook */}
              <Section num="8" title="Investment & Macro Outlook" icon={Brain} badge={safe(ins.valuation?.market_cycle)} badgeColor="purple">
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

              {/* 11. Fraud & Risk */}
              <Section num="9" title="Fraud & Risk Analysis" icon={Shield} badge={`${ins.fraud?.total_flags || 0} flags`} badgeColor={ins.fraud?.total_flags ? 'red' : 'green'}>
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

              {/* 12. Agent Trace */}
              <Section num="10" title="Full Agent Trace — 11 Agents" icon={FileText} badge="JSON" badgeColor="purple" defaultOpen={false}>
                <pre className="mt-3 text-[0.65rem] num p-5 rounded-xl overflow-auto max-h-[600px] leading-relaxed whitespace-pre-wrap" style={{ background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text3)' }}>
                  {JSON.stringify(tr, null, 2)}
                </pre>
              </Section>
            </div>
          )}
        </main>
      </div>

      <div className="print-footer">Generated by Collateral Valuation Engine — 11-Agent AI Pipeline — {new Date().toLocaleString('en-IN')}<br />Poonawalla Fincorp — AI-Powered Estimation Portal — Confidential</div>

      <ChatBot onFieldsExtracted={handleFieldsExtracted} onValuationResult={handleChatValuation} />
    </div>
  )
}
