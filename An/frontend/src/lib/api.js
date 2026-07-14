/* ============================================================
   api.js — client gọi backend An (auth, hồ sơ sức khỏe, lịch, chu kỳ)
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

export const cycleApi = {
  list: (token) => request('/cycle', { token }),
  create: (token, entry) => request('/cycle', { method: 'POST', body: entry, token }),
  remove: (token, id) => request(`/cycle/${id}`, { method: 'DELETE', token }),
}

export function triageUrl() {
  return `${API_BASE}/triage`
}
