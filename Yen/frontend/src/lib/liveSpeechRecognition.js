/* Browser-native interim speech recognition.

   This is used only for the live preview while the user is speaking. The WAV
   recording still goes to backend/stt when recording stops, so the backend
   remains the source of the final transcript. */

function speechRecognitionConstructor() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

export function liveSpeechRecognitionSupport() {
  if (typeof window === 'undefined') return { supported: false, reason: 'unsupported' }
  if (!window.isSecureContext) return { supported: false, reason: 'insecure_context' }
  return speechRecognitionConstructor()
    ? { supported: true, reason: null }
    : { supported: false, reason: 'unsupported' }
}

function recognitionError(code) {
  const error = new Error(code || 'speech_recognition_error')
  error.code = code || 'speech_recognition_error'
  return error
}

export class LiveSpeechRecognizer {
  constructor({ language = 'vi-VN', onStart, onTranscript, onError, onEnd } = {}) {
    this.language = language
    this.onStart = onStart
    this.onTranscript = onTranscript
    this.onError = onError
    this.onEnd = onEnd
    this.recognition = null
  }

  start() {
    const Recognition = speechRecognitionConstructor()
    if (!Recognition || !window.isSecureContext) {
      throw recognitionError('unsupported')
    }

    const recognition = new Recognition()
    recognition.lang = this.language
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    recognition.onstart = () => this.onStart?.()
    recognition.onresult = (event) => {
      const finalParts = []
      const interimParts = []

      for (let i = 0; i < event.results.length; i += 1) {
        const text = event.results[i]?.[0]?.transcript?.trim()
        if (!text) continue
        if (event.results[i].isFinal) finalParts.push(text)
        else interimParts.push(text)
      }

      const finalText = finalParts.join(' ').replace(/\s+/g, ' ').trim()
      const interimText = interimParts.join(' ').replace(/\s+/g, ' ').trim()
      const text = [finalText, interimText].filter(Boolean).join(' ').trim()
      if (text) this.onTranscript?.(text, { finalText, interimText })
    }
    recognition.onerror = (event) => {
      if (event.error !== 'aborted') this.onError?.(recognitionError(event.error))
    }
    recognition.onend = () => {
      this.recognition = null
      this.onEnd?.()
    }

    this.recognition = recognition
    try {
      recognition.start()
    } catch (error) {
      this.recognition = null
      throw error
    }
  }

  stop() {
    try {
      this.recognition?.stop()
    } catch {
      // Recognition may already have ended after a period of silence.
    }
  }

  abort() {
    const recognition = this.recognition
    this.recognition = null
    if (!recognition) return

    recognition.onstart = null
    recognition.onresult = null
    recognition.onerror = null
    recognition.onend = null
    try {
      recognition.abort()
    } catch {
      // Nothing remains to clean up.
    }
  }
}
