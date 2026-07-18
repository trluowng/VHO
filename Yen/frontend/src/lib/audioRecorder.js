/* Record browser microphone input as PCM WAV for backend/stt.
   MediaRecorder normally emits WebM/Opus, while SpeechRecognition.AudioFile
   accepts WAV/AIFF/FLAC. Capturing PCM here avoids a server-side ffmpeg
   dependency and keeps the STT endpoint small. */

function recorderError(code, message) {
  const error = new Error(message)
  error.code = code
  return error
}

function mergeChunks(chunks) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0)
  const merged = new Float32Array(length)
  let offset = 0
  for (const chunk of chunks) {
    merged.set(chunk, offset)
    offset += chunk.length
  }
  return merged
}

function writeAscii(view, offset, value) {
  for (let i = 0; i < value.length; i += 1) view.setUint8(offset + i, value.charCodeAt(i))
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)

  writeAscii(view, 0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeAscii(view, 8, 'WAVE')
  writeAscii(view, 12, 'fmt ')
  view.setUint32(16, 16, true)       // PCM header length
  view.setUint16(20, 1, true)        // PCM format
  view.setUint16(22, 1, true)        // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeAscii(view, 36, 'data')
  view.setUint32(40, samples.length * 2, true)

  let offset = 44
  for (let i = 0; i < samples.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
    offset += 2
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

export function audioRecordingSupport() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') {
    return { supported: false, reason: 'unsupported' }
  }
  if (!window.isSecureContext) return { supported: false, reason: 'insecure_context' }
  const AudioContext = window.AudioContext || window.webkitAudioContext
  if (!AudioContext || !navigator.mediaDevices?.getUserMedia) {
    return { supported: false, reason: 'unsupported' }
  }
  return { supported: true, reason: null }
}

export function canRecordAudio() {
  return audioRecordingSupport().supported
}

export class WavRecorder {
  constructor() {
    this.context = null
    this.stream = null
    this.source = null
    this.processor = null
    this.silentGain = null
    this.chunks = []
    this.sampleRate = 0
    this.active = false
  }

  async start() {
    if (!canRecordAudio()) {
      throw recorderError('unsupported', 'Trình duyệt không hỗ trợ ghi âm.')
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      })

      const AudioContext = window.AudioContext || window.webkitAudioContext
      this.context = new AudioContext()
      if (this.context.state === 'suspended') await this.context.resume()

      this.sampleRate = this.context.sampleRate
      this.source = this.context.createMediaStreamSource(this.stream)
      this.processor = this.context.createScriptProcessor(4096, 1, 1)
      this.silentGain = this.context.createGain()
      this.silentGain.gain.value = 0
      this.processor.onaudioprocess = (event) => {
        if (!this.active) return
        this.chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)))
      }

      this.source.connect(this.processor)
      this.processor.connect(this.silentGain)
      this.silentGain.connect(this.context.destination)
      this.active = true
    } catch (error) {
      await this.cancel()
      throw error
    }
  }

  async stop() {
    if (!this.active) throw recorderError('not_recording', 'Không có bản ghi âm đang chạy.')

    this.active = false
    const chunks = this.chunks
    const sampleRate = this.sampleRate
    await this.cleanup()

    const samples = mergeChunks(chunks)
    this.chunks = []
    if (!sampleRate || samples.length < sampleRate / 4) {
      throw recorderError('recording_too_short', 'Bản ghi âm quá ngắn.')
    }
    return encodeWav(samples, sampleRate)
  }

  async cancel() {
    this.active = false
    this.chunks = []
    await this.cleanup()
  }

  async cleanup() {
    if (this.processor) {
      this.processor.onaudioprocess = null
      this.processor.disconnect()
    }
    this.source?.disconnect()
    this.silentGain?.disconnect()
    this.stream?.getTracks().forEach((track) => track.stop())

    const context = this.context
    this.processor = null
    this.source = null
    this.silentGain = null
    this.stream = null
    this.context = null

    if (context && context.state !== 'closed') {
      try {
        await context.close()
      } catch {
        // The microphone tracks have already been stopped; nothing else to do.
      }
    }
  }
}
