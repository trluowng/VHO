import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { cycleApi } from '../lib/api.js'
import { Droplet } from './icons.jsx'

function formatVi(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export default function CycleTracker() {
  const { token } = useAuth()
  const [entries, setEntries] = useState([])
  const [prediction, setPrediction] = useState(null)
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
            <span className="cycle-summary__value">{formatVi(prediction?.predicted_next_period)}</span>
          </div>
        </div>
      </div>

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
