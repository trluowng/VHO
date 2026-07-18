import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { calendarApi } from '../lib/api.js'
import { CATEGORIES, categoryMeta } from '../lib/calendarCategories.js'
import { toISODate, monthKey, buildMonthGrid, addDays } from '../lib/calendarGrid.js'
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
  const [view, setView] = useState('month')
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

  // Nhắc thuốc là 1 đợt lặp lại (entry_date -> date_end, nhiều giờ/ngày), nên phải
  // xuất hiện trên MỌI ngày trong khoảng đó (lưới tháng + danh sách theo ngày),
  // không chỉ đúng entry_date như các loại sự kiện 1 ngày còn lại.
  const entriesByDate = useMemo(() => {
    const map = {}
    for (const e of entries) {
      if (e.type === 'thuoc' && e.date_end && e.date_end > e.entry_date) {
        for (let d = e.entry_date; d <= e.date_end; d = addDays(d, 1)) {
          (map[d] ||= []).push(e)
        }
      } else {
        (map[e.entry_date] ||= []).push(e)
      }
    }
    return map
  }, [entries])

  const filteredEntries = useMemo(
    () => (filter === 'all' ? entries : entries.filter((e) => e.type === filter)),
    [entries, filter],
  )

  // Nhắc thuốc "sắp tới" là những đợt CHƯA kết thúc (date_end >= hôm nay), không
  // chỉ những đợt bắt đầu từ hôm nay trở đi -- giữ nguyên entry_date thật (ngày
  // bắt đầu đợt) để sidebar bên phải hiển thị đúng khoảng ngày, việc quy đổi
  // "Hôm nay" cho hiển thị badge nằm ở AppointmentCard.
  const upcoming = useMemo(
    () => filteredEntries
      .filter((e) => (e.type === 'thuoc' ? (e.date_end || e.entry_date) >= todayIso : e.entry_date >= todayIso))
      .sort((a, b) => (a.entry_date + (a.time_start || (a.times && a.times[0]) || '')).localeCompare(b.entry_date + (b.time_start || (b.times && b.times[0]) || ''))),
    [filteredEntries, todayIso],
  )
  const appointments = useMemo(
    () => upcoming.filter((e) => e.type === 'kham_benh' || e.type === 'xet_nghiem'),
    [upcoming],
  )
  const followUps = useMemo(() => upcoming.filter((e) => e.type === 'tiem_chung'), [upcoming])
  const medications = useMemo(() => upcoming.filter((e) => e.type === 'thuoc'), [upcoming])

  const todayEntries = entriesByDate[todayIso] || []
  const selectedEntries = (entriesByDate[selected] || []).filter((e) => filter === 'all' || e.type === filter)
  const todayDate = new Date(todayIso + 'T00:00:00')
  const weekDates = useMemo(() => {
    const anchor = new Date(selected + 'T00:00:00')
    const mondayOffset = (anchor.getDay() + 6) % 7
    const monday = new Date(anchor)
    monday.setDate(anchor.getDate() - mondayOffset)
    return Array.from({ length: 7 }, (_, index) => {
      const date = new Date(monday)
      date.setDate(monday.getDate() + index)
      return date
    })
  }, [selected])
  const monthEntries = useMemo(
    () => [...filteredEntries].sort((a, b) => (
      a.entry_date + (a.time_start || a.times?.[0] || '')
    ).localeCompare(b.entry_date + (b.time_start || b.times?.[0] || ''))),
    [filteredEntries],
  )

  async function removeEntry(id) {
    setBusy(true)
    try {
      await calendarApi.remove(token, id)
      await load()
    } finally {
      setBusy(false)
    }
  }

  function jumpToToday() {
    const now = new Date()
    setCursor(new Date(now.getFullYear(), now.getMonth(), 1))
    setSelected(todayIso)
  }

  function moveMonth(offset) {
    const next = new Date(cursor.getFullYear(), cursor.getMonth() + offset, 1)
    setCursor(next)
    setSelected(toISODate(next))
  }

  function selectCalendarDay(date, inMonth) {
    setSelected(toISODate(date))
    if (!inMonth) setCursor(new Date(date.getFullYear(), date.getMonth(), 1))
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
            <button onClick={() => moveMonth(-1)} aria-label="Tháng trước">‹</button>
            <span className="cal-main__month">Tháng {cursor.getMonth() + 1}, {cursor.getFullYear()}</span>
            <button onClick={() => moveMonth(1)} aria-label="Tháng sau">›</button>
          </div>
          <div className="cal-main__view-toggle" role="group" aria-label="Kiểu hiển thị lịch">
            <button type="button" className={view === 'month' ? 'is-active' : ''} onClick={() => setView('month')}>Tháng</button>
            <button type="button" className={view === 'week' ? 'is-active' : ''} onClick={() => setView('week')}>Tuần</button>
            <button type="button" className={view === 'list' ? 'is-active' : ''} onClick={() => setView('list')}>Danh sách</button>
          </div>
        </div>

        {view === 'month' && (
          <div className="cal-grid">
            <div className="cal-grid__weekdays">
              {WEEKDAYS.map((w) => <span key={w}>{w}</span>)}
            </div>
            <div className="cal-grid__cells">
              {grid.map(({ date, inMonth }) => {
                const iso = toISODate(date)
                const dayEntries = entriesByDate[iso] || []
                const visibleDayEntries = dayEntries.filter((e) => filter === 'all' || e.type === filter)
                const firstMeta = visibleDayEntries[0] ? categoryMeta(visibleDayEntries[0].type) : null
                const isToday = iso === todayIso
                const isSelected = iso === selected
                return (
                  <button
                    key={iso}
                    className={`cal-grid__cell ${!inMonth ? 'is-muted' : ''} ${visibleDayEntries.length ? 'has-events' : ''} ${isSelected ? 'is-selected' : ''} ${isToday && !isSelected ? 'is-today' : ''}`}
                    style={firstMeta ? { '--cal-day-color': firstMeta.dot } : undefined}
                    onClick={() => selectCalendarDay(date, inMonth)}
                  >
                    <span className="cal-grid__day-number">{date.getDate()}</span>
                    {visibleDayEntries.length > 0 && (
                      <span className="cal-grid__dots">
                        {visibleDayEntries.slice(0, 3).map((e, index) => (
                          <i key={`${e.id}-${index}`} style={{ background: categoryMeta(e.type).dot }} />
                        ))}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {view === 'week' && (
          <div className="cal-week-view">
            {weekDates.map((date, index) => {
              const iso = toISODate(date)
              const dayEntries = (entriesByDate[iso] || []).filter((e) => filter === 'all' || e.type === filter)
              return (
                <button
                  type="button"
                  key={iso}
                  className={`cal-week-day ${iso === selected ? 'is-selected' : ''} ${iso === todayIso ? 'is-today' : ''}`}
                  onClick={() => setSelected(iso)}
                >
                  <span className="cal-week-day__name">{WEEKDAYS[index]}</span>
                  <strong>{date.getDate()}</strong>
                  <span className="cal-week-day__events">
                    {dayEntries.length === 0 && <small>Trống</small>}
                    {dayEntries.slice(0, 3).map((entry) => (
                      <i key={entry.id} style={{ '--entry-color': categoryMeta(entry.type).dot }}>
                        {entry.time_start || entry.times?.[0] || 'Cả ngày'} · {entry.title}
                      </i>
                    ))}
                  </span>
                </button>
              )
            })}
          </div>
        )}

        {view === 'list' && (
          <div className="cal-list-view">
            {monthEntries.length === 0 && <p className="empty-hint">Không có sự kiện phù hợp trong tháng này.</p>}
            {monthEntries.map((entry) => {
              const meta = categoryMeta(entry.type)
              const EntryIcon = meta.icon
              return (
                <button type="button" key={entry.id} className="cal-list-row" onClick={() => setSelected(entry.entry_date)}>
                  <span className="cal-list-row__date">
                    <strong>{new Date(entry.entry_date + 'T00:00:00').getDate()}</strong>
                    <small>Tháng {new Date(entry.entry_date + 'T00:00:00').getMonth() + 1}</small>
                  </span>
                  <span className="cal-list-row__icon" style={{ color: meta.dot, background: `color-mix(in srgb, ${meta.dot} 14%, transparent)` }}>
                    <EntryIcon width={17} height={17} />
                  </span>
                  <span className="cal-list-row__body">
                    <strong>{entry.title}</strong>
                    <small>{entry.doctor || entry.location || entry.note || meta.label}</small>
                  </span>
                  <span className="cal-list-row__time">{entry.time_start || entry.times?.join(', ') || 'Cả ngày'}</span>
                </button>
              )
            })}
          </div>
        )}

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
              Hôm nay - {todayDate.toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' })}
            </p>
            <p className="cal-today-card__desc">
              {todayEntries.length > 0 ? `Bạn có ${todayEntries.length} lịch hẹn và nhắc nhở trong ngày.` : 'Bạn chưa có lịch hẹn hay nhắc nhở nào hôm nay.'}
            </p>
          </div>
          <button type="button" className="btn btn--ghost cal-today-card__cta" onClick={jumpToToday}>
            Xem lịch hôm nay →
          </button>
        </div>

        {selectedEntries.length > 0 && (
          <ul className="cal-day-list">
            {selectedEntries.map((e) => {
              const meta = categoryMeta(e.type)
              return (
                <li key={e.id}>
                  <span
                    className="cal-day-list__icon"
                    style={{ color: meta.dot, background: `color-mix(in srgb, ${meta.dot} 16%, transparent)` }}
                  >
                    <meta.icon width={15} height={15} />
                  </span>
                  <span className="cal-day-list__body">
                    <span className="cal-day-list__title">{e.title}</span>
                    <span className="cal-day-list__meta">
                      {meta.label}
                      {e.times?.length > 0 && <> · <Clock width={11} height={11} /> {e.times.join(', ')}</>}
                      {e.time_start && <> · <Clock width={11} height={11} /> {e.time_start}</>}
                      {e.doctor && ` · ${e.doctor}`}
                      {e.type === 'thuoc' && e.note && ` · ${e.note}`}
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

      <CalendarSidebarRight
        appointments={appointments}
        medications={medications}
        followUps={followUps}
        onRemove={removeEntry}
        busy={busy}
      />

      {modalDate && (
        <CalendarEntryModal date={modalDate} onClose={() => setModalDate(null)} onSaved={load} />
      )}
    </div>
  )
}
