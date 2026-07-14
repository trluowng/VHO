import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function RequireAuth() {
  const { ready, token } = useAuth()
  const location = useLocation()

  if (!ready) return null // đợi xác thực token đã lưu trước khi quyết định điều hướng
  if (!token) return <Navigate to="/dang-nhap" replace state={{ from: location }} />
  return <Outlet />
}
