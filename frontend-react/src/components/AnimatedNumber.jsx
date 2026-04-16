import { useState, useEffect, useRef } from 'react'

export default function AnimatedNumber({ value, duration = 1500, format, className = '' }) {
  const [display, setDisplay] = useState(0)
  const ref = useRef(null)
  const startRef = useRef(0)
  const startTimeRef = useRef(null)

  useEffect(() => {
    if (value === undefined || value === null) return
    const target = typeof value === 'number' ? value : parseFloat(value) || 0
    startRef.current = display
    startTimeRef.current = null

    const ease = (t) => 1 - Math.pow(1 - t, 3)

    const animate = (timestamp) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp
      const elapsed = timestamp - startTimeRef.current
      const progress = Math.min(elapsed / duration, 1)
      const eased = ease(progress)
      const current = startRef.current + (target - startRef.current) * eased
      setDisplay(current)
      if (progress < 1) ref.current = requestAnimationFrame(animate)
    }

    ref.current = requestAnimationFrame(animate)
    return () => { if (ref.current) cancelAnimationFrame(ref.current) }
  }, [value])

  const formatted = format ? format(display) : Math.round(display).toLocaleString('en-IN')

  return <span className={`num ${className}`}>{formatted}</span>
}
