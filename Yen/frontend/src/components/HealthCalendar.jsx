import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { calendarApi } from '../lib/api.js'
import { CATEGORIES, categoryMeta } from '../lib/calendarCategories.js'
import { toISODate, monthKey, buildMonthGrid } from '../lib/calendarGrid.js'
import { Calendar as CalendarIcon, Clock } from './icons.jsx'
import CalendarSidebarLeft from './calendar/CalendarSidebarLeft.jsx'
import CalendarSidebarRight from './calendar/CalendarSidebarRight.jsx'
import CalendarEntryModal from './calendar/CalendarEntryModal.jsx'

const WEEKDAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

export default function HealthCalendar() {
  const { token } = useAuth()
  const [cursor, setCursor] = useState(() => new Date())
  const [entries, setEntries] = useState([])
  const [selected, setSelected] = useState(() => toISODate(new Date()))
  const [filter, setFilter] = useState('all')
  const [modalDate, setModalDate] = useState(null)
  const [busy, setBusy] = useState(false)

  const key = monthKey(cursor)
  const todayIso = toISODate(new Date())
  const grid = useMemo(() => buildMonthGrid(cursor.getFullYear(), cursor.getMonth()), [cursor])

  async function load() {
    try {
      const data = await calendarApi.list(token, key)
      setEntries(data.entries)
    } catch {
      // giữ danh sách cũ nếu tải lỗi — không chặn giao diện
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  const entriesByDate = useMemo(() => {
    const map = {}
    for (const e of entries) (map[e.entry_date] ||= []).push(e)
    return map
  }, [entries])

  const filteredEntries = useMemo(
    () => (filter === 'all' ? entries : entries.filter((e) => e.type === filter)),
    [entries, filter],
  )

  const upcoming = useMemo(
    () => filteredEntries.filter((e) => e.entry_date >= todayIso).sort((a, b) => (a.entry_date + (a.time_start || '')).localeCompare(b.entry_date + (b.time_start || ''))),
    [filteredEntries, todayIso],
  )
  const appointments = useMemo(
    () => upcoming.filter((e) => e.type === 'kham_benh' || e.type === 'xet_nghiem'),
    [upcoming],
  )
  const followUps = useMemo(() => upcoming.filter((e) => e.type === 'tiem_chung'), [upcoming])

  const todayEntries = entriesByDate[todayIso] || []
  const monthLabel = cursor.toLocaleDateString('vi-VN', { month: 'long', year: 'numeric' })
  const selectedDate = new Date(selected + 'T00:00:00')
  const selectedEntries = (entriesByDate[selected] || []).filter((e) => filter === 'all' || e.type === filter)

  async function removeEntry(id) {
    setBusy(true)
    try {
      await calendarApi.remove(token, id)
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="cal-page">
      <CalendarSidebarLeft
        activeFilter={filter}
        onFilterChange={setFilter}
        upcoming={upcoming}
        onOpenModal={() => setModalDate(selected)}
      />

      <div className="cal-main">
        <div className="cal-main__toolbar">
          <div className="cal-main__nav">
            <button onClick={() => setCursor((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))} aria-label="Tháng trước">‹</button>
            <span className="cal-main__month">Tháng {cursor.getMonth() + 1}, {cursor.getFullYear()}</span>
            <button onClick={() => setCursor((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))} aria-label="Tháng sau">›</button>
          </div>
          <div className="cal-main__view-toggle">
            <button className="is-active">Tháng</button>
            <button disabled title="Sắp ra mắt">Tuần</button>
            <button disabled title="Sắp ra mắt">Danh sách</button>
          </div>
        </div>

        <div className="cal-grid">
          <div className="cal-grid__weekdays">
            {WEEKDAYS.map((w) => <span key={w}>{w}</span>)}
          </div>
          <div className="cal-grid__cells">
            {grid.map(({ date, inMonth }) => {
              const iso = toISODate(date)
              const dayEntries = entriesByDate[iso] || []
              const isToday = iso === todayIso
              const isSelected = iso === selected
              return (
                <button
                  key={iso}
                  className={`cal-grid__cell ${!inMonth ? 'is-muted' : ''} ${isSelected ? 'is-selected' : ''} ${isToday && !isSelected ? 'is-today' : ''}`}
                  onClick={() => setSelected(iso)}
                >
                  <span>{date.getDate()}</span>
                  {dayEntries.length > 0 && (
                    <span className="cal-grid__dots">
                      {dayEntries.slice(0, 3).map((e) => (
                        <i key={e.id} style={{ background: categoryMeta(e.type).dot }} />
                      ))}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        <div className="cal-legend">
          {CATEGORIES.map((c) => (
            <span key={c.value} className="cal-legend__item">
              <i style={{ background: c.dot }} /> {c.label}
            </span>
          ))}
        </div>

        <div className="cal-today-card">
          <span className="cal-today-card__icon"><CalendarIcon width={20} height={20} /></span>
          <div className="cal-today-card__body">
            <p className="cal-today-card__title">
              {selected === todayIso ? 'Hôm nay' : 'Ngày đã chọn'} - {selectedDate.toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' })}
            </p>
            <p className="cal-today-card__desc">
              {selected === todayIso
                ? (todayEntries.length > 0 ? `Bạn có ${todayEntries.length} lịch hẹn và nhắc nhở trong ngày.` : 'Bạn chưa có lịch hẹn hay nhắc nhở nào hôm nay.')
                : (selectedEntries.length > 0 ? `${selectedEntries.length} mục trong ngày này.` : 'Chưa có lịch hẹn hay nhắc nhở nào cho ngày này.')}
            </p>
          </div>
          <button type="button" className="btn btn--ghost cal-today-card__cta" onClick={() => setModalDate(selected)}>
            Thêm lịch cho ngày này →
          </button>
        </div>

        {selectedEntries.length > 0 && (
          <ul className="cal-day-list">
            {selectedEntries.map((e) => {
              const meta = categoryMeta(e.type)
              return (
                <li key={e.id}>
                  <span style={{ color: meta.dot }}><meta.icon width={16} height={16} /></span>
                  <span className="cal-day-list__body">
                    <span className="cal-day-list__title">{e.title}</span>
                    <span className="cal-day-list__meta">
                      {meta.label}
                      {e.time_start && <> · <Clock width={11} height={11} /> {e.time_start}</>}
                      {e.doctor && ` · ${e.doctor}`}
                    </span>
                  </span>
                  <button className="cycle-history__remove" onClick={() => removeEntry(e.id)} disabled={busy}>Xoá</button>
                </li>
              )
            })}
          </ul>
        )}

        <p className="cal-disclaimer">
          Yên là trợ lý hỗ trợ khách hàng của Bệnh viện Tim Hà Nội. Nội dung chỉ mang tính tham khảo, không thay thế chẩn đoán y khoa.
        </p>
      </div>

      <CalendarSidebarRight appointments={appointments} followUps={followUps} />

      {modalDate && (
        <CalendarEntryModal date={modalDate} onClose={() => setModalDate(null)} onSaved={load} />
      )}
    </div>
  )
}
