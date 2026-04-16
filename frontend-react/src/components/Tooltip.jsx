import { useState, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'

const DEFINITIONS = {
  // ── Top-level output metrics ──
  market_value: {
    title: 'Fair Market Value (FMV)',
    formula: 'V = R_c × A × MCR × f_loc × f_age × f_cfg × f_legal × f_floor × f_regulatory',
    desc: 'Value if sold patiently to a willing buyer with adequate market exposure. Range reflects model uncertainty (±8–25%). This is the primary collateral benchmark per IBA/NHB guidelines.',
  },
  distress_value: {
    title: 'Distress Sale Value (DSV)',
    formula: 'DSV = FMV × (1 − discount)  where discount = 15% + 25% × (1 − RPI/100)',
    desc: '90-day forced-liquidation value. Discount narrows for liquid assets (high RPI) and widens for illiquid ones. Used by SARFAESI recovery proceedings.',
  },
  rpi: {
    title: 'Resale Potential Index (RPI)',
    formula: 'RPI = 100 × (0.30×S_infra + 0.20×S_cfg + 0.20×S_ds + 0.15×S_legal + 0.10×S_age + 0.05×S_yield)',
    desc: '0–100 composite liquidity score. ≥80 Highly Liquid (TIER S), 60–79 Moderate (TIER A), 40–59 Restricted (TIER B), <40 Illiquid (TIER C). Drives LTV recommendation.',
  },
  confidence: {
    title: 'Confidence Score',
    formula: 'C = 0.40×Q_data + 0.30×Q_agree + 0.20×Q_density + 0.10×(1−P_fraud)',
    desc: 'System confidence in the estimate. ≥85% High, 65–85% Medium, 45–65% Low, <45% Unreliable. Reduces when data is incomplete, sources disagree or fraud flags exist.',
  },
  ttl: {
    title: 'Time to Liquidate',
    formula: 'τ_median = T_base / (RPI/50)^1.5  ·  range = τ × e^(±0.40)',
    desc: 'Expected days to sell at fair value. Log-normal distribution — 80th percentile can be 2× median. High-RPI assets transact much faster.',
  },

  // ── Valuation factor rows ──
  mcr: {
    title: 'Market-to-Circle Ratio (MCR)',
    formula: 'MCR = rule_MCR × (1−w) + LLM_MCR × w   (w ≤ 0.60)',
    desc: 'How much the real market trades above the government circle rate. Tier-1 prime zones reach 2.2×; peripheral Tier-3 as low as 1.05×. Blended from lookup table + Gemma4 LLM reasoning.',
  },
  circle_rate: {
    title: 'Circle Rate (Ready Reckoner Rate)',
    formula: 'Published by State Revenue Dept / Sub-Registrar Office',
    desc: 'Government-mandated minimum registration value per sqft. The floor anchor for our valuation. Updated annually in most states; staleness is flagged.',
  },
  f_age: {
    title: 'Age Depreciation Factor (f_age)',
    formula: 'f_age = 1 − s × 0.60 × (1 − e^(−0.04 × age))   adjusted ±5% by LLM condition score',
    desc: 'Exponential decay of structure value. Structure ratio (s) = 0.55 for apartments, 0.35 for villas. Land value is unaffected. Gemma4 adjusts ±5% based on visual condition assessment.',
  },
  f_cfg: {
    title: 'Configuration / Size Factor (f_cfg)',
    formula: 'f_cfg = clamp(1 − 0.08 × |area − mode_area| / mode_area,  0.85, 1.12)',
    desc: 'Penalty for non-standard unit size vs locality modal area. A perfectly standard 2BHK scores 1.0. Unusually large or small units are harder to sell and priced at a discount.',
  },
  f_loc: {
    title: 'Micro-Location Adjustment (f_loc)',
    formula: 'f_loc = 1 + 0.25×(S_infra − S_exp) + 0.15×(S_nbhd − 0.5)',
    desc: 'Fine-tunes value based on actual POI proximity vs the bucket expectation. Above-average infra for a "standard" bucket = premium; below-average for "prime" = discount.',
  },
  f_legal: {
    title: 'Legal Factor — Ownership & Title (f_legal)',
    formula: 'Freehold+clear→1.00 | Freehold+unknown→0.95 | Leasehold→0.92 | Disputed→0.85',
    desc: 'Direct discount for ownership risk. Disputed title severely impacts both value and liquidity. Leasehold has reduced marketability vs freehold.',
  },
  f_floor: {
    title: 'Floor Adjustment Factor (f_floor)',
    formula: 'Ground shop +5% | Mid (4–8F) +2% | High+lift +3% | High−lift −10–15%',
    desc: 'Floor-level premium or penalty. Shops at ground floor are most valuable. Residential units above floor 8 without a passenger lift face a significant marketability discount.',
  },
  f_regulatory: {
    title: 'Regulatory Compliance Factor (f_regulatory)',
    formula: 'f_reg = ∏ haircut_i  ·  (OC missing → ×0.92, Litigation → ×0.80, Attachment → ×0.70)',
    desc: 'India-specific multiplicative haircut for compliance gaps. Missing Occupancy Certificate, active court orders, RERA non-registration, or attachment orders compound to reduce value. Minimum: 0.40.',
  },

  // ── Infrastructure & location ──
  infra_score: {
    title: 'Infrastructure Proximity Score (S_infra)',
    formula: 'S_infra = Σ w_i × e^(−d_i / d_ref)   (live OSM distances)',
    desc: 'Weighted sum of exponential decay scores for 6 POI categories: metro (20%), highway (15%), school (15%), hospital (15%), commercial (20%), IT park (15%). Computed from live OpenStreetMap data.',
  },
  s_nbhd: {
    title: 'Neighbourhood Quality Score (S_nbhd)',
    formula: 'S_nbhd = 0.50 + 0.30×ρ_res + 0.20×ρ_com − 0.40×ρ_ind + density_bonus',
    desc: 'Mix of residential, commercial and industrial POIs around the property. More residential + commercial and less industrial = higher neighbourhood quality.',
  },

  // ── Market ──
  supply_demand: {
    title: 'Supply-Demand Score (S_ds)',
    formula: 'S_ds = e^(−MOI/12)   where MOI = active_listings / monthly_absorption',
    desc: 'Months of Inventory model. MOI < 3 = hot sellers\' market (S_ds ≈ 0.78). MOI = 12 = balanced. MOI > 24 = buyer\'s market with price pressure.',
  },
  fungibility: {
    title: 'Asset Fungibility',
    desc: 'How easily this asset class can be converted to cash. Standard 2BHK in Tier-1 city ≈ 0.80–0.90. Specialised warehouse or unique villa ≈ 0.25–0.45. Drives time-to-sell estimate.',
  },

  // ── Income ──
  grm: {
    title: 'Gross Rent Multiplier (GRM)',
    formula: 'GRM = Property Value / Annual Gross Rent',
    desc: 'Years to recover property value from gross rent alone. Residential: 25–40× typical; commercial: 12–20×. Lower GRM = better income relative to price.',
  },

  // ── Confidence & risk ──
  ltv: {
    title: 'Loan-to-Value (LTV)',
    formula: 'RBI caps: ≤₹30L → 90%, ≤₹75L → 80%, >₹75L → 75%   CRE → 65–75%',
    desc: 'Maximum recommended loan as % of conservative market value. Our engine considers RPI, confidence, fraud flags and regulatory compliance to recommend an appropriate LTV.',
  },
  uncertainty: {
    title: 'Uncertainty Band (u)',
    formula: 'u = 8% + 10%×(1−Q_data) + 8%×(1−Q_agree) + 6%×P_fraud',
    desc: 'Width of the value range as % of point estimate. Minimum 8%; widens to 25% with missing data, poor source agreement, or fraud flags. Multiply point estimate by (1±u) for the range.',
  },

  // ── Driver labels (used by DriverBar tooltips) ──
  market_to_circle_ratio:    { title: 'Market-to-Circle Ratio', formula: 'Tier + bucket lookup, blended with LLM', desc: 'Real transaction premium over government floor rate. Single largest driver in most valuations.' },
  micro_location_adjustment: { title: 'Micro-Location Premium', formula: 'f_loc = 1 + 0.25×ΔS_infra + 0.15×ΔS_nbhd', desc: 'Fine-grain location quality vs expected for this micro-bucket. Powered by live OSM POI data.' },
  age_depreciation:          { title: 'Age & Condition Depreciation', formula: 'Exponential decay, LLM condition-adjusted', desc: 'Non-linear structure decay — land value is preserved. Older buildings with good maintenance get a small upward adjustment.' },
  config_factor:             { title: 'Configuration Standardness', formula: 'Elasticity penalty for size deviation', desc: 'Penalty for non-standard area vs locality modal unit. Standard-sized units are faster to sell.' },
  legal_factor:              { title: 'Legal & Title Factor', formula: 'Lookup by (ownership, title_clear)', desc: 'Disputed title or leasehold reduces collateral quality. Freehold with clear title = 1.00.' },
  floor_factor:              { title: 'Floor Adjustment', formula: 'Tiered by floor band and lift availability', desc: 'Ground-floor shops command premium. High floors without lift face marketability discount.' },
  regulatory_compliance:     { title: 'Regulatory Compliance', formula: '∏ haircut_i per compliance gap', desc: 'India-specific: missing OC, litigation, attachment order, RERA non-registration multiply to reduce value.' },
  macro_economic_adjustment: { title: 'Macro-Economic Adjustment', formula: 'repo_rate_impact × cycle_factor × seasonal_factor', desc: 'Overlays RBI repo rate environment, market cycle position and seasonal demand on the base valuation.' },
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
