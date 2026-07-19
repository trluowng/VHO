import { useState } from 'react'
import { Link } from 'react-router-dom'
import { doctorsApi } from '../lib/api.js'
import { ArrowRight, Calendar as CalendarIcon, Check, Clock, MapPin, Stethoscope } from './icons.jsx'

function formatDate(iso) {
  const date = new Date(`${iso}T00:00:00`)
  return date.toLocaleDateString('vi-VN', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

function doctorLabel(option) {
  return option.doctor_name || option.doctor?.full_name || 'Bác sĩ'
}

export default function ChatBookingOptions({ options = [], token, confirmed, onBooked }) {
  const [bookingKey, setBookingKey] = useState(null)
  const [booked, setBooked] = useState(confirmed || null)
  const [error, setError] = useState(null)

  async function book(option) {
    const key = `${option.doctor_id}-${option.visit_date}-${option.time_slot}`
    setBookingKey(key)
    setError(null)
    try {
      const result = await doctorsApi.book(token, option.doctor_id, {
        visit_date: option.visit_date,
        time_slot: option.time_slot,
      })
      const nextBooked = { ...result, ...option, emailNotification: result.email_notification }
      setBooked(nextBooked)
      onBooked?.(nextBooked)
    } catch (err) {
      setError(err.message)
    } finally {
      setBookingKey(null)
    }
  }

  if (booked) {
    const doctorName = booked.doctor?.full_name || doctorLabel(booked)
    return (
      <div className="chat-booking-card chat-booking-card--success">
        <span className="chat-booking-card__success-icon"><Check width={20} height={20} /></span>
        <div className="chat-booking-card__success-copy">
          <strong>Đã chốt lịch khám</strong>
          <p>{formatDate(booked.visit_date)} · {booked.time_slot} với {doctorName}</p>
          {booked.emailNotification === 'sent' && <small>Email xác nhận đã được gửi tới email tài khoản của bạn.</small>}
          {(booked.emailNotification === 'failed' || booked.emailNotification === 'disabled') && (
            <small className="is-error">Chưa gửi được email xác nhận, nhưng lịch khám đã được lưu.</small>
          )}
        </div>
        <Link to="/app/lich" state={{ focusDate: booked.visit_date }}>
          Xem lịch <ArrowRight width={13} height={13} />
        </Link>
      </div>
    )
  }

  if (!options.length) return null

  return (
    <div className="chat-booking-card">
      <div className="chat-booking-card__head">
        <span><Stethoscope width={16} height={16} /></span>
        <div>
          <strong>Chọn lịch khám ngay trong chat</strong>
          <p>Chốt một khung giờ, lịch sẽ tự cập nhật sang tab Lịch và tab Đặt lịch khám.</p>
        </div>
      </div>

      <div className="chat-booking-card__list">
        {options.map((option, index) => {
          const key = `${option.doctor_id}-${option.visit_date}-${option.time_slot}-${index}`
          const isBooking = bookingKey === `${option.doctor_id}-${option.visit_date}-${option.time_slot}`
          return (
            <div className="chat-booking-option" key={key}>
              <div className="chat-booking-option__main">
                <strong>{doctorLabel(option)}</strong>
                <small><Stethoscope width={12} height={12} /> {option.specialty || 'Khám bệnh'}</small>
                <small><CalendarIcon width={12} height={12} /> {formatDate(option.visit_date)}</small>
                <small><Clock width={12} height={12} /> {option.time_slot}</small>
                {(option.campus || option.location) && (
                  <small><MapPin width={12} height={12} /> {[option.campus, option.location].filter(Boolean).join(' · ')}</small>
                )}
              </div>
              <button type="button" className="btn btn--primary" onClick={() => book(option)} disabled={Boolean(bookingKey)}>
                {isBooking ? 'Đang chốt…' : 'Chốt lịch này'}
              </button>
            </div>
          )
        })}
      </div>

      {error && <p className="auth-error">{error}</p>}
    </div>
  )
}
