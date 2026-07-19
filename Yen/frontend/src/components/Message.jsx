import { motion } from 'framer-motion'
import { Pulse, Volume } from './icons.jsx'

const time = () =>
  new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })

export default function Message({ role, text, confirm, stamp, meta, onSpeak, speaking }) {
  const ai = role === 'ai'
  const ms = meta?.ms
  return (
    <motion.div
      className={`msg ${ai ? 'ai' : 'user'}`}
      initial={{ opacity: 0, y: 14, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="msg__avatar">{ai ? <Pulse /> : 'Bạn'}</div>
      <div className="msg__body">
        <div className="bubble">
          {confirm && <span style={{ color: 'var(--sage)', fontWeight: 600 }}>✓ Đã ghi nhận — </span>}
          {text}
        </div>
        <span className="msg__time">
          {stamp || time()}
          {ai && meta?.source && (
            <span className={`run-tag ${meta.source}`}>
              {meta.source === 'gemini' ? 'Gemini' : 'demo'}
              {typeof ms === 'number' && <> · ⏱ {(ms / 1000).toFixed(ms < 1000 ? 2 : 1)}s</>}
            </span>
          )}
        </span>
        {ai && onSpeak && text && (
          <button
            type="button"
            className={`msg-speak-btn ${speaking ? 'is-speaking' : ''}`}
            onClick={() => onSpeak(text)}
            disabled={speaking}
            aria-label="Đọc câu trả lời này"
            title="Đọc câu trả lời này"
          >
            <Volume width={13} height={13} />
            <span>{speaking ? 'Đang đọc…' : 'Nghe câu này'}</span>
          </button>
        )}
      </div>
    </motion.div>
  )
}
