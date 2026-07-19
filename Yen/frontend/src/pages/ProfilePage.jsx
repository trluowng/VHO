import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { Alert, Calendar as CalendarIcon, Clock, Cross, Heart, Phone, Pill, Pulse, Shield, User } from '../components/icons.jsx'
import TabNav from '../components/TabNav.jsx'
import EditableTagList from '../components/EditableTagList.jsx'
import ProfileSidebar from '../components/ProfileSidebar.jsx'
import ProfileInfoCard from '../components/ProfileInfoCard.jsx'
import VitalsMonitor from '../components/VitalsMonitor.jsx'
import { calendarApi } from '../lib/api.js'
import { toISODate } from '../lib/calendarGrid.js'

const GENDER_OPTIONS = [
  { value: 'nu', label: 'Nữ' },
  { value: 'nam', label: 'Nam' },
]

const PERSONAL_FIELDS = [
  { key: 'full_name', label: 'Họ và tên', placeholder: 'vd: Nguyễn Minh An' },
  {
    key: 'birth_date',
    label: 'Ngày sinh',
    type: 'date',
    format: (value) => value
      ? new Date(`${value}T00:00:00`).toLocaleDateString('vi-VN')
      : '—',
  },
  { key: 'gender', label: 'Giới tính', type: 'select', options: GENDER_OPTIONS, format: (v) => GENDER_OPTIONS.find((g) => g.value === v)?.label || '—' },
  { key: 'phone', label: 'Số điện thoại', type: 'tel', placeholder: 'vd: 0901 234 567' },
  { key: 'email', label: 'Email', readOnly: true },
  { key: 'address', label: 'Địa chỉ', placeholder: 'vd: 123 Đường Lê Lợi, Q.1, TP.HCM' },
  { key: 'occupation', label: 'Nghề nghiệp', placeholder: 'vd: Nhân viên văn phòng' },
  { key: 'blood_type', label: 'Nhóm máu', placeholder: 'vd: O+' },
  { key: 'insurance_status', label: 'Bảo hiểm y tế', placeholder: 'vd: Có hiệu lực' },
  { key: 'insurance_number', label: 'Mã số BHYT', placeholder: 'vd: HT1234567890' },
]

const EMERGENCY_FIELDS = [
  { key: 'emergency_contact_name', label: 'Họ và tên', placeholder: 'vd: Trần Thị Lan' },
  { key: 'emergency_contact_relationship', label: 'Mối quan hệ', placeholder: 'vd: Mẹ' },
  { key: 'emergency_contact_phone', label: 'Số điện thoại', type: 'tel', placeholder: 'vd: 0912 345 678' },
]

function formatReminderDate(iso) {
  if (!iso) return '—'
  return new Date(`${iso}T00:00:00`).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
}

function MedicationReminderList({ reminders, loading }) {
  return (
    <div className="profile-medication-reminders">
      <div className="profile-medication-reminders__head">
        <span><CalendarIcon width={14} height={14} /> Lịch nhắc uống thuốc</span>
        <Link to="/app/lich">Quản lý trong Lịch →</Link>
      </div>

      {loading && <p className="profile-medication-reminders__empty">Đang tải lịch nhắc thuốc…</p>}
      {!loading && reminders.length === 0 && (
        <p className="profile-medication-reminders__empty">Chưa có lịch nhắc uống thuốc đang hoạt động.</p>
      )}

      {!loading && reminders.length > 0 && (
        <div className="profile-medication-reminders__list">
          {reminders.map((entry) => {
            const isActive = entry.entry_date <= toISODate(new Date())
            return (
              <article key={entry.id} className="profile-medication-reminder">
                <span className="profile-medication-reminder__icon"><Pill width={16} height={16} /></span>
                <span className="profile-medication-reminder__body">
                  <span className="profile-medication-reminder__title-row">
                    <strong>{entry.title}</strong>
                    <em className={isActive ? 'is-active' : ''}>{isActive ? 'Đang dùng' : 'Sắp tới'}</em>
                  </span>
                  {entry.note && <small>{entry.note}</small>}
                  <span className="profile-medication-reminder__meta">
                    {entry.times?.length > 0 && (
                      <span><Clock width={11} height={11} /> {entry.times.join(' · ')}</span>
                    )}
                    <span>
                      {formatReminderDate(entry.entry_date)}
                      {' – '}
                      {formatReminderDate(entry.date_end || entry.entry_date)}
                    </span>
                  </span>
                </span>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function ProfilePage() {
  const { token, user, profile, updateProfile } = useAuth()
  const [medicationReminders, setMedicationReminders] = useState([])
  const [loadingReminders, setLoadingReminders] = useState(true)
  const profileValues = { ...(profile || {}), email: user?.email || '' }
  const activeMedicationReminders = useMemo(() => {
    const today = toISODate(new Date())
    return medicationReminders
      .filter((entry) => entry.type === 'thuoc' && (entry.date_end || entry.entry_date) >= today)
      .sort((a, b) => a.entry_date.localeCompare(b.entry_date))
  }, [medicationReminders])
  const medicationNames = new Set([
    ...(profile?.medications || []).map((name) => name.trim().toLocaleLowerCase('vi-VN')),
    ...activeMedicationReminders.map((entry) => entry.title.trim().toLocaleLowerCase('vi-VN')),
  ].filter(Boolean))
  const healthSummary = [
    {
      label: 'Bệnh nền',
      value: `${profile?.chronic_conditions?.length || 0} mục`,
      hint: profile?.chronic_conditions?.length ? 'Đã cập nhật' : 'Chưa ghi nhận',
      icon: Pulse,
      tone: 'blue',
    },
    {
      label: 'Dị ứng',
      value: `${profile?.allergies?.length || 0} mục`,
      hint: profile?.allergies?.length ? 'Cần lưu ý' : 'Chưa ghi nhận',
      icon: Alert,
      tone: profile?.allergies?.length ? 'red' : 'green',
    },
    {
      label: 'Thuốc đang dùng',
      value: `${medicationNames.size} loại`,
      hint: activeMedicationReminders.length
        ? `${activeMedicationReminders.length} lịch nhắc đang hoạt động`
        : (profile?.medications?.length ? 'Đã khai báo trong hồ sơ' : 'Chưa ghi nhận'),
      icon: Pill,
      tone: 'purple',
    },
    {
      label: 'Bảo hiểm y tế',
      value: profile?.insurance_status || 'Chưa cập nhật',
      hint: profile?.insurance_number ? `Mã: ${profile.insurance_number}` : 'Chưa có mã BHYT',
      icon: Shield,
      tone: 'green',
    },
  ]

  useEffect(() => {
    let cancelled = false
    async function loadMedicationReminders() {
      if (!token) {
        setMedicationReminders([])
        setLoadingReminders(false)
        return
      }
      setLoadingReminders(true)
      try {
        const data = await calendarApi.list(token)
        if (!cancelled) setMedicationReminders(data.entries || [])
      } catch {
        if (!cancelled) setMedicationReminders([])
      } finally {
        if (!cancelled) setLoadingReminders(false)
      }
    }
    loadMedicationReminders()
    return () => { cancelled = true }
  }, [token])

  async function save(updates) {
    // age phải là số nguyên nếu đổi giới tính đi kèm form khác cập nhật riêng —
    // ở đây chỉ các trường text/select nên gửi thẳng object con.
    await updateProfile(updates)
  }

  async function updateList(key, values) {
    await updateProfile({ [key]: values })
  }

  return (
    <>
      <div className="atmos">
        <div className="atmos__grain" />
        <div className="atmos__veil" />
      </div>

      <div className="shell shell--profile">
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
          <div className="profile-layout">
            <ProfileSidebar user={user} profile={profile || {}} />

            <div className="profile-main">
              <ProfileInfoCard
                icon={User}
                title="Thông tin cá nhân"
                fields={PERSONAL_FIELDS}
                values={profileValues}
                onSave={save}
                className="profile-card--personal"
              />

              <div className="profile-main__conditions">
                <EditableTagList
                  icon={Pulse}
                  label="Tiền sử bệnh"
                  values={profile?.chronic_conditions || []}
                  onChange={(v) => updateList('chronic_conditions', v)}
                  placeholder="vd: tăng huyết áp"
                  className="profile-tag-card profile-tag-card--history"
                  variant="list"
                />
                <EditableTagList
                  icon={Shield}
                  label="Dị ứng"
                  values={profile?.allergies || []}
                  onChange={(v) => updateList('allergies', v)}
                  placeholder="vd: penicillin"
                  tone="danger"
                  className="profile-tag-card profile-tag-card--allergies"
                />
              </div>

              <EditableTagList
                icon={Pill}
                label="Thuốc đang dùng"
                values={profile?.medications || []}
                onChange={(v) => updateList('medications', v)}
                placeholder="vd: Amlodipine 5mg"
                className="profile-tag-card profile-tag-card--medications"
                variant="list"
              >
                <MedicationReminderList reminders={activeMedicationReminders} loading={loadingReminders} />
              </EditableTagList>

              <section className="panel profile-health-summary">
                <div className="panel__head">
                  <p className="panel__label profile-card__title" style={{ margin: 0 }}>
                    <Heart width={17} height={17} /> Tổng quan hồ sơ sức khỏe
                  </p>
                </div>
                <div className="profile-health-summary__grid">
                  {healthSummary.map(({ label, value, hint, icon: Icon, tone }) => (
                    <article key={label} className={`profile-health-stat profile-health-stat--${tone}`}>
                      <span className="profile-health-stat__icon"><Icon width={17} height={17} /></span>
                      <span className="profile-health-stat__body">
                        <small>{label}</small>
                        <strong>{value}</strong>
                        <em>{hint}</em>
                      </span>
                    </article>
                  ))}
                </div>
              </section>

              <div className="profile-main__vitals">
                <VitalsMonitor profile={profile} />
              </div>

              <div id="emergency-contact" className="profile-main__emergency">
                <ProfileInfoCard
                  icon={Phone}
                  title="Người liên hệ khẩn cấp"
                  fields={EMERGENCY_FIELDS}
                  values={profile || {}}
                  onSave={save}
                  className="profile-card--emergency"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
