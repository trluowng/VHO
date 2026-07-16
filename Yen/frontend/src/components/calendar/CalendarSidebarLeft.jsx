import { CATEGORIES, categoryMeta } from '../../lib/calendarCategories.js'
import { Calendar as CalendarIcon, Edit, RefreshCw } from '../icons.jsx'

function formatUpcomingDate(iso) {
  const today = new Date()
  const todayIso = today.toISOString().slice(0, 10)
  const tomorrow = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1).toISOString().slice(0, 10)
  if (iso === todayIso) return 'Hôm nay'
  if (iso === tomorrow) return 'Ngày mai'
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export default function CalendarSidebarLeft({ activeFilter, onFilterChange, upcoming, onOpenModal }) {
  return (
    <aside className="cal-sidebar cal-sidebar--left">
      <button type="button" className="btn btn--primary cal-sidebar__new-btn" onClick={onOpenModal}>
        <Edit width={16} height={16} /> Đặt lịch mới
      </button>

      <div className="cal-sidebar__section">
        <h4 className="cal-sidebar__heading">
          <CalendarIcon width={14} height={14} /> Bộ lọc
        </h4>
        <div className="cal-sidebar__filters">
          <button
            className={`cal-filter-chip ${activeFilter === 'all' ? 'is-active' : ''}`}
            onClick={() => onFilterChange('all')}
          >
            Tất cả
          </button>
          {CATEGORIES.map((c) => (
            <button
              key={c.value}
              className={`cal-filter-chip ${activeFilter === c.value ? 'is-active' : ''}`}
              onClick={() => onFilterChange(c.value)}
            >
              <c.icon width={14} height={14} /> {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="cal-sidebar__section">
        <h4 className="cal-sidebar__heading">Sự kiện sắp tới</h4>
        {upcoming.length === 0 && <p className="empty-hint">Chưa có sự kiện nào sắp tới.</p>}
        <ul className="cal-upcoming-list">
          {upcoming.slice(0, 5).map((e) => {
            const meta = categoryMeta(e.type)
            return (
              <li key={e.id}>
                <span className="cal-upcoming-list__icon" style={{ color: meta.dot }}>
                  <meta.icon width={16} height={16} />
                </span>
                <span className="cal-upcoming-list__body">
                  <span className="cal-upcoming-list__title">{e.title}</span>
                  <span className="cal-upcoming-list__meta">
                    {formatUpcomingDate(e.entry_date)}{e.time_start ? ` · ${e.time_start}` : ''}
                  </span>
                </span>
              </li>
            )
          })}
        </ul>
      </div>

      <button type="button" className="btn btn--ghost cal-sidebar__sync-btn" disabled title="Sắp ra mắt">
        <RefreshCw width={15} height={15} />
        <span>
          Đồng bộ lịch
          <small>Kết nối với Google Calendar</small>
        </span>
      </button>
    </aside>
  )
}
