import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { Cross } from '../components/icons.jsx'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login({ email, password })
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err.message || 'Đăng nhập thất bại, thử lại nhé.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="atmos">
        <div className="atmos__grain" />
        <div className="atmos__veil" />
      </div>

      <div className="auth-card">
        <Link to="/" className="brand auth-card__brand">
          <div className="brand__mark"><Cross /></div>
          <div className="brand__name">An<em> · sức khỏe</em></div>
        </Link>

        <h1 className="auth-card__title">Đăng nhập</h1>
        <p className="auth-card__lede">Tiếp tục trò chuyện với hồ sơ sức khỏe đã lưu của bạn.</p>

        <form className="auth-form" onSubmit={onSubmit}>
          <label className="auth-field">
            <span>Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ban@vidu.com"
              autoComplete="email"
            />
          </label>

          <label className="auth-field">
            <span>Mật khẩu</span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Mật khẩu của bạn"
              autoComplete="current-password"
            />
          </label>

          {error && <p className="auth-error">{error}</p>}

          <button className="btn btn--primary btn--lg auth-submit" type="submit" disabled={busy}>
            {busy ? 'Đang đăng nhập…' : 'Đăng nhập'}
          </button>
        </form>

        <p className="auth-card__switch">
          Chưa có tài khoản? <Link to="/dang-ky">Tạo tài khoản</Link>
        </p>
      </div>
    </div>
  )
}
