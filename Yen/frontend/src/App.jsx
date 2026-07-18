import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext.jsx'
import RequireAuth from './components/RequireAuth.jsx'
import LandingPage from './pages/LandingPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import SignupPage from './pages/SignupPage.jsx'
import ChatPage from './pages/ChatPage.jsx'
import CalendarPage from './pages/CalendarPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import BookingPage from './pages/BookingPage.jsx'
import DoctorDetailPage from './pages/DoctorDetailPage.jsx'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dang-nhap" element={<LoginPage />} />
        <Route path="/dang-ky" element={<SignupPage />} />

        <Route element={<RequireAuth />}>
          <Route path="/app" element={<ChatPage />} />
          <Route path="/app/lich" element={<CalendarPage />} />
          <Route path="/app/dat-lich" element={<BookingPage />} />
          <Route path="/app/dat-lich/:doctorId" element={<DoctorDetailPage />} />
          <Route path="/app/ho-so" element={<ProfilePage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
