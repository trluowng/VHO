import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { calendarApi } from '../lib/api.js'

const WEEKDAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
const TYPE_LABEL = { note: 'Ghi chú', measurement: 'Đo lường', reminder: 'Nhắc nhở' }
const TYPE_DOT = { note: 'var(--sage)', measurement: 'var(--amber-warm)', reminder: 'var(--clay)' }

function pad(n) {
  return String(n).padStart(2, '0')
}
function toISODate(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function monthKey(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`
}

function buildGrid(year, month) {
  // month: 0-based. Lưới bắt đầu từ Thứ 2.
  const first = new Date(year, month, 1)
  const startOffset = (first.getDay() + 6) % 7 // 0 = Thứ 2
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells = []
  for (let i = 0; i < startOffset; i++) cells.push(null)
  for (let day = 1; day <= daysInMonth; day++) cells.push(new Date(year, month, day))
  return cells
}

export default function HealthCalendar() {
  const { token } = useAuth()
  const [cursor, setCursor] = useState(() => new Date())
  const [entries, setEntries] = useState([])
  const [selected, setSelected] = useState(() => toISODate(new Date()))
  const [title, setTitle] = useState('')
  const [type, setType] = useState('note')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const key = monthKey(cursor)
  const grid = useMemo(() => buildGrid(cursor.getFullYear(), cursor.getMonth()), [cursor])
  const entriesByDate = useMemo(() => {
    const map = {}
    for (const e of entries) (map[e.entry_date] ||= []).push(e)
    return map
  }, [entries])

  async function load() {
    try {
      const data = await calendarApi.list(token, key)
      setEntries(data.entries)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  async function addEntry(e) {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    setError(null)
    try {
      await calendarApi.create(token, { entry_date: selected, type, title: title.trim(), note: note || null })
      setTitle('')
      setNote('')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function removeEntry(id) {
    setBusy(true)
    try {
      await calendarApi.remove(token, id)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const selectedEntries = entriesByDate[selected] || []
  const monthLabel = cursor.toLocaleDateString('vi-VN', { month: 'long', year: 'numeric' })

  return (
    <div className="calendar">
      <div className="calendar__grid-panel">
        <div className="calendar__nav">
          <button onClick={() => setCursor((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))}>‹</button>
          <span className="calendar__month">{monthLabel}</span>
          <button onClick={() => setCursor((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))}>›</button>
        </div>
        <div className="calendar__weekdays">
          {WEEKDAYS.map((w) => (
            <span key={w}>{w}</span>
          ))}
        </div>
        <div className="calendar__cells">
          {grid.map((d, i) => {
            if (!d) return <span key={i} className="calendar__cell is-empty" />
            const iso = toISODate(d)
            const dayEntries = entriesByDate[iso] || []
            const isToday = iso === toISODate(new Date())
            const isSelected = iso === selected
            return (
              <button
                key={iso}
                className={`calendar__cell ${isSelected ? 'is-selected' : ''} ${isToday ? 'is-today' : ''}`}
                onClick={() => setSelected(iso)}
              >
                <span>{d.getDate()}</span>
                {dayEntries.length > 0 && (
                  <span className="calendar__dots">
                    {dayEntries.slice(0, 3).map((e) => (
                      <i key={e.id} style={{ background: TYPE_DOT[e.type] }} />
                    ))}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      <div className="calendar__side">
        <h3 className="panel__label">
          {new Date(selected + 'T00:00:00').toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit' })}
        </h3>

        <ul className="calendar__entries">
          {selectedEntries.length === 0 && <li className="empty-hint">Chưa có mục nào cho ngày này.</li>}
          {selectedEntries.map((e) => (
            <li key={e.id}>
              <span className="calendar__entry-dot" style={{ background: TYPE_DOT[e.type] }} />
              <span className="calendar__entry-body">
                <span className="calendar__entry-title">{e.title}</span>
                <span className="calendar__entry-type">{TYPE_LABEL[e.type]}{e.note ? ` · ${e.note}` : ''}</span>
              </span>
              <button className="cycle-history__remove" onClick={() => removeEntry(e.id)} disabled={busy}>Xoá</button>
            </li>
          ))}
        </ul>

        <form className="calendar__form" onSubmit={addEntry}>
          <label>
            <span>Tiêu đề</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="vd: Uống thuốc huyết áp" required />
          </label>
          <label>
            <span>Loại</span>
            <select value={type} onChange={(e) => setType(e.target.value)}>
              <option value="note">Ghi chú</option>
              <option value="measurement">Đo lường</option>
              <option value="reminder">Nhắc nhở</option>
            </select>
          </label>
          <label>
            <span>Chi tiết (tuỳ chọn)</span>
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="vd: 120/80 mmHg" />
          </label>
          {error && <p className="auth-error">{error}</p>}
          <button className="btn btn--primary" type="submit" disabled={busy}>Thêm vào lịch</button>
        </form>
      </div>
    </div>
  )
}
