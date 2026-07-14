import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { Cross } from '../components/icons.jsx'

const GENDERS = [
  { value: 'nu', label: 'Nữ' },
  { value: 'nam', label: 'Nam' },
  { value: 'khac', label: 'Khác' },
]

export default function SignupPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [age, setAge] = useState('')
  const [gender, setGender] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function onSubmit(e) {
    e.preventDefault()
    if (!gender) {
      setError('Vui lòng chọn giới tính.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await register({ email, password, age: Number(age), gender })
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err.message || 'Đăng ký thất bại, thử lại nhé.')
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

        <h1 className="auth-card__title">Tạo tài khoản</h1>
        <p className="auth-card__lede">
          Lưu hồ sơ sức khỏe của bạn một lần — An sẽ nhớ để không hỏi lại tuổi, giới tính,
          bệnh nền mỗi lần trò chuyện.
        </p>

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
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Tối thiểu 6 ký tự"
              autoComplete="new-password"
            />
          </label>

          <label className="auth-field">
            <span>Tuổi</span>
            <input
              type="number"
              required
              min={1}
              max={119}
              value={age}
              onChange={(e) => setAge(e.target.value)}
              placeholder="vd: 28"
            />
          </label>

          <div className="auth-field">
            <span>Giới tính</span>
            <div className="gender-picker">
              {GENDERS.map((g) => (
                <button
                  type="button"
                  key={g.value}
                  className={`gender-chip ${gender === g.value ? 'is-active' : ''}`}
                  onClick={() => setGender(g.value)}
                >
                  {g.label}
                </button>
              ))}
            </div>
            {gender === 'nu' && (
              <p className="auth-field__hint">
                Tài khoản nữ sẽ tự động có thêm tab theo dõi chu kỳ kinh nguyệt trong mục Lịch.
              </p>
            )}
          </div>

          {error && <p className="auth-error">{error}</p>}

          <button className="btn btn--primary btn--lg auth-submit" type="submit" disabled={busy}>
            {busy ? 'Đang tạo tài khoản…' : 'Tạo tài khoản'}
          </button>
        </form>

        <p className="auth-card__switch">
          Đã có tài khoản? <Link to="/dang-nhap">Đăng nhập</Link>
        </p>
      </div>
    </div>
  )
}
