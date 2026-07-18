import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Cross, Edit } from './icons.jsx'

export default function EditableTagList({
  label,
  values,
  onChange,
  placeholder,
  busy,
  tone,
  icon: Icon,
  className = '',
  variant = 'chips',
  children,
}) {
  const [editing, setEditing] = useState(false)
  const [adding, setAdding] = useState(false)
  const [draft, setDraft] = useState('')

  function addValue() {
    const v = draft.trim()
    if (v && !values.includes(v)) onChange([...values, v])
    setDraft('')
    setAdding(false)
  }

  function removeValue(v) {
    onChange(values.filter((x) => x !== v))
  }

  return (
    <section className={`panel editable-tag-list editable-tag-list--${variant} ${className}`.trim()}>
      <div className="panel__head">
        <p className="panel__label profile-card__title" style={{ margin: 0 }}>
          {Icon && <Icon width={17} height={17} />} {label}
        </p>
        <button type="button" className="edit-toggle" onClick={() => { setEditing((v) => !v); setAdding(false) }}>
          {!editing && <Edit width={13} height={13} />}
          {editing ? 'Xong' : 'Sửa'}
        </button>
      </div>

      {values.length === 0 && !editing ? (
        !children && <p className="empty-hint">Chưa có thông tin. Bấm "Sửa" để thêm.</p>
      ) : (
        <div className="chips">
          <AnimatePresence>
            {values.map((v) => (
              <motion.span
                key={v}
                className={`chip ${tone === 'danger' ? 'chip--danger' : ''} ${editing ? 'is-editing' : ''}`}
                layout
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.6 }}
                transition={{ type: 'spring', stiffness: 420, damping: 26 }}
              >
                <span className="chip__dot" />
                {v}
                {editing && (
                  <button className="chip__x" onClick={() => removeValue(v)} disabled={busy} aria-label={`Xoá ${v}`}>
                    <Cross width={12} height={12} style={{ transform: 'rotate(45deg)' }} />
                  </button>
                )}
              </motion.span>
            ))}
          </AnimatePresence>

          {editing && (adding ? (
            <span className="chip chip--input">
              <input
                autoFocus
                value={draft}
                placeholder={placeholder}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') addValue(); if (e.key === 'Escape') { setAdding(false); setDraft('') } }}
                onBlur={() => { if (draft.trim()) addValue(); else setAdding(false) }}
              />
            </span>
          ) : (
            <button className="chip chip--add" onClick={() => setAdding(true)}>＋ Thêm</button>
          ))}
        </div>
      )}

      {children}
    </section>
  )
}
