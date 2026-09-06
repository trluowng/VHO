import { Routes, Route, Navigate } from 'react-router-dom'
import { SessionProvider } from './context/SessionContext.jsx'
import LandingPage from './pages/LandingPage.jsx'
import ChatPage from './pages/ChatPage.jsx'
import CalendarPage from './pages/CalendarPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import BookingPage from './pages/BookingPage.jsx'
import DoctorDetailPage from './pages/DoctorDetailPage.jsx'

export default function App() {
  return (
    <SessionProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/app" element={<ChatPage />} />
        <Route path="/app/lich" element={<CalendarPage />} />
        <Route path="/app/dat-lich" element={<BookingPage />} />
        <Route path="/app/dat-lich/:doctorId" element={<DoctorDetailPage />} />
        <Route path="/app/ho-so" element={<ProfilePage />} />
        <Route path="/dang-nhap" element={<Navigate to="/app" replace />} />
        <Route path="/dang-ky" element={<Navigate to="/app" replace />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </SessionProvider>
  )
}
