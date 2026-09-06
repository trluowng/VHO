/* ============================================================
   api.js — client gọi backend Yên (hồ sơ sức khỏe, lịch, chu kỳ)
   ============================================================ */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export function isApiConfigured() {
  return !!API_BASE
}

async function request(path, { method = 'GET', body, clientId } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (clientId) headers['X-Client-ID'] = clientId

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
  invalid_gender: 'Vui lòng chọn giới tính.',
  invalid_age: 'Tuổi không hợp lệ.',
  invalid_birth_date: 'Ngày sinh không hợp lệ.',
  client_id_required: 'Không xác định được phiên trên trình duyệt. Vui lòng tải lại trang.',
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

export const profileApi = {
  get: (clientId) => request('/profile', { clientId }),
  update: (clientId, updates) => request('/profile', { method: 'PUT', body: updates, clientId }),
}

export const calendarApi = {
  list: (clientId, month) => request(`/calendar${month ? `?month=${month}` : ''}`, { clientId }),
  create: (clientId, entry) => request('/calendar', { method: 'POST', body: entry, clientId }),
  remove: (clientId, id) => request(`/calendar/${id}`, { method: 'DELETE', clientId }),
}

export const doctorsApi = {
  list: (clientId, { query, campus, specialty, timeSlot } = {}) => {
    const params = new URLSearchParams()
    if (query) params.set('query', query)
    if (campus) params.set('campus', campus)
    if (specialty) params.set('specialty', specialty)
    if (timeSlot) params.set('time_slot', timeSlot)
    const qs = params.toString()
    return request(`/doctors${qs ? `?${qs}` : ''}`, { clientId })
  },
  schedule: (clientId, doctorId) => request(`/doctors/${doctorId}/schedule`, { clientId }),
  book: (clientId, doctorId, slot) => request(`/doctors/${doctorId}/book`, { method: 'POST', body: slot, clientId }),
}

export const cycleApi = {
  list: (clientId) => request('/cycle', { clientId }),
  create: (clientId, entry) => request('/cycle', { method: 'POST', body: entry, clientId }),
  remove: (clientId, id) => request(`/cycle/${id}`, { method: 'DELETE', clientId }),
}

export const sttApi = {
  transcribe: async (clientId, audioBlob) => {
    const headers = { 'Content-Type': 'audio/wav' }
    if (clientId) headers['X-Client-ID'] = clientId

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
  synthesize: async (clientId, text) => {
    const headers = { 'Content-Type': 'application/json' }
    if (clientId) headers['X-Client-ID'] = clientId

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
