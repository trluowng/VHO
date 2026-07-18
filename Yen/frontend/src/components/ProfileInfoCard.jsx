import { useState } from 'react'
import { Edit } from './icons.jsx'

/* Thẻ thông tin dạng xem/sửa dùng chung — "Thông tin cá nhân" và "Người liên hệ
   khẩn cấp" đều cùng một khuôn: xem dạng danh sách, bấm "Sửa" để hiện form,
   "Lưu" để gọi onSave rồi quay lại chế độ xem. */
export default function ProfileInfoCard({ icon: Icon, title, fields, values, onSave, busy, className = '' }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(() => Object.fromEntries(fields.map((f) => [f.key, values[f.key] || ''])))
  const [saving, setSaving] = useState(false)

  function startEdit() {
    setDraft(Object.fromEntries(fields.map((f) => [f.key, values[f.key] || ''])))
    setEditing(true)
  }

  async function save() {
    setSaving(true)
    try {
      const writableValues = Object.fromEntries(
        fields.filter((field) => !field.readOnly).map((field) => [field.key, draft[field.key]]),
      )
      await onSave(writableValues)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className={`panel profile-card ${className}`.trim()}>
      <div className="panel__head">
        <p className="panel__label profile-card__title" style={{ margin: 0 }}>
          {Icon && <Icon width={15} height={15} />} {title}
        </p>
        <button
          type="button"
          className="edit-toggle"
          onClick={editing ? save : startEdit}
          disabled={busy || saving}
        >
          {!editing && <Edit width={13} height={13} />}
          {editing ? (saving ? 'Đang lưu…' : 'Lưu') : 'Sửa'}
        </button>
      </div>

      {editing ? (
        <div className="profile-card__form">
          {fields.map((f) => (
            <label key={f.key} className="auth-field">
              <span>{f.label}</span>
              {f.readOnly ? (
                <input value={draft[f.key]} readOnly disabled />
              ) : f.type === 'select' ? (
                <select value={draft[f.key]} onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}>
                  <option value="">—</option>
                  {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              ) : (
                <input
                  type={f.type || 'text'}
                  value={draft[f.key]}
                  placeholder={f.placeholder}
                  onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
                />
              )}
            </label>
          ))}
        </div>
      ) : (
        <dl className="profile-facts">
          {fields.map((f) => (
            <div key={f.key}>
              <dt>{f.label}</dt>
              <dd>{f.format ? f.format(values[f.key]) : (values[f.key] || '—')}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  )
}
