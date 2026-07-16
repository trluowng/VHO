import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { cycleApi } from '../lib/api.js'
import { toISODate, buildMonthGrid } from '../lib/calendarGrid.js'
import { Droplet, Info } from './icons.jsx'

const WEEKDAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

function formatVi(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function addDaysIso(iso, days) {
  const d = new Date(iso + 'T00:00:00')
  d.setDate(d.getDate() + days)
  return toISODate(d)
}

function inRange(iso, start, end) {
  return start && end && iso >= start && iso <= end
}

/** Ngày kinh (đã ghi nhận hoặc dự đoán) > cửa sổ dễ thụ thai > còn lại là ngày an toàn. */
function classifyDay(iso, entries, prediction) {
  const periodLen = prediction?.period_length_days || 5
  for (const e of entries) {
    if (inRange(iso, e.period_start_date, addDaysIso(e.period_start_date, periodLen - 1))) return 'period'
  }
  if (inRange(iso, prediction?.predicted_period_start, prediction?.predicted_period_end)) return 'period-predicted'
  if (inRange(iso, prediction?.fertile_window_start, prediction?.fertile_window_end)) return 'fertile'
  return 'safe'
}

const DOT_CLASS = {
  period: 'cycle-grid__dot--period',
  'period-predicted': 'cycle-grid__dot--period-predicted',
  fertile: 'cycle-grid__dot--fertile',
  safe: 'cycle-grid__dot--safe',
}

export default function CycleTracker() {
  const { token } = useAuth()
  const [entries, setEntries] = useState([])
  const [prediction, setPrediction] = useState(null)
  const [cursor, setCursor] = useState(() => new Date())
  const [newDate, setNewDate] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [loaded, setLoaded] = useState(false)

  async function load() {
    try {
      const data = await cycleApi.list(token)
      setEntries(data.entries)
      setPrediction(data.prediction)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoaded(true)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function addEntry(e) {
    e.preventDefault()
    if (!newDate) return
    setBusy(true)
    setError(null)
    try {
      const data = await cycleApi.create(token, { period_start_date: newDate, note: note || null })
      setEntries(data.entries)
      setPrediction(data.prediction)
      setNewDate('')
      setNote('')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function removeEntry(id) {
    setBusy(true)
    try {
      const data = await cycleApi.remove(token, id)
      setEntries(data.entries)
      setPrediction(data.prediction)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const grid = useMemo(() => buildMonthGrid(cursor.getFullYear(), cursor.getMonth()), [cursor])
  const todayIso = toISODate(new Date())
  const hasData = entries.length > 0

  if (!loaded) return null

  return (
    <div className="cycle-tracker">
      <div className="cycle-summary">
        <div className="cycle-summary__icon"><Droplet width={22} height={22} /></div>
        <div className="cycle-summary__grid">
          <div>
            <span className="cycle-summary__label">Đang ở ngày</span>
            <span className="cycle-summary__value">
              {prediction?.current_cycle_day ?? '—'}
              {prediction?.average_cycle_length_days ? ` / ${prediction.average_cycle_length_days}` : ''}
            </span>
          </div>
          <div>
            <span className="cycle-summary__label">Kỳ gần nhất</span>
            <span className="cycle-summary__value">{formatVi(prediction?.last_period_start_date)}</span>
          </div>
          <div>
            <span className="cycle-summary__label">Dự đoán kỳ tới</span>
            <span className="cycle-summary__value">
              {prediction?.predicted_period_start ? `${formatVi(prediction.predicted_period_start)} - ${formatVi(prediction.predicted_period_end)}` : '—'}
            </span>
          </div>
        </div>
      </div>

      {hasData && (
        <div className="cycle-grid-panel">
          <div className="cycle-grid-panel__nav">
            <button onClick={() => setCursor((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))} aria-label="Tháng trước">‹</button>
            <span>Tháng {cursor.getMonth() + 1}, {cursor.getFullYear()}</span>
            <button onClick={() => setCursor((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))} aria-label="Tháng sau">›</button>
          </div>

          <div className="cycle-grid__weekdays">
            {WEEKDAYS.map((w) => <span key={w}>{w}</span>)}
          </div>
          <div className="cycle-grid__cells">
            {grid.map(({ date, inMonth }) => {
              const iso = toISODate(date)
              const kind = classifyDay(iso, entries, prediction)
              const isToday = iso === todayIso
              return (
                <span key={iso} className={`cycle-grid__cell ${!inMonth ? 'is-muted' : ''} ${isToday ? 'is-today' : ''}`}>
                  <span>{date.getDate()}</span>
                  <i className={`cycle-grid__dot ${DOT_CLASS[kind]}`} />
                </span>
              )
            })}
          </div>

          <div className="cycle-legend">
            <span className="cycle-legend__item"><i className="cycle-grid__dot--period" /> Ngày hành kinh</span>
            <span className="cycle-legend__item"><i className="cycle-grid__dot--period-predicted" /> Dự đoán kỳ tới</span>
            <span className="cycle-legend__item"><i className="cycle-grid__dot--fertile" /> Cửa sổ dễ thụ thai</span>
            <span className="cycle-legend__item"><i className="cycle-grid__dot--safe" /> Ngày an toàn (ước lượng)</span>
          </div>

          <div className="cycle-disclaimer">
            <Info width={14} height={14} />
            <span>
              Đây là ước lượng dựa trên độ dài chu kỳ trung bình đã ghi nhận, có thể lệch nếu chu
              kỳ không đều. <strong>Không dùng để tránh thai</strong> — nếu cần biện pháp tránh
              thai đáng tin cậy, hãy hỏi ý kiến bác sĩ.
            </span>
          </div>
        </div>
      )}

      <form className="cycle-form" onSubmit={addEntry}>
        <label>
          <span>Ngày bắt đầu kỳ kinh</span>
          <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)} required />
        </label>
        <label>
          <span>Ghi chú (tuỳ chọn)</span>
          <input type="text" value={note} onChange={(e) => setNote(e.target.value)} placeholder="vd: đau bụng nhẹ" />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>Ghi nhận</button>
      </form>

      {error && <p className="auth-error">{error}</p>}

      <ul className="cycle-history">
        {entries.length === 0 && <li className="empty-hint">Chưa có dữ liệu chu kỳ nào — ghi nhận kỳ kinh gần nhất để bắt đầu dự đoán.</li>}
        {entries.map((e) => (
          <li key={e.id}>
            <span className="cycle-history__dot" />
            <span className="cycle-history__date">{formatVi(e.period_start_date)}</span>
            {e.note && <span className="cycle-history__note">{e.note}</span>}
            <button className="cycle-history__remove" onClick={() => removeEntry(e.id)} disabled={busy}>Xoá</button>
          </li>
        ))}
      </ul>
    </div>
  )
}
