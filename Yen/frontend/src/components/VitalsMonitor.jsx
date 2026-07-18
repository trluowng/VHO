import { useEffect, useMemo, useRef, useState } from 'react'
import { Heart, Pulse } from './icons.jsx'

const HISTORY_LEN = 24
const HR_TICK_MS = 2200
const BP_TICK_MS = 4500

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function jitter(value, amount) {
  return value + (Math.random() * 2 - 1) * amount
}

/** Ước lượng mức nền huyết áp/nhịp tim theo hồ sơ (tuổi + bệnh nền) để mô phỏng
 * có ý nghĩa hơn là random hoàn toàn -- KHÔNG phải giá trị đo thật. */
function computeBaseline(profile) {
  const age = profile?.age ?? 30
  const conditions = (profile?.chronic_conditions || []).join(' ').toLowerCase()
  const hasHypertension = conditions.includes('huyết áp')
  const hasDiabetes = conditions.includes('đái tháo đường') || conditions.includes('tiểu đường')
  const hasCardiac = conditions.includes('tim')

  let sys = 116
  let dia = 75
  let hr = 74

  if (age >= 60) { sys += 10; dia += 4; hr -= 3 }
  else if (age <= 18) { hr += 12 }

  if (hasHypertension) { sys += 22; dia += 12 }
  if (hasDiabetes) { sys += 4; hr += 2 }
  if (hasCardiac) { hr += 6 }

  return { sys: Math.round(sys), dia: Math.round(dia), hr: Math.round(hr) }
}

function bpStatus(sys, dia) {
  if (sys >= 140 || dia >= 90) return { label: 'Cao', tone: 'red' }
  if (sys >= 120 || dia >= 80) return { label: 'Hơi cao', tone: 'amber' }
  return { label: 'Bình thường', tone: 'green' }
}

function hrStatus(hr) {
  if (hr < 60) return { label: 'Chậm', tone: 'amber' }
  if (hr > 100) return { label: 'Nhanh', tone: 'red' }
  return { label: 'Bình thường', tone: 'green' }
}

function Sparkline({ values, min, max }) {
  const points = useMemo(() => {
    if (values.length < 2) return ''
    const w = 100
    const h = 28
    const range = Math.max(1, max - min)
    return values
      .map((v, i) => {
        const x = (i / (values.length - 1)) * w
        const y = h - ((clamp(v, min, max) - min) / range) * h
        return `${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')
  }, [values, min, max])

  if (!points) return null
  return (
    <svg className="vitals-sparkline" viewBox="0 0 100 28" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function VitalsMonitor({ profile }) {
  const baseline = useMemo(() => computeBaseline(profile), [profile?.age, profile?.chronic_conditions])
  const baselineRef = useRef(baseline)
  baselineRef.current = baseline

  const [hr, setHr] = useState(baseline.hr)
  const [bp, setBp] = useState({ sys: baseline.sys, dia: baseline.dia })
  const [hrHistory, setHrHistory] = useState(() => Array(HISTORY_LEN).fill(baseline.hr))
  const [updatedAt, setUpdatedAt] = useState(() => new Date())

  useEffect(() => {
    // Đổi hồ sơ (đổi tài khoản) -> reset lại quanh baseline mới ngay lập tức.
    setHr(baselineRef.current.hr)
    setBp({ sys: baselineRef.current.sys, dia: baselineRef.current.dia })
    setHrHistory(Array(HISTORY_LEN).fill(baselineRef.current.hr))
  }, [baseline.hr, baseline.sys, baseline.dia])

  useEffect(() => {
    const hrTimer = setInterval(() => {
      setHr((prev) => {
        const next = Math.round(clamp(jitter(prev, 3), baselineRef.current.hr - 10, baselineRef.current.hr + 10))
        setHrHistory((history) => [...history.slice(1), next])
        return next
      })
      setUpdatedAt(new Date())
    }, HR_TICK_MS)

    const bpTimer = setInterval(() => {
      setBp(() => ({
        sys: Math.round(clamp(jitter(baselineRef.current.sys, 4), baselineRef.current.sys - 8, baselineRef.current.sys + 8)),
        dia: Math.round(clamp(jitter(baselineRef.current.dia, 3), baselineRef.current.dia - 6, baselineRef.current.dia + 6)),
      }))
      setUpdatedAt(new Date())
    }, BP_TICK_MS)

    return () => {
      clearInterval(hrTimer)
      clearInterval(bpTimer)
    }
  }, [])

  const hrState = hrStatus(hr)
  const bpState = bpStatus(bp.sys, bp.dia)
  const beatDuration = clamp(60 / Math.max(hr, 30), 0.5, 1.4).toFixed(2)

  return (
    <section className="panel vitals-monitor">
      <div className="panel__head">
        <p className="panel__label profile-card__title" style={{ margin: 0 }}>
          <Pulse width={17} height={17} /> Chỉ số sức khỏe
        </p>
        <span className="vitals-live">
          <i className="vitals-live__dot" /> Đang đo trực tiếp
        </span>
      </div>

      <div className="vitals-monitor__grid">
        <article className={`vitals-stat vitals-stat--${hrState.tone}`}>
          <span className="vitals-stat__icon" style={{ animationDuration: `${beatDuration}s` }}>
            <Heart width={20} height={20} />
          </span>
          <span className="vitals-stat__body">
            <small>Nhịp tim</small>
            <strong>{hr} <em>bpm</em></strong>
            <span className={`vitals-stat__tag vitals-stat__tag--${hrState.tone}`}>{hrState.label}</span>
          </span>
          <Sparkline values={hrHistory} min={baseline.hr - 12} max={baseline.hr + 12} />
        </article>

        <article className={`vitals-stat vitals-stat--${bpState.tone}`}>
          <span className="vitals-stat__icon"><Pulse width={20} height={20} /></span>
          <span className="vitals-stat__body">
            <small>Huyết áp</small>
            <strong>{bp.sys}/{bp.dia} <em>mmHg</em></strong>
            <span className={`vitals-stat__tag vitals-stat__tag--${bpState.tone}`}>{bpState.label}</span>
          </span>
        </article>
      </div>

      <p className="vitals-monitor__footnote">
        Cập nhật lúc {updatedAt.toLocaleTimeString('vi-VN')} · Dữ liệu mô phỏng để minh hoạ, không phải chỉ số đo từ thiết bị y tế thật.
      </p>
    </section>
  )
}
