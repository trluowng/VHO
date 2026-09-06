import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { profileApi } from '../lib/api.js'

const STORAGE_KEY = 'yen.clientId'
const SessionContext = createContext(null)

function createClientId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  if (globalThis.crypto?.getRandomValues) {
    const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16))
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  }
  return `${Date.now()}${Math.random().toString(36).slice(2)}`
}

function loadClientId() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return stored

    // Giữ lại dữ liệu của người đã đăng nhập ở phiên bản cũ bằng cách dùng user id
    // cũ làm mã phiên mới, rồi xoá token/mật khẩu phiên khỏi trình duyệt.
    const legacyAuth = JSON.parse(localStorage.getItem('an.auth') || 'null')
    const legacyUserId = legacyAuth?.user?.id
    if (legacyUserId) {
      localStorage.setItem(STORAGE_KEY, legacyUserId)
      localStorage.removeItem('an.auth')
      return legacyUserId
    }
  } catch {
    // localStorage có thể bị chặn trong chế độ riêng tư; phiên vẫn dùng được tạm thời.
  }

  const clientId = createClientId()
  try {
    localStorage.setItem(STORAGE_KEY, clientId)
    localStorage.removeItem('an.auth')
  } catch {
    // Bỏ qua khi trình duyệt không cho phép lưu cục bộ.
  }
  return clientId
}

export function SessionProvider({ children }) {
  const clientId = useMemo(loadClientId, [])
  const [profile, setProfile] = useState(null)

  useEffect(() => {
    let cancelled = false
    profileApi.get(clientId)
      .then((data) => {
        if (!cancelled) setProfile(data)
      })
      .catch((error) => {
        console.warn('[Yên] Không tải được hồ sơ đã lưu:', error.message)
      })
    return () => { cancelled = true }
  }, [clientId])

  const updateProfile = useCallback(async (updates) => {
    const nextProfile = await profileApi.update(clientId, updates)
    setProfile(nextProfile)
    return nextProfile
  }, [clientId])

  // /triage may extract and persist profile facts that the user states in chat.
  // Mirror that authoritative backend snapshot locally so every tab sees it
  // immediately without issuing a duplicate PUT request.
  const syncProfile = useCallback((nextProfile) => {
    if (nextProfile) setProfile(nextProfile)
  }, [])

  const value = {
    clientId,
    profile,
    isFemale: profile?.gender === 'nu',
    updateProfile,
    syncProfile,
  }

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession() {
  const context = useContext(SessionContext)
  if (!context) throw new Error('useSession() phải dùng bên trong <SessionProvider>')
  return context
}
