import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { Chat, Calendar, LogOut } from './icons.jsx'

export default function TabNav() {
  const { user, logout } = useAuth()

  return (
    <div className="topbar__right">
      <nav className="tabnav">
        <NavLink to="/app" end className={({ isActive }) => `tabnav__link ${isActive ? 'is-active' : ''}`}>
          <Chat width={16} height={16} /> Trò chuyện
        </NavLink>
        <NavLink to="/app/lich" className={({ isActive }) => `tabnav__link ${isActive ? 'is-active' : ''}`}>
          <Calendar width={16} height={16} /> Lịch
        </NavLink>
      </nav>
      {user && <span className="pill-note">{user.email}</span>}
      <button className="restart-btn" onClick={logout} title="Đăng xuất">
        <LogOut width={15} height={15} /> Đăng xuất
      </button>
    </div>
  )
}
