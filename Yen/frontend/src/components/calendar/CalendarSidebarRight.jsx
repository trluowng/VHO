import { categoryMeta } from '../../lib/calendarCategories.js'
import { ChevronRight, Clock, MapPin } from '../icons.jsx'

function formatDate(iso) {
  const today = new Date()
  const todayIso = today.toISOString().slice(0, 10)
  const tomorrow = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1).toISOString().slice(0, 10)
  if (iso === todayIso) return 'Hôm nay'
  if (iso === tomorrow) return 'Ngày mai'
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function AppointmentCard({ entry }) {
  const meta = categoryMeta(entry.type)
  return (
    <li className="cal-appt-card">
      <span className="cal-appt-card__badge">{formatDate(entry.entry_date)}</span>
      <div className="cal-appt-card__row">
        <span className="cal-appt-card__icon" style={{ color: meta.dot }}>
          <meta.icon width={18} height={18} />
        </span>
        <div className="cal-appt-card__body">
          <p className="cal-appt-card__title">{entry.title}</p>
          {entry.doctor && <p className="cal-appt-card__doctor">{entry.doctor}</p>}
          {(entry.time_start || entry.location) && (
            <p className="cal-appt-card__meta">
              {entry.time_start && (
                <span><Clock width={12} height={12} /> {entry.time_start}{entry.time_end ? ` - ${entry.time_end}` : ''}</span>
              )}
              {entry.location && <span><MapPin width={12} height={12} /> {entry.location}</span>}
            </p>
          )}
        </div>
        <ChevronRight width={16} height={16} className="cal-appt-card__chevron" />
      </div>
    </li>
  )
}

export default function CalendarSidebarRight({ appointments, followUps }) {
  return (
    <aside className="cal-sidebar cal-sidebar--right">
      <div className="cal-sidebar__section">
        <div className="cal-sidebar__section-head">
          <h4 className="cal-sidebar__heading">Lịch hẹn sắp tới</h4>
        </div>
        {appointments.length === 0 && <p className="empty-hint">Chưa có lịch hẹn nào sắp tới.</p>}
        <ul className="cal-appt-list">
          {appointments.slice(0, 4).map((e) => (
            <AppointmentCard key={e.id} entry={e} />
          ))}
        </ul>
      </div>

      <div className="cal-sidebar__section">
        <div className="cal-sidebar__section-head">
          <h4 className="cal-sidebar__heading">Tiêm chủng / Tái khám</h4>
        </div>
        {followUps.length === 0 && <p className="empty-hint">Chưa có lịch tiêm chủng/tái khám nào.</p>}
        <ul className="cal-appt-list">
          {followUps.slice(0, 4).map((e) => (
            <AppointmentCard key={e.id} entry={e} />
          ))}
        </ul>
      </div>
    </aside>
  )
}
