import { useState } from 'react'
import { useAuth } from '../../context/AuthContext.jsx'
import { calendarApi } from '../../lib/api.js'
import { CATEGORIES } from '../../lib/calendarCategories.js'
import { X } from '../icons.jsx'

export default function CalendarEntryModal({ date, onClose, onSaved }) {
  const { token } = useAuth()
  const [category, setCategory] = useState('kham_benh')
  const [title, setTitle] = useState('')
  const [timeStart, setTimeStart] = useState('')
  const [timeEnd, setTimeEnd] = useState('')
  const [doctor, setDoctor] = useState('')
  const [location, setLocation] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const showDoctorLocation = category === 'kham_benh' || category === 'xet_nghiem' || category === 'tiem_chung'

  async function submit(e) {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    setError(null)
    try {
      await calendarApi.create(token, {
        entry_date: date,
        type: category,
        title: title.trim(),
        note: note.trim() || null,
        time_start: timeStart || null,
        time_end: timeEnd || null,
        doctor: showDoctorLocation ? doctor.trim() || null : null,
        location: showDoctorLocation ? location.trim() || null : null,
      })
      onSaved()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="cal-modal__overlay" onClick={onClose}>
      <div className="cal-modal" onClick={(e) => e.stopPropagation()}>
        <div className="cal-modal__head">
          <h3>Đặt lịch mới</h3>
          <button type="button" className="cal-modal__close" onClick={onClose} aria-label="Đóng">
            <X width={16} height={16} />
          </button>
        </div>

        <form className="cal-modal__form" onSubmit={submit}>
          <label>
            <span>Loại</span>
            <div className="cal-modal__category-grid">
              {CATEGORIES.map((c) => (
                <button
                  type="button"
                  key={c.value}
                  className={`cal-modal__category-btn ${category === c.value ? 'is-active' : ''}`}
                  onClick={() => setCategory(c.value)}
                >
                  <c.icon width={16} height={16} />
                  {c.label}
                </button>
              ))}
            </div>
          </label>

          <label>
            <span>Tiêu đề</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="vd: Khám tim mạch định kỳ" required />
          </label>

          <label>
            <span>Ngày</span>
            <input type="date" value={date} disabled />
          </label>

          <div className="cal-modal__row">
            <label>
              <span>Giờ bắt đầu (tuỳ chọn)</span>
              <input type="time" value={timeStart} onChange={(e) => setTimeStart(e.target.value)} />
            </label>
            <label>
              <span>Giờ kết thúc (tuỳ chọn)</span>
              <input type="time" value={timeEnd} onChange={(e) => setTimeEnd(e.target.value)} />
            </label>
          </div>

          {showDoctorLocation && (
            <div className="cal-modal__row">
              <label>
                <span>Bác sĩ (tuỳ chọn)</span>
                <input value={doctor} onChange={(e) => setDoctor(e.target.value)} placeholder="vd: BS. Trần Minh Đức" />
              </label>
              <label>
                <span>Địa điểm (tuỳ chọn)</span>
                <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="vd: Phòng khám Tâm Anh" />
              </label>
            </div>
          )}

          <label>
            <span>Ghi chú (tuỳ chọn)</span>
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="vd: Nhịn ăn trước khi xét nghiệm" />
          </label>

          {error && <p className="auth-error">{error}</p>}

          <div className="cal-modal__actions">
            <button type="button" className="btn btn--ghost" onClick={onClose}>Huỷ</button>
            <button type="submit" className="btn btn--primary" disabled={busy}>Lưu lịch</button>
          </div>
        </form>
      </div>
    </div>
  )
}
