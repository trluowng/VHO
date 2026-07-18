import { categoryMeta } from '../../lib/calendarCategories.js'
import { Bell, Clock, MapPin, X } from '../icons.jsx'

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function formatShort(iso) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
}

function formatDate(iso) {
  const today = todayIso()
  const tomorrow = new Date(new Date(today + 'T00:00:00').getTime() + 86400000).toISOString().slice(0, 10)
  if (iso === today) return 'Hôm nay'
  if (iso === tomorrow) return 'Ngày mai'
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

/** Nhắc thuốc là 1 đợt (entry_date -> date_end): badge hiển thị "Hôm nay" nếu
 * đợt đang diễn ra hôm nay, ngược lại hiển thị theo ngày bắt đầu đợt. */
function badgeDate(entry) {
  if (entry.type === 'thuoc' && entry.date_end) {
    const today = todayIso()
    if (entry.entry_date <= today && today <= entry.date_end) return today
  }
  return entry.entry_date
}

function AppointmentCard({ entry, onRemove, busy }) {
  const meta = categoryMeta(entry.type)
  const subtitle = entry.doctor || entry.note
  const isMultiDayMedication = entry.type === 'thuoc' && entry.date_end && entry.date_end !== entry.entry_date
  return (
    <li className="cal-appt-card">
      <div className="cal-appt-card__top">
        <span
          className="cal-appt-card__badge"
          style={{ background: `color-mix(in srgb, ${meta.dot} 18%, transparent)`, color: meta.dot }}
        >
          {formatDate(badgeDate(entry))}
        </span>
        <button
          type="button"
          className="cal-appt-card__remove"
          onClick={() => onRemove(entry.id)}
          disabled={busy}
          aria-label="Xoá nhắc nhở"
          title="Xoá nhắc nhở"
        >
          <X width={13} height={13} />
        </button>
      </div>
      <div className="cal-appt-card__row">
        <span
          className="cal-appt-card__icon"
          style={{ color: meta.dot, background: `color-mix(in srgb, ${meta.dot} 16%, transparent)` }}
        >
          <meta.icon width={17} height={17} />
        </span>
        <div className="cal-appt-card__body">
          <p className="cal-appt-card__title">{entry.title}</p>
          {subtitle && <p className="cal-appt-card__doctor">{subtitle}</p>}
          {entry.time_start && (
            <p className="cal-appt-card__meta">
              <span><Clock width={12} height={12} /> {entry.time_start}{entry.time_end ? ` - ${entry.time_end}` : ''}</span>
              {entry.location && <span><MapPin width={12} height={12} /> {entry.location}</span>}
            </p>
          )}
          {!entry.time_start && entry.location && (
            <p className="cal-appt-card__meta"><span><MapPin width={12} height={12} /> {entry.location}</span></p>
          )}
          {entry.times?.length > 0 && (
            <ul className="cal-appt-card__times">
              {entry.times.map((t, i) => (
                <li key={i}><Clock width={11} height={11} /> Lần {i + 1}: {t}</li>
              ))}
            </ul>
          )}
          {isMultiDayMedication && (
            <p className="cal-appt-card__range">Từ {formatShort(entry.entry_date)} đến {formatShort(entry.date_end)}</p>
          )}
        </div>
      </div>
    </li>
  )
}

function MedicationCard({ entry, onRemove, busy }) {
  const meta = categoryMeta(entry.type)
  const times = entry.times?.length ? entry.times : [entry.time_start].filter(Boolean)
  const isMultiDay = entry.date_end && entry.date_end !== entry.entry_date

  return (
    <li className="cal-med-card">
      <span
        className="cal-med-card__icon"
        style={{ color: meta.dot, background: `color-mix(in srgb, ${meta.dot} 14%, white)` }}
      >
        <meta.icon width={18} height={18} />
      </span>

      <div className="cal-med-card__body">
        <div className="cal-med-card__head">
          <div className="cal-med-card__name">
            <p>{entry.title}</p>
            {entry.note && <small>{entry.note}</small>}
          </div>
          <span
            className="cal-med-card__badge"
            style={{ background: `color-mix(in srgb, ${meta.dot} 16%, white)`, color: meta.dot }}
          >
            {formatDate(badgeDate(entry))}
          </span>
        </div>

        {times.length > 0 && (
          <div className="cal-med-card__times" aria-label="Giờ uống thuốc">
            {times.map((time, index) => (
              <span key={`${time}-${index}`}><Clock width={11} height={11} /> {time}</span>
            ))}
          </div>
        )}

        <p className="cal-med-card__range">
          {isMultiDay
            ? `Từ ${formatShort(entry.entry_date)} đến ${formatShort(entry.date_end)}`
            : `Ngày ${formatShort(entry.entry_date)}`}
        </p>
      </div>

      <span className="cal-med-card__bell" aria-hidden="true"><Bell width={16} height={16} /></span>
      <button
        type="button"
        className="cal-med-card__remove"
        onClick={() => onRemove(entry.id)}
        disabled={busy}
        aria-label={`Xoá nhắc uống ${entry.title}`}
        title="Xoá nhắc uống thuốc"
      >
        <X width={14} height={14} />
      </button>
    </li>
  )
}

export default function CalendarSidebarRight({ appointments, medications, followUps, onRemove, busy }) {
  return (
    <aside className="cal-sidebar cal-sidebar--right">
      <div className="cal-sidebar__section">
        <div className="cal-sidebar__section-head">
          <h4 className="cal-sidebar__heading">Lịch hẹn sắp tới</h4>
          <span className="cal-sidebar__view-all">Xem tất cả</span>
        </div>
        {appointments.length === 0 && <p className="empty-hint">Chưa có lịch hẹn nào sắp tới.</p>}
        <ul className="cal-appt-list">
          {appointments.slice(0, 4).map((e) => (
            <AppointmentCard key={e.id} entry={e} onRemove={onRemove} busy={busy} />
          ))}
        </ul>
      </div>

      <div className="cal-sidebar__section cal-sidebar__section--medications">
        <div className="cal-sidebar__section-head">
          <h4 className="cal-sidebar__heading">Nhắc uống thuốc</h4>
          <span className="cal-sidebar__view-all">Xem tất cả</span>
        </div>
        {medications.length === 0 && <p className="empty-hint">Chưa có nhắc uống thuốc nào.</p>}
        <ul className="cal-appt-list">
          {medications.slice(0, 4).map((e) => (
            <MedicationCard key={e.id} entry={e} onRemove={onRemove} busy={busy} />
          ))}
        </ul>
      </div>

      <div className="cal-sidebar__section">
        <div className="cal-sidebar__section-head">
          <h4 className="cal-sidebar__heading">Tiêm chủng / Tái khám</h4>
          <span className="cal-sidebar__view-all">Xem tất cả</span>
        </div>
        {followUps.length === 0 && <p className="empty-hint">Chưa có lịch tiêm chủng/tái khám nào.</p>}
        <ul className="cal-appt-list">
          {followUps.slice(0, 4).map((e) => (
            <AppointmentCard key={e.id} entry={e} onRemove={onRemove} busy={busy} />
          ))}
        </ul>
      </div>
    </aside>
  )
}
