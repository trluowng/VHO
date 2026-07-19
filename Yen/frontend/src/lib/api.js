/* ============================================================
   api.js — client gọi backend Yên (auth, hồ sơ sức khỏe, lịch, chu kỳ)
   ============================================================ */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export function isApiConfigured() {
  return !!API_BASE
}

async function request(path, { method = 'GET', body, token, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (auth && token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error(ERROR_LABELS[data.detail] || data.detail || `Lỗi máy chủ (${res.status})`)
    err.status = res.status
    err.detail = data.detail
    throw err
  }
  return data
}

const ERROR_LABELS = {
  invalid_email: 'Email không hợp lệ.',
  password_too_short: 'Mật khẩu cần tối thiểu 6 ký tự.',
  invalid_gender: 'Vui lòng chọn giới tính.',
  invalid_age: 'Tuổi không hợp lệ.',
  email_taken: 'Email này đã được đăng ký.',
  invalid_credentials: 'Email hoặc mật khẩu không đúng.',
  unauthorized: 'Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.',
  period_start_date_in_future: 'Ngày bắt đầu kỳ kinh không thể ở tương lai.',
  period_start_date_required: 'Vui lòng chọn ngày bắt đầu kỳ kinh.',
  invalid_period_start_date: 'Ngày bắt đầu kỳ kinh không hợp lệ.',
  empty_audio: 'Bản ghi âm đang trống.',
  invalid_audio: 'Không đọc được bản ghi âm. Vui lòng thử lại.',
  no_speech: 'Không nhận diện được lời nói. Hãy nói gần micro và thử lại.',
  audio_too_large: 'Bản ghi âm quá dài. Vui lòng ghi tối đa 30 giây.',
  stt_service_unavailable: 'Dịch vụ nhận dạng giọng nói đang bận. Vui lòng thử lại.',
  slot_already_booked: 'Khung giờ này vừa có người đặt trước bạn. Vui lòng chọn khung giờ khác.',
  slot_not_found: 'Khung giờ này không còn tồn tại. Vui lòng chọn lại.',
  doctor_not_found: 'Không tìm thấy bác sĩ này.',
}

export const authApi = {
  register: (payload) => request('/auth/register', { method: 'POST', body: payload, auth: false }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload, auth: false }),
}

export const profileApi = {
  get: (token) => request('/profile', { token }),
  update: (token, updates) => request('/profile', { method: 'PUT', body: updates, token }),
}

export const calendarApi = {
  list: (token, month) => request(`/calendar${month ? `?month=${month}` : ''}`, { token }),
  create: (token, entry) => request('/calendar', { method: 'POST', body: entry, token }),
  remove: (token, id) => request(`/calendar/${id}`, { method: 'DELETE', token }),
}

export const doctorsApi = {
  list: (token, { query, campus, specialty, timeSlot } = {}) => {
    const params = new URLSearchParams()
    if (query) params.set('query', query)
    if (campus) params.set('campus', campus)
    if (specialty) params.set('specialty', specialty)
    if (timeSlot) params.set('time_slot', timeSlot)
    const qs = params.toString()
    return request(`/doctors${qs ? `?${qs}` : ''}`, { token })
  },
  schedule: (token, doctorId) => request(`/doctors/${doctorId}/schedule`, { token }),
  book: (token, doctorId, slot) => request(`/doctors/${doctorId}/book`, { method: 'POST', body: slot, token }),
}

export const cycleApi = {
  list: (token) => request('/cycle', { token }),
  create: (token, entry) => request('/cycle', { method: 'POST', body: entry, token }),
  remove: (token, id) => request(`/cycle/${id}`, { method: 'DELETE', token }),
}

export const sttApi = {
  transcribe: async (token, audioBlob) => {
    const headers = { 'Content-Type': 'audio/wav' }
    if (token) headers.Authorization = `Bearer ${token}`

    const res = await fetch(`${API_BASE}/stt/transcribe`, {
      method: 'POST',
      headers,
      body: audioBlob,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      const err = new Error(ERROR_LABELS[data.detail] || data.detail || `Lỗi máy chủ (${res.status})`)
      err.status = res.status
      err.detail = data.detail
      throw err
    }
    return data
  },
}

export const ttsApi = {
  /** Trả về Blob audio/mpeg -- trình duyệt tự phát bằng thẻ <audio>, backend không
   *  phát âm thanh cục bộ (server có thể chạy headless trên cloud). */
  synthesize: async (token, text) => {
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers.Authorization = `Bearer ${token}`

    const res = await fetch(`${API_BASE}/tts`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ text }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      const err = new Error(ERROR_LABELS[data.detail] || data.detail || `Lỗi máy chủ (${res.status})`)
      err.status = res.status
      err.detail = data.detail
      throw err
    }
    return res.blob()
  },
}

export function triageUrl() {
  return `${API_BASE}/triage`
}
