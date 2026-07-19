import { useEffect, useRef, useState, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { createSession, handleUser, setSymptoms, callRealModel, detectRedFlag } from '../lib/triageEngine.js'
import { loadSessions, upsertSession } from '../lib/sessionLog.js'
import { isApiConfigured, sttApi } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { Cross } from '../components/icons.jsx'
import TabNav from '../components/TabNav.jsx'
import SessionHistory from '../components/SessionHistory.jsx'
import Message from '../components/Message.jsx'
import Typing from '../components/Typing.jsx'
import QuickReplies from '../components/QuickReplies.jsx'
import Composer from '../components/Composer.jsx'
import WelcomeHero from '../components/WelcomeHero.jsx'
import ProfileRail from '../components/ProfileRail.jsx'
import TriageResult from '../components/TriageResult.jsx'
import ChatBookingOptions from '../components/ChatBookingOptions.jsx'
import Emergency from '../components/Emergency.jsx'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const USE_REAL = isApiConfigured() // bật khi đã trỏ tới backend Gemini
const clock = () => new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })

function deriveTitle(items, session) {
  const sy = session?.symptoms || []
  if (sy.length) return sy.slice(0, 2).map((s) => s.label).join(' & ')
  const firstUser = items.find((i) => i.role === 'user')
  if (firstUser) return firstUser.text.length > 34 ? firstUser.text.slice(0, 34) + '…' : firstUser.text
  return 'Phiên mới'
}
function snapshotProfile(s) {
  return {
    symptoms: s.symptoms || [],
    confidence: s.confidence || 0,
    confTier: s.confTier || 'none',
    missing: s.missing || [],
    facts: s.facts || {},
    stage: s.stage,
  }
}
function lastLevel(items) {
  const r = [...items].reverse().find((i) => i.type === 'result')
  return r?.triage?.level || null
}

export default function ChatPage() {
  const { token } = useAuth()
  const [session, setSession] = useState(createSession)
  const [items, setItems] = useState([])
  const [quick, setQuick] = useState(null)
  const [typing, setTyping] = useState(false)
  const [busy, setBusy] = useState(false)
  const [emergency, setEmergency] = useState(null)

  const [sessions, setSessions] = useState(loadSessions)
  const [sid, setSid] = useState(null)
  const [reviewing, setReviewing] = useState(null)
  const [speakingMessageId, setSpeakingMessageId] = useState(null)

  const idRef = useRef(0)
  const sidRef = useRef(null)
  const startedAtRef = useRef(null)
  const preEmergency = useRef(null)
  const scrollRef = useRef(null)
  const itemsRef = useRef([])
  const currentUtteranceRef = useRef(null)
  const started = items.some((i) => i.role === 'user')

  // Đọc từng câu trả lời AI khi người dùng bấm nút loa dưới message.
  const speakAiMessage = useCallback((messageId, text) => {
    if (!text) return
    const synth = window.speechSynthesis
    if (!synth) return
    synth.cancel()
    setSpeakingMessageId(messageId)

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'vi-VN'
    utterance.rate = 0.95
    utterance.pitch = 1
    utterance.voice = synth
      .getVoices()
      .find((voice) => voice.lang?.toLowerCase().startsWith('vi')) || null
    utterance.onend = () => setSpeakingMessageId(null)
    utterance.onerror = () => setSpeakingMessageId(null)
    currentUtteranceRef.current = utterance
    synth.speak(utterance)
  }, [])

  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel()
      setSpeakingMessageId(null)
      currentUtteranceRef.current = null
    }
  }, [])

  useEffect(() => {
    itemsRef.current = items
  }, [items])

  const push = useCallback((item) => {
    setItems((prev) => [...prev, { id: ++idRef.current, at: Date.now(), stamp: clock(), ...item }])
  }, [])

  // autoscroll
  useEffect(() => {
    const el = scrollRef.current
    if (el && !reviewing) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [items, typing, quick, reviewing])

  // Tự lưu phiên hiện tại vào nhật ký (localStorage) sau mỗi lượt
  useEffect(() => {
    if (reviewing || !sidRef.current) return
    if (!items.some((i) => i.role === 'user')) return
    setSessions(
      upsertSession({
        id: sidRef.current,
        title: deriveTitle(items, session),
        startedAt: startedAtRef.current,
        updatedAt: Date.now(),
        source: USE_REAL ? 'gemini' : 'rule',
        items,
        profile: snapshotProfile(session),
        level: lastLevel(items),
      }),
    )
  }, [items, session, reviewing])

  // meta gắn vào AI message đầu tiên của mỗi lượt: { ms, source }
  const playEvents = useCallback(
    async (events, meta) => {
      setBusy(true)
      let firstAi = true
      for (const ev of events) {
        setTyping(true)
        const dwell = ev.type === 'emergency' ? 380 : 620 + Math.min((ev.text || '').length, 80) * 6
        await sleep(dwell)
        setTyping(false)
        if (ev.type === 'emergency') {
          setEmergency({ flag: ev.flag })
          break
        }
        const m = firstAi ? meta : null
        if (ev.type === 'message' || ev.type === 'question') {
          push({ type: 'message', role: 'ai', text: ev.text, confirm: ev.confirm, meta: m })
          if (ev.type === 'question') setQuick(ev.quick || null)
          firstAi = false
        } else if (ev.type === 'result') {
          push({ type: 'result', triage: ev.triage, meta: m })
          firstAi = false
        } else if (ev.type === 'booking_options') {
          push({ type: 'booking_options', options: ev.options || [], meta: m })
          firstAi = false
        } else if (ev.type === 'booking_confirmation') {
          push({ type: 'booking_confirmation', booking: ev.booking, meta: m })
          firstAi = false
        }
        await sleep(170)
      }
      setBusy(false)
    },
    [push],
  )

  // Gọi backend Gemini thật; lỗi/không cấu hình → fallback rule-based engine.
  const runReal = useCallback(
    async (text) => {
      // Sàng lọc red-flag tại chỗ trước (<1s) — tình huống khẩn cấp không được
      // chờ round-trip Gemini (vài giây), phải hiện cảnh báo ngay lập tức.
      const flag = detectRedFlag(text)
      if (flag) {
        setSession((s) => ({ ...s, redFlag: flag, stage: 'emergency' }))
        await playEvents([{ type: 'emergency', flag }], { source: 'rule-fastpath' })
        return
      }

      setBusy(true)
      setTyping(true)
      const t0 = performance.now()
      try {
        const history = itemsRef.current
          .filter((i) => i.type === 'message')
          .map((i) => ({ role: i.role, text: i.text }))
        const data = await callRealModel(history, text, token, sidRef.current)
        const ms = data?._meta?.latencyMs ?? Math.round(performance.now() - t0)
        setTyping(false)
        if (data.profile) setSession((s) => ({ ...createSession(), ...data.profile, result: s.result }))
        await playEvents(data.events || [], { ms, source: 'gemini' })
      } catch (err) {
        setTyping(false)
        console.warn('[Yên] Backend lỗi, dùng rule-based engine:', err?.message || err)
        const { session: ns, events } = handleUser(session, text)
        setSession(ns)
        await playEvents(events, { source: 'rule' })
      } finally {
        setBusy(false)
      }
    },
    [session, playEvents, token],
  )

  const send = useCallback(
    (text) => {
      if (busy) return
      if (!sidRef.current) {
        sidRef.current = 's_' + Date.now()
        startedAtRef.current = Date.now()
        setSid(sidRef.current)
      }
      push({ type: 'message', role: 'user', text })
      setQuick(null)
      preEmergency.current = session
      if (USE_REAL) {
        runReal(text)
        return
      }
      const { session: ns, events } = handleUser(session, text)
      setSession(ns)
      playEvents(events, { source: 'rule' })
    },
    [busy, session, push, playEvents, runReal],
  )

  const transcribeSpeech = useCallback(
    (audioBlob) => sttApi.transcribe(token, audioBlob),
    [token],
  )

  const handleBookedFromChat = useCallback(
    (booking) => {
      const doctorName = booking.doctor?.full_name || booking.doctor_name || 'bác sĩ'
      const emailNote =
        booking.emailNotification === 'sent'
          ? 'Email xác nhận cũng đã được gửi tới email tài khoản của bạn.'
          : 'Nếu email chưa gửi được, lịch khám vẫn đã được lưu trong hệ thống.'
      const text = `Đã chốt lịch với ${doctorName} vào ${booking.visit_date} lúc ${booking.time_slot}. Lịch này đã xuất hiện trong tab Lịch và slot đã được loại khỏi tab Đặt lịch khám. ${emailNote}`
      push({ type: 'message', role: 'ai', text, confirm: true })
    },
    [push],
  )

  const reset = useCallback(() => {
    sidRef.current = null
    startedAtRef.current = null
    setSid(null)
    setReviewing(null)
    setItems([])
    setSession(createSession())
    setQuick(null)
    setTyping(false)
    setBusy(false)
    setEmergency(null)
  }, [])

  const openSession = useCallback((rec) => {
    setReviewing(rec)
    setQuick(null)
    setEmergency(null)
  }, [])
  const exitReview = useCallback(() => setReviewing(null), [])

  const onBack = useCallback(() => {
    setEmergency(null)
    if (preEmergency.current) setSession(preEmergency.current)
  }, [])

  const editSymptoms = useCallback(
    (next) => {
      // Optimistic: hiện ngay chip vừa sửa lên UI (cả 2 chế độ)
      setSession((s) => ({ ...s, symptoms: next }))
      if (USE_REAL) {
        if (busy) return

        const removed = session.symptoms.filter(
          (oldSymptom) =>
            !next.some(
              (newSymptom) => newSymptom.label === oldSymptom.label
            )
        )

        const removedLabels = removed
          .map((s) => s.label)
          .join(', ')

        if (removedLabels) {
          send(`Xin lỗi, tôi không bị ${removedLabels}.`)
        }

        return
      }
      const { session: ns, events } = setSymptoms(session, next)
      setSession(ns)
      if (events.length && !busy) playEvents(events, { source: 'rule' })
    },
    [session, busy, playEvents, send],
  )

  const activeTitle =
    session.symptoms && session.symptoms.length
      ? session.symptoms.slice(0, 2).map((s) => s.label).join(' & ')
      : null

  const onCta = useCallback(
    (cta) => {
      if (/bắt đầu lại/i.test(cta.label)) return reset()
      if (/lưu/i.test(cta.label)) {
        push({ type: 'message', role: 'ai', text: '✓ Đã lưu bản tóm tắt phiên này. Bạn có thể mang theo khi đi khám — gồm triệu chứng, thời gian, câu trả lời và lý do mình đưa ra khuyến nghị.' })
        return
      }
      if (/mô tả thêm/i.test(cta.label)) {
        push({ type: 'message', role: 'ai', text: 'Được — bạn cứ kể thêm bất kỳ chi tiết nào: thời gian, mức độ, hay bệnh nền / thuốc đang dùng. Mình sẽ cập nhật lại đánh giá.' })
        return
      }
      if (/đặt lịch/i.test(cta.label)) {
        // Nhãn CTA thường là "Đặt lịch khám <chuyên khoa>" -- gửi lại thành 1 câu
        // yêu cầu rõ ràng thay vì gửi nguyên nhãn nút, để backend hiểu đây là yêu
        // cầu xem bác sĩ/lịch trống (gọi xem_lich_kham) chứ không phải mô tả
        // triệu chứng mới cần đánh giá lại từ đầu.
        const specialty = cta.label.replace(/đặt lịch khám\s*/i, '').trim()
        send(specialty ? `Tôi muốn đặt lịch khám ${specialty}.` : 'Tôi muốn đặt lịch khám.')
        return
      }
      if (/bác sĩ/i.test(cta.label)) {
        push({ type: 'message', role: 'ai', text: 'Mình đã chuẩn bị sẵn bản tóm tắt để bạn chia sẻ với bác sĩ hoặc nhân viên y tế. Trong lúc đó, hãy theo dõi nếu triệu chứng nặng lên.' })
      }
    },
    [reset, push, send],
  )

  const viewItems = reviewing ? reviewing.items : items
  const railSession = reviewing ? { ...createSession(), ...reviewing.profile } : session

  return (
    <>
      <div className="atmos">
        <div className="atmos__grain" />
        <div className="atmos__veil" />
      </div>

      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand__mark"><Cross /></div>
            <div>
              <div className="brand__name">Yên<em> · sức khỏe</em></div>
              <div className="brand__sub">Symptom Triage Assistant</div>
            </div>
          </div>
          <TabNav />
        </header>

        <div className="workspace">
          <SessionHistory
            sessions={sessions}
            activeId={reviewing ? reviewing.id : sid}
            isReviewing={!!reviewing}
            activeTitle={activeTitle}
            onNew={reset}
            onOpen={openSession}
          />

          <ProfileRail session={railSession} onEditSymptoms={reviewing ? undefined : editSymptoms} />

          <main className="chat">
            <AnimatePresence>
              {reviewing && (
                <motion.div
                  className="review-banner"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  <span>👁 Đang xem lại phiên cũ — chỉ đọc</span>
                  <button onClick={exitReview}>Về phiên hiện tại</button>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="chat__scroll" ref={scrollRef}>
              <div className="thread">
                {!started && !reviewing && <WelcomeHero onPick={send} />}

                <AnimatePresence initial={false}>
                  {viewItems.map((it) =>
                    it.type === 'result' ? (
                      <motion.div key={it.id} layout>
                        <TriageResult triage={it.triage} onCta={onCta} />
                      </motion.div>
                    ) : it.type === 'booking_options' ? (
                      <motion.div key={it.id} layout>
                        <ChatBookingOptions options={it.options} token={token} onBooked={handleBookedFromChat} />
                      </motion.div>
                    ) : it.type === 'booking_confirmation' ? (
                      <motion.div key={it.id} layout>
                        <ChatBookingOptions confirmed={it.booking} token={token} />
                      </motion.div>
                    ) : (
                      <Message
                        key={it.id}
                        role={it.role}
                        text={it.text}
                        confirm={it.confirm}
                        stamp={it.stamp}
                        meta={it.meta}
                        speaking={speakingMessageId === it.id}
                        onSpeak={it.role === 'ai' && !reviewing ? (text) => speakAiMessage(it.id, text) : undefined}
                      />
                    ),
                  )}
                </AnimatePresence>

                <AnimatePresence>{typing && !reviewing && <Typing key="typing" />}</AnimatePresence>

                <AnimatePresence>
                  {quick && !typing && !busy && !reviewing && (
                    <QuickReplies options={quick} onPick={send} />
                  )}
                </AnimatePresence>
              </div>
            </div>

            <Composer
              onSend={send}
              onTranscribe={transcribeSpeech}
              disabled={busy}
              locked={!!emergency || !!reviewing}
            />

            <AnimatePresence>
              {emergency && <Emergency flag={emergency.flag} onBack={onBack} />}
            </AnimatePresence>
          </main>
        </div>
      </div>
    </>
  )
}
