import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { doctorsApi } from '../lib/api.js'
import {
  ArrowRight,
  Calendar as CalendarIcon,
  Check,
  Clock,
  Cross,
  Info,
  MapPin,
  Phone,
  Shield,
  Stethoscope,
  User,
  X,
} from '../components/icons.jsx'
import TabNav from '../components/TabNav.jsx'
import BookingStepper from '../components/booking/BookingStepper.jsx'

function formatGroupDate(iso) {
  const date = new Date(`${iso}T00:00:00`)
  return date.toLocaleDateString('vi-VN', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

function formatDateTab(iso) {
  const date = new Date(`${iso}T00:00:00`)
  return {
    weekday: date.toLocaleDateString('vi-VN', { weekday: 'short' }),
    day: date.toLocaleDateString('vi-VN', { day: '2-digit' }),
    month: date.toLocaleDateString('vi-VN', { month: '2-digit' }),
  }
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

export default function DoctorDetailPage() {
  const { doctorId } = useParams()
  const [searchParams] = useSearchParams()
  const preferredTimeSlot = searchParams.get('time_slot') || ''
  const { token, user, profile } = useAuth()
  const [doctor, setDoctor] = useState(null)
  const [slots, setSlots] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [selected, setSelected] = useState(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [booking, setBooking] = useState(false)
  const [bookError, setBookError] = useState(null)
  const [booked, setBooked] = useState(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await doctorsApi.schedule(token, doctorId)
      setDoctor(data.doctor)
      setSlots(data.slots || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, doctorId])

  const groups = useMemo(() => {
    const map = new Map()
    for (const slot of slots) {
      if (!map.has(slot.visit_date)) map.set(slot.visit_date, [])
      map.get(slot.visit_date).push(slot)
    }
    return [...map.entries()].sort(([first], [second]) => first.localeCompare(second))
  }, [slots])

  useEffect(() => {
    if (groups.length === 0) {
      setSelectedDate('')
      return
    }
    if (!groups.some(([date]) => date === selectedDate)) {
      const preferredGroup = preferredTimeSlot
        ? groups.find(([, groupSlots]) => groupSlots.some((slot) => slot.time_slot === preferredTimeSlot))
        : null
      setSelectedDate(preferredGroup?.[0] || groups[0][0])
    }
  }, [groups, preferredTimeSlot, selectedDate])

  const visibleSlots = useMemo(
    () => groups.find(([date]) => date === selectedDate)?.[1] || [],
    [groups, selectedDate],
  )

  function pickDate(date) {
    setSelectedDate(date)
    setSelected(null)
    setBooked(null)
    setBookError(null)
  }

  function pickSlot(slot) {
    setSelected(slot)
    setBooked(null)
    setBookError(null)
  }

  function openConfirmation() {
    if (!selected) return
    setBookError(null)
    setConfirmOpen(true)
  }

  async function confirmBooking() {
    if (!selected) return
    setBooking(true)
    setBookError(null)
    try {
      const result = await doctorsApi.book(token, doctorId, {
        visit_date: selected.visit_date,
        time_slot: selected.time_slot,
      })
      setBooked({ ...selected, emailNotification: result.email_notification })
      setSelected(null)
      setConfirmOpen(false)
      await load()
    } catch (err) {
      setBookError(err.message)
      if (err.detail === 'slot_already_booked' || err.detail === 'slot_not_found') {
        await load()
        setSelected(null)
        setConfirmOpen(false)
      }
    } finally {
      setBooking(false)
    }
  }

  const step = booked ? 3 : (confirmOpen ? 3 : 2)

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
          <div className="booking-page booking-page--detail">
            <div className="doctor-flow__top">
              <Link to="/app/dat-lich" className="doctor-page__back">← Quay lại danh sách bác sĩ</Link>
              <BookingStepper current={step} complete={Boolean(booked)} />
            </div>

            {loading && !doctor && (
              <div className="booking-state booking-state--loading"><span className="booking-spinner" /> Đang tải lịch khám…</div>
            )}
            {error && <div className="booking-state booking-state--error"><p>{error}</p><button type="button" onClick={load}>Tải lại</button></div>}

            {booked && doctor && (
              <section className="doctor-booking-success">
                <span className="doctor-booking-success__icon"><Check width={24} height={24} /></span>
                <div>
                  <strong>Đặt lịch khám thành công</strong>
                  <p>{formatGroupDate(booked.visit_date)} · {booked.time_slot} với {doctor.full_name}</p>
                  {booked.emailNotification === 'sent' && (
                    <small className="doctor-booking-success__email">Email xác nhận đã được gửi tới {user?.email}.</small>
                  )}
                  {(booked.emailNotification === 'failed' || booked.emailNotification === 'disabled') && (
                    <small className="doctor-booking-success__email is-error" role="alert">
                      Không thể gửi email xác nhận. Lịch khám vẫn đã được lưu trong tab Lịch.
                    </small>
                  )}
                </div>
                <Link to="/app/lich" state={{ focusDate: booked.visit_date }}>
                  Xem trong tab Lịch <ArrowRight width={14} height={14} />
                </Link>
              </section>
            )}

            {doctor && (
              <div className="doctor-booking-layout">
                <aside className="doctor-profile-card">
                  <span className="doctor-profile-card__avatar">{doctorInitials(doctor.full_name)}</span>
                  <span className="doctor-profile-card__specialty"><Stethoscope width={13} height={13} /> {doctor.specialty}</span>
                  <h1>{doctor.full_name}</h1>
                  <p className="doctor-profile-card__degree">{doctor.degree}</p>

                  <div className="doctor-profile-card__facts">
                    <span><MapPin width={16} height={16} /><span><small>Cơ sở khám</small><strong>{doctor.campus}</strong></span></span>
                    <span><Stethoscope width={16} height={16} /><span><small>Khoa/Phòng</small><strong>{doctor.department} · {doctor.room}</strong></span></span>
                    <span><CalendarIcon width={16} height={16} /><span><small>Lịch còn trống</small><strong>{slots.length} khung giờ</strong></span></span>
                  </div>

                  <div className="doctor-profile-card__notice">
                    <Shield width={16} height={16} />
                    <span><strong>Đặt lịch an toàn</strong><small>Bạn có thể quản lý lịch hẹn trong tab Lịch.</small></span>
                  </div>
                </aside>

                <main className="doctor-schedule-card">
                  <div className="doctor-schedule-card__head">
                    <div>
                      <span>Bước 2/3</span>
                      <h2>Chọn ngày và giờ khám</h2>
                      <p>Các khung giờ dưới đây được cập nhật theo lịch trống hiện tại.</p>
                    </div>
                    <span className="doctor-schedule-card__live"><i /> Lịch trực tuyến</span>
                  </div>

                  {bookError && !confirmOpen && <p className="auth-error doctor-schedule-card__error">{bookError}</p>}

                  {groups.length === 0 && !loading ? (
                    <div className="booking-state">
                      <CalendarIcon width={28} height={28} />
                      <strong>Bác sĩ hiện chưa có lịch trống</strong>
                      <p>Vui lòng quay lại chọn bác sĩ khác.</p>
                      <Link to="/app/dat-lich" className="btn btn--ghost">Chọn bác sĩ khác</Link>
                    </div>
                  ) : (
                    <>
                      <div className="doctor-date-tabs" role="tablist" aria-label="Chọn ngày khám">
                        {groups.map(([date, daySlots]) => {
                          const label = formatDateTab(date)
                          return (
                            <button
                              key={date}
                              type="button"
                              role="tab"
                              aria-selected={selectedDate === date}
                              className={selectedDate === date ? 'is-active' : ''}
                              onClick={() => pickDate(date)}
                            >
                              <small>{label.weekday}</small>
                              <strong>{label.day}/{label.month}</strong>
                              <em>{daySlots.length} giờ trống</em>
                            </button>
                          )
                        })}
                      </div>

                      <div className="doctor-time-section">
                        <div className="doctor-time-section__head">
                          <strong>{selectedDate && formatGroupDate(selectedDate)}</strong>
                          <small>Chọn một khung giờ phù hợp</small>
                        </div>
                        <div className="doctor-time-grid">
                          {visibleSlots.map((slot, index) => {
                            const isSelected = selected?.visit_date === slot.visit_date && selected?.time_slot === slot.time_slot
                            return (
                              <button
                                key={`${slot.time_slot}-${index}`}
                                type="button"
                                className={isSelected ? 'is-selected' : ''}
                                onClick={() => pickSlot(slot)}
                              >
                                <Clock width={15} height={15} />
                                <span><strong>{slot.time_slot}</strong><small>Còn trống</small></span>
                                {isSelected && <Check width={14} height={14} />}
                              </button>
                            )
                          })}
                        </div>
                      </div>

                      <div className={`doctor-selection-summary ${selected ? 'has-selection' : ''}`}>
                        {selected ? (
                          <>
                            <span className="doctor-selection-summary__icon"><CalendarIcon width={18} height={18} /></span>
                            <span className="doctor-selection-summary__copy">
                              <small>Lịch bạn đã chọn</small>
                              <strong>{formatGroupDate(selected.visit_date)} · {selected.time_slot}</strong>
                              <em>{selected.campus} · {selected.room}</em>
                            </span>
                            <button type="button" className="btn btn--primary" onClick={openConfirmation}>
                              Tiếp tục xác nhận <ArrowRight width={14} height={14} />
                            </button>
                          </>
                        ) : (
                          <><Info width={16} height={16} /><span>Chọn một khung giờ để tiếp tục đặt lịch.</span></>
                        )}
                      </div>
                    </>
                  )}
                </main>
              </div>
            )}

            <p className="cal-disclaimer">
              Yên là trợ lý hỗ trợ khách hàng của Bệnh viện Tim Hà Nội. Vui lòng đến sớm 15 phút và mang theo giấy tờ tùy thân, thẻ BHYT nếu có.
            </p>
          </div>
        </div>
      </div>

      {confirmOpen && selected && (
        <div className="cal-modal__overlay doctor-confirm-overlay" onClick={() => !booking && setConfirmOpen(false)}>
          <div className="cal-modal doctor-confirm-modal" onClick={(event) => event.stopPropagation()}>
            <div className="doctor-confirm-modal__head">
              <div>
                <span>Bước 3/3</span>
                <h3>Xác nhận lịch khám</h3>
                <p>Kiểm tra lại thông tin trước khi hoàn tất.</p>
              </div>
              <button type="button" onClick={() => setConfirmOpen(false)} disabled={booking} aria-label="Đóng"><X width={17} height={17} /></button>
            </div>

            <div className="doctor-confirm-modal__doctor">
              <span>{doctorInitials(doctor?.full_name)}</span>
              <div><strong>{doctor?.full_name}</strong><small>{doctor?.degree} · {doctor?.specialty}</small></div>
            </div>

            <div className="doctor-confirm-modal__details">
              <span><CalendarIcon width={17} height={17} /><span><small>Ngày khám</small><strong>{formatGroupDate(selected.visit_date)}</strong></span></span>
              <span><Clock width={17} height={17} /><span><small>Khung giờ</small><strong>{selected.time_slot}</strong></span></span>
              <span><MapPin width={17} height={17} /><span><small>Địa điểm</small><strong>{selected.campus} · {doctor?.department} · {selected.room}</strong></span></span>
            </div>

            <div className="doctor-confirm-modal__patient">
              <div className="doctor-confirm-modal__section-title"><User width={14} height={14} /> Người đi khám</div>
              <div>
                <span><small>Họ và tên</small><strong>{profile?.full_name || 'Chưa cập nhật'}</strong></span>
                <span><small>Số điện thoại</small><strong>{profile?.phone || 'Chưa cập nhật'}</strong></span>
                <span><small>Email</small><strong>{user?.email || '—'}</strong></span>
              </div>
              {!profile?.phone && <p><Phone width={13} height={13} /> Bạn nên cập nhật số điện thoại trong Hồ sơ để bệnh viện dễ liên hệ.</p>}
            </div>

            <div className="doctor-confirm-modal__note">
              <Shield width={15} height={15} />
              <span>
                Khi xác nhận, lịch hẹn sẽ được thêm vào tab Lịch của bạn.
                <strong>Email xác nhận sẽ được gửi tới {user?.email || 'email tài khoản của bạn'}.</strong>
              </span>
            </div>
            {bookError && <p className="auth-error">{bookError}</p>}
            <div className="cal-modal__actions">
              <button type="button" className="btn btn--ghost" onClick={() => setConfirmOpen(false)} disabled={booking}>Quay lại</button>
              <button type="button" className="btn btn--primary" onClick={confirmBooking} disabled={booking}>
                {booking ? 'Đang xác nhận…' : <>Xác nhận đặt lịch <ArrowRight width={14} height={14} /></>}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
