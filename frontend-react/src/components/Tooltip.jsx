import { useState, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'

const DEFINITIONS = {
  market_value: { title: 'Market Value Range', formula: 'V = R_c × A × MCR × f_loc × f_age × f_cfg × f_legal × f_floor', desc: 'Fair market value if sold patiently to a willing buyer. Range reflects uncertainty.' },
  distress_value: { title: 'Distress / Forced-Sale Value', formula: 'D = MV × (1 − discount) × ±5%', desc: 'Recovery value in a forced sale within 30 days. Discount 15-40% based on liquidity.' },
  rpi: { title: 'Resale Potential Index', formula: 'RPI = 100 × Σ(w_i × S_i)', desc: '0-100 liquidity score. 80+ Highly Liquid, 60-80 Moderate, 40-60 Restricted, <40 Illiquid.' },
  confidence: { title: 'Confidence Score', formula: 'C = 0.40×Q_data + 0.30×Q_agree + 0.20×Q_density + 0.10×(1−P_fraud)', desc: 'System trust in its estimate. Higher = more data, better source agreement.' },
  ttl: { title: 'Time to Liquidate', formula: 'τ = T_base / (RPI/50)^1.5', desc: 'Expected days to sell. Log-normal — some properties can take much longer.' },
  mcr: { title: 'Market-to-Circle Ratio', formula: 'MCR adjusted by Gemma4 LLM', desc: 'Market prices vs government circle rate. Tier-1 prime can reach 2.2×.' },
  circle_rate: { title: 'Circle Rate', formula: 'State government gazette', desc: 'Government minimum per sqft — the floor anchor for our valuation.' },
  f_age: { title: 'Age Depreciation', formula: 'f_age = 1 − s × 0.60 × (1 − e^(−0.04×age))', desc: 'Structure depreciates exponentially. Land value is preserved.' },
  f_cfg: { title: 'Config Factor', formula: 'f_cfg = 1 − 0.08 × |area − mode| / mode', desc: 'Penalty for non-standard size. Standard 2BHK = 1.0.' },
  f_loc: { title: 'Micro-Location', formula: 'f_loc = 1 + 0.25×(S_infra−exp) + 0.15×(S_nbhd−0.5)', desc: 'Fine-tunes based on local infrastructure quality.' },
  f_legal: { title: 'Legal Factor', formula: 'Freehold+clear=1.0, disputed=0.85', desc: 'Legal risk directly discounts valuation.' },
  f_floor: { title: 'Floor Factor', formula: 'Ground shop +5%, high no-lift −15%', desc: 'Floor accessibility premium or penalty.' },
  infra_score: { title: 'Infrastructure Score', formula: 'S_infra = Σ w_i × e^(−d_i / d_ref)', desc: 'Exponential decay from 6 POI types. Closer = higher score.' },
  ltv: { title: 'Loan-to-Value', desc: 'Max recommended loan as % of conservative market value.' },
  uncertainty: { title: 'Uncertainty Band', formula: 'u = 8% + data_gap + disagreement + fraud', desc: 'Range width. Min 8%, max 25%. Widens with missing data.' },
  supply_demand: { title: 'Supply-Demand Score', formula: 'S_ds = e^(−MOI/12)', desc: 'Months of Inventory model. <6 mo = sellers market.' },
  fungibility: { title: 'Fungibility', desc: 'How interchangeable this property is. Standard apartments = high.' },
  market_to_circle_ratio: { title: 'MCR', formula: 'MCR = tier × bucket lookup', desc: 'Market premium over circle rate.' },
  micro_location_adjustment: { title: 'Micro-Location', desc: 'Premium for above-average infrastructure in the micro-bucket.' },
  age_depreciation: { title: 'Age Depreciation', desc: 'Non-linear structure decay. Land does not depreciate.' },
  config_factor: { title: 'Config Standardness', desc: 'Penalty for deviating from locality modal size.' },
  floor_factor: { title: 'Floor Adjustment', desc: 'Ground shop premium, high floor lift penalty.' },
  legal_factor: { title: 'Legal Discount', desc: 'Disputed title hammers both value and liquidity.' },
}

function TipPortal({ rect, def }) {
  const pad = 12
  let top = rect.top - pad - 10
  let left = rect.left + rect.width / 2
  let transform = 'translate(-50%, -100%)'

  // If tooltip would go above viewport, show below instead
  if (top < 80) {
    top = rect.bottom + pad
    transform = 'translate(-50%, 0)'
  }

  // Clamp horizontally
  left = Math.max(180, Math.min(window.innerWidth - 180, left))

  return createPortal(
    <div className="tip-portal visible" style={{ top, left, transform }}>
      <div className="tip-title">{def.title}</div>
      {def.formula && <code>{def.formula}</code>}
      <p>{def.desc}</p>
    </div>,
    document.body
  )
}

export default function Tooltip({ id, children, wrapperClassName = 'inline-flex items-center cursor-help', wrapperStyle }) {
  const def = DEFINITIONS[id]
  const [show, setShow] = useState(false)
  const [rect, setRect] = useState(null)
  const ref = useRef(null)
  const timer = useRef(null)

  const handleEnter = useCallback(() => {
    timer.current = setTimeout(() => {
      if (ref.current) setRect(ref.current.getBoundingClientRect())
      setShow(true)
    }, 200)
  }, [])

  const handleLeave = useCallback(() => {
    clearTimeout(timer.current)
    setShow(false)
  }, [])

  if (!def) return children

  return (
    <span ref={ref} onMouseEnter={handleEnter} onMouseLeave={handleLeave}
      className={wrapperClassName}
      style={wrapperStyle}>
      {children}
      {show && rect && <TipPortal rect={rect} def={def} />}
    </span>
  )
}
