import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { doctorsApi } from '../lib/api.js'
import { Calendar as CalendarIcon, ChevronRight, Clock, Cross, MapPin, Search, Shield, Stethoscope, X } from '../components/icons.jsx'
import TabNav from '../components/TabNav.jsx'
import BookingStepper from '../components/booking/BookingStepper.jsx'

const CAMPUSES = ['Cơ sở 1', 'Cơ sở 2']
const SPECIALTIES = ['Tim mạch', 'Nhi', 'Da liễu', 'Nội tổng quát']
const SPECIALTY_COLORS = {
  'Tim mạch': 'var(--cal-blue)',
  'Nhi': 'var(--green)',
  'Da liễu': 'var(--cal-purple)',
  'Nội tổng quát': 'var(--amber-warm)',
}

function formatSlotDate(iso) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' })
}

function doctorInitials(name = '') {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

function DoctorCard({ doctor }) {
  const color = SPECIALTY_COLORS[doctor.specialty] || 'var(--cal-blue)'

  return (
    <Link to={`/app/dat-lich/${doctor.id_doctor}`} className="booking-card booking-card--link">
      <div className="booking-card__head">
        <span className="booking-card__avatar" style={{ color, background: `color-mix(in srgb, ${color} 13%, white)` }}>
          {doctorInitials(doctor.full_name)}
        </span>
        <div className="booking-card__id">
          <p className="booking-card__name">{doctor.full_name}</p>
          <p className="booking-card__meta">{doctor.degree}</p>
        </div>
        <span className="booking-card__specialty" style={{ color, background: `color-mix(in srgb, ${color} 11%, white)` }}>
          {doctor.specialty}
        </span>
      </div>

      <p className="booking-card__location">
        <MapPin width={13} height={13} /> {doctor.campus} · {doctor.department}
      </p>

      {doctor.next_slots?.length > 0 ? (
        <div className="booking-card__availability">
          <span className="booking-card__availability-label">
            <CalendarIcon width={13} height={13} /> Lịch gần nhất
          </span>
          <div className="booking-card__slots">
            {doctor.next_slots.map((s, i) => (
              <span key={`${s.visit_date}-${s.time_slot}-${i}`} className="booking-slot">
                <strong>{formatSlotDate(s.visit_date)}</strong>
                <small><Clock width={10} height={10} /> {s.time_slot}</small>
              </span>
            ))}
          </div>
        </div>
      ) : (
        <p className="empty-hint">Hiện chưa có lịch trống.</p>
      )}

      <span className="booking-card__footer">
        <small>{doctor.available_count} khung giờ còn trống</small>
        <span className="booking-card__cta">Chọn bác sĩ <ChevronRight width={14} height={14} /></span>
      </span>
    </Link>
  )
}

export default function BookingPage() {
  const { token } = useAuth()
  const [rawQuery, setRawQuery] = useState('')
  const [query, setQuery] = useState('')
  const [campus, setCampus] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [doctors, setDoctors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Debounce ô tìm tên -- tránh gọi API mỗi lần gõ 1 ký tự.
  useEffect(() => {
    const t = setTimeout(() => setQuery(rawQuery.trim()), 300)
    return () => clearTimeout(t)
  }, [rawQuery])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const data = await doctorsApi.list(token, { query, campus, specialty })
        if (!cancelled) setDoctors(data.doctors || [])
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [token, query, campus, specialty])

  const resultCountLabel = useMemo(() => {
    if (loading) return 'Đang tải…'
    return `${doctors.length} bác sĩ`
  }, [loading, doctors.length])

  const availableSlotCount = useMemo(
    () => doctors.reduce((total, doctor) => total + (doctor.available_count || 0), 0),
    [doctors],
  )
  const hasFilters = Boolean(rawQuery || campus || specialty)

  function clearFilters() {
    setRawQuery('')
    setQuery('')
    setCampus('')
    setSpecialty('')
  }

  return (
    <>
      <div className="atmos">
        <div className="atmos__grain" />
        <div className="atmos__veil" />
      </div>

      <div className="shell shell--booking">
        <header className="topbar">
          <div className="brand">
            <div className="brand__mark"><Cross /></div>
            <div>
              <div className="brand__name">Yên<em> · sức khỏe</em></div>
              <div className="brand__sub">AI y tế cá nhân</div>
            </div>
          </div>
          <TabNav />
        </header>

        <div className="calendar-page__body">
          <div className="booking-page">
            <section className="booking-hero">
              <div>
                <span className="booking-hero__eyebrow"><Stethoscope width={14} height={14} /> Đặt lịch trực tuyến</span>
                <h1>Chọn bác sĩ phù hợp với bạn</h1>
                <p>Tìm theo chuyên khoa, cơ sở và khung giờ thuận tiện. Lịch hẹn sẽ tự động xuất hiện trong tab Lịch.</p>
              </div>
              <div className="booking-hero__trust">
                <Shield width={22} height={22} />
                <span><strong>Thông tin được bảo mật</strong><small>Xác nhận ngay trên tài khoản của bạn</small></span>
              </div>
            </section>

            <BookingStepper current={1} />

            <div className="booking-workspace">
              <aside className="booking-filter-panel">
                <div className="booking-filter-panel__head">
                  <div>
                    <strong>Bộ lọc tìm kiếm</strong>
                    <small>Chọn nhu cầu khám của bạn</small>
                  </div>
                  {hasFilters && <button type="button" onClick={clearFilters}>Đặt lại</button>}
                </div>

                <div className="booking-filter-block">
                  <span className="booking-filters__label">Chuyên khoa</span>
                  <div className="booking-specialties">
                    <button type="button" className={!specialty ? 'is-active' : ''} onClick={() => setSpecialty('')}>
                      <Stethoscope width={16} height={16} /><span><strong>Tất cả</strong><small>Mọi chuyên khoa</small></span>
                    </button>
                    {SPECIALTIES.map((item) => (
                      <button key={item} type="button" className={specialty === item ? 'is-active' : ''} onClick={() => setSpecialty(item)}>
                        <span className="booking-specialties__dot" style={{ background: SPECIALTY_COLORS[item] }} />
                        <span><strong>{item}</strong><small>Tìm bác sĩ {item.toLocaleLowerCase('vi-VN')}</small></span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="booking-filter-block">
                  <span className="booking-filters__label">Cơ sở khám</span>
                  <div className="booking-campus-options">
                    <button type="button" className={!campus ? 'is-active' : ''} onClick={() => setCampus('')}>Tất cả cơ sở</button>
                    {CAMPUSES.map((item) => (
                      <button key={item} type="button" className={campus === item ? 'is-active' : ''} onClick={() => setCampus(item)}>{item}</button>
                    ))}
                  </div>
                </div>
              </aside>

              <main className="booking-results">
                <div className="booking-search">
                  <div className="booking-search__input">
                    <Search width={18} height={18} />
                    <input
                      value={rawQuery}
                      onChange={(e) => setRawQuery(e.target.value)}
                      placeholder="Tìm theo tên bác sĩ…"
                    />
                    {rawQuery && (
                      <button type="button" onClick={() => setRawQuery('')} aria-label="Xoá từ khoá"><X width={15} height={15} /></button>
                    )}
                  </div>
                </div>

                <div className="booking-results__head">
                  <div>
                    <h2>Danh sách bác sĩ</h2>
                    <p>{resultCountLabel}{!loading && ` · ${availableSlotCount} khung giờ có thể đặt`}</p>
                  </div>
                  {(specialty || campus) && (
                    <div className="booking-results__active-filters">
                      {specialty && <span>{specialty}</span>}
                      {campus && <span>{campus}</span>}
                    </div>
                  )}
                </div>

                {error && <div className="booking-state booking-state--error"><p>{error}</p><button type="button" onClick={clearFilters}>Thử lại</button></div>}
                {!loading && !error && doctors.length === 0 && (
                  <div className="booking-state">
                    <Search width={28} height={28} />
                    <strong>Chưa tìm thấy bác sĩ phù hợp</strong>
                    <p>Hãy thử tên khác hoặc đặt lại bộ lọc.</p>
                    <button type="button" className="btn btn--ghost" onClick={clearFilters}>Đặt lại bộ lọc</button>
                  </div>
                )}
                {loading ? (
                  <div className="booking-results__grid" aria-label="Đang tải danh sách bác sĩ">
                    {[0, 1, 2, 3].map((item) => <div key={item} className="booking-card booking-card--skeleton" />)}
                  </div>
                ) : (
                  <div className="booking-results__grid">
                    {doctors.map((doctor) => <DoctorCard key={doctor.id_doctor} doctor={doctor} />)}
                  </div>
                )}
              </main>
            </div>

            <p className="cal-disclaimer">
              Yên là trợ lý hỗ trợ khách hàng của Bệnh viện Tim Hà Nội. Lịch hiển thị chỉ mang tính tham khảo, vui lòng gọi tổng đài để xác nhận trước khi đến khám.
            </p>
          </div>
        </div>
      </div>
    </>
  )
}
