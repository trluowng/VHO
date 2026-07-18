import { useCallback, useEffect, useRef, useState } from 'react'
import { audioRecordingSupport, WavRecorder } from '../lib/audioRecorder.js'
import { LiveSpeechRecognizer, liveSpeechRecognitionSupport } from '../lib/liveSpeechRecognition.js'
import { Microphone, Send } from './icons.jsx'

const MAX_RECORDING_MS = 30_000

function speechErrorMessage(error) {
  if (error?.name === 'NotAllowedError' || error?.name === 'SecurityError' || error?.code === 'not-allowed' || error?.code === 'service-not-allowed') {
    return 'Bạn cần cho phép trình duyệt sử dụng micro để nhập bằng giọng nói.'
  }
  if (error?.name === 'NotFoundError' || error?.code === 'audio-capture') return 'Không tìm thấy micro trên thiết bị.'
  if (error?.name === 'NotReadableError') return 'Micro đang được ứng dụng khác sử dụng.'
  if (error?.code === 'no-speech') return 'Chưa nghe rõ lời nói — bạn có thể tiếp tục nói rồi bấm dừng.'
  if (error?.code === 'network') return 'Nhận dạng trực tiếp bị gián đoạn; bản ghi vẫn sẽ được xử lý khi bạn bấm dừng.'
  if (error?.code === 'recording_too_short') return 'Bản ghi quá ngắn — hãy nói ít nhất một câu rồi thử lại.'
  return error?.message || 'Không thể nhận dạng giọng nói. Vui lòng thử lại.'
}

function withSpeech(base, transcript) {
  const prefix = (base || '').trim()
  const spoken = (transcript || '').trim()
  if (!prefix) return spoken
  if (!spoken) return prefix
  return `${prefix} ${spoken}`
}

export default function Composer({ onSend, onTranscribe, disabled, locked }) {
  const [value, setValue] = useState('')
  const [starting, setStarting] = useState(false)
  const [recording, setRecording] = useState(false)
  const [liveListening, setLiveListening] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [speechError, setSpeechError] = useState(null)
  const ref = useRef(null)
  const recorderRef = useRef(null)
  const liveRecognizerRef = useRef(null)
  const speechBaseRef = useRef('')
  const timerRef = useRef(null)
  const audioSupport = audioRecordingSupport()
  const liveSupport = liveSpeechRecognitionSupport()
  const voiceSupported = typeof onTranscribe === 'function' && audioSupport.supported
  const voiceUnavailable = audioSupport.reason === 'insecure_context'
    ? 'Micro bị chặn trên địa chỉ HTTP dạng IP — hãy mở bằng localhost hoặc HTTPS.'
    : 'Trình duyệt này chưa hỗ trợ thu âm từ micro.'

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 130) + 'px'
  }, [value])

  const clearTimer = useCallback(() => {
    if (timerRef.current) window.clearTimeout(timerRef.current)
    timerRef.current = null
  }, [])

  const finishRecording = useCallback(async (recorder = recorderRef.current) => {
    if (!recorder || recorderRef.current !== recorder) return
    recorderRef.current = null
    const liveRecognizer = liveRecognizerRef.current
    liveRecognizerRef.current = null
    liveRecognizer?.stop()
    clearTimer()
    setRecording(false)
    setLiveListening(false)
    setTranscribing(true)
    setSpeechError(null)

    try {
      const audio = await recorder.stop()
      const data = await onTranscribe(audio)
      const transcript = (data?.text || '').trim()
      if (!transcript) throw new Error('Dịch vụ chưa trả về nội dung nhận dạng.')
      setValue(withSpeech(speechBaseRef.current, transcript))
      window.requestAnimationFrame(() => ref.current?.focus())
    } catch (error) {
      setSpeechError(speechErrorMessage(error))
    } finally {
      setTranscribing(false)
    }
  }, [clearTimer, onTranscribe])

  const startRecording = useCallback(async () => {
    if (!voiceSupported || disabled || locked || starting || transcribing || recorderRef.current) return
    setSpeechError(null)
    setStarting(true)
    speechBaseRef.current = value.trim()
    const recorder = new WavRecorder()
    recorderRef.current = recorder

    try {
      await recorder.start()
      if (recorderRef.current !== recorder) {
        await recorder.cancel()
        return
      }
      setStarting(false)
      setRecording(true)

      if (liveSupport.supported) {
        let liveRecognizer
        liveRecognizer = new LiveSpeechRecognizer({
          language: 'vi-VN',
          onTranscript: (transcript) => {
            if (liveRecognizerRef.current !== liveRecognizer || recorderRef.current !== recorder) return
            setValue(withSpeech(speechBaseRef.current, transcript))
          },
          onError: (error) => {
            if (liveRecognizerRef.current === liveRecognizer) setSpeechError(speechErrorMessage(error))
          },
          onEnd: () => {
            if (liveRecognizerRef.current !== liveRecognizer) return
            liveRecognizerRef.current = null
            setLiveListening(false)
          },
        })
        liveRecognizerRef.current = liveRecognizer
        try {
          liveRecognizer.start()
          setLiveListening(true)
        } catch (error) {
          liveRecognizerRef.current = null
          setLiveListening(false)
          setSpeechError(speechErrorMessage(error))
        }
      }

      timerRef.current = window.setTimeout(() => {
        void finishRecording(recorder)
      }, MAX_RECORDING_MS)
    } catch (error) {
      if (recorderRef.current === recorder) recorderRef.current = null
      await recorder.cancel()
      setStarting(false)
      setSpeechError(speechErrorMessage(error))
    }
  }, [disabled, finishRecording, liveSupport.supported, locked, starting, transcribing, value, voiceSupported])

  const toggleRecording = () => {
    if (recording) void finishRecording()
    else void startRecording()
  }

  useEffect(() => () => {
    clearTimer()
    liveRecognizerRef.current?.abort()
    liveRecognizerRef.current = null
    void recorderRef.current?.cancel()
    recorderRef.current = null
  }, [clearTimer])

  useEffect(() => {
    if (!(locked || disabled) || !recorderRef.current) return
    const recorder = recorderRef.current
    recorderRef.current = null
    liveRecognizerRef.current?.abort()
    liveRecognizerRef.current = null
    clearTimer()
    setStarting(false)
    setRecording(false)
    setLiveListening(false)
    void recorder.cancel()
  }, [clearTimer, disabled, locked])

  const submit = () => {
    const v = value.trim()
    if (!v || disabled || starting || recording || transcribing) return
    onSend(v)
    setValue('')
    setSpeechError(null)
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className={`composer ${locked ? 'is-locked' : ''}`}>
      <div className={`composer__inner ${recording ? 'is-recording' : ''}`}>
        <textarea
          ref={ref}
          rows={1}
          value={value}
          placeholder={recording ? 'Đang nghe bạn nói…' : 'Mô tả triệu chứng của bạn bằng lời…'}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKey}
          disabled={locked}
          readOnly={recording}
        />
        <button
          type="button"
          className={`mic-btn ${recording ? 'is-recording' : ''}`}
          onClick={toggleRecording}
          disabled={!voiceSupported || disabled || locked || starting || transcribing}
          aria-label={recording ? 'Dừng ghi âm' : 'Nhập bằng giọng nói'}
          aria-pressed={recording}
          title={voiceSupported ? (recording ? 'Dừng và chuyển thành văn bản' : 'Nhập bằng giọng nói') : voiceUnavailable}
        >
          <Microphone />
        </button>
        <button className="send-btn" onClick={submit} disabled={!value.trim() || disabled || starting || recording || transcribing} aria-label="Gửi">
          <Send />
        </button>
      </div>
      <div className={`composer__hint ${speechError ? 'is-error' : ''}`} aria-live="polite">
        {starting
          ? 'Đang mở micro…'
          : recording
          ? (liveListening ? 'Đang nghe trực tiếp… chữ sẽ xuất hiện khi bạn nói' : 'Đang ghi âm tiếng Việt… bấm micro lần nữa để dừng')
          : transcribing
            ? 'Đang chuyển giọng nói thành văn bản…'
            : speechError || (!voiceSupported ? voiceUnavailable : 'Yên là prototype hỗ trợ — không thay thế chẩn đoán y khoa · Bấm micro để nói')}
      </div>
    </div>
  )
}
