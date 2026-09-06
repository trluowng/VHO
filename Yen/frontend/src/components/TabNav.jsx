import { NavLink } from 'react-router-dom'
import { Chat, Calendar, Stethoscope, User } from './icons.jsx'

export default function TabNav() {
  return (
    <div className="topbar__right">
      <nav className="tabnav">
        <NavLink to="/app" end className={({ isActive }) => `tabnav__link ${isActive ? 'is-active' : ''}`}>
          <Chat width={16} height={16} /> Trò chuyện
        </NavLink>
        <NavLink to="/app/lich" className={({ isActive }) => `tabnav__link ${isActive ? 'is-active' : ''}`}>
          <Calendar width={16} height={16} /> Lịch
        </NavLink>
        <NavLink to="/app/dat-lich" className={({ isActive }) => `tabnav__link ${isActive ? 'is-active' : ''}`}>
          <Stethoscope width={16} height={16} /> Đặt lịch khám
        </NavLink>
        <NavLink to="/app/ho-so" className={({ isActive }) => `tabnav__link ${isActive ? 'is-active' : ''}`}>
          <User width={16} height={16} /> Hồ sơ
        </NavLink>
      </nav>
    </div>
  )
}
