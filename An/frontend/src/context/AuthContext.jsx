import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { authApi, profileApi } from '../lib/api.js'

const STORAGE_KEY = 'an.auth'
const AuthContext = createContext(null)

function loadStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(loadStored) // { token, user, profile } | null
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (auth) localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
    else localStorage.removeItem(STORAGE_KEY)
  }, [auth])

  // Xác nhận token còn dùng được khi tải lại trang; nếu hết hạn thì đăng xuất êm.
  useEffect(() => {
    let cancelled = false
    async function check() {
      if (!auth?.token) {
        setReady(true)
        return
      }
      try {
        const profile = await profileApi.get(auth.token)
        if (!cancelled) setAuth((a) => (a ? { ...a, profile } : a))
      } catch {
        if (!cancelled) setAuth(null)
      } finally {
        if (!cancelled) setReady(true)
      }
    }
    check()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const register = useCallback(async ({ email, password, age, gender }) => {
    const data = await authApi.register({ email, password, age, gender })
    setAuth(data)
    return data
  }, [])

  const login = useCallback(async ({ email, password }) => {
    const data = await authApi.login({ email, password })
    setAuth(data)
    return data
  }, [])

  const logout = useCallback(() => setAuth(null), [])

  const updateProfile = useCallback(
    async (updates) => {
      if (!auth?.token) return
      const profile = await profileApi.update(auth.token, updates)
      setAuth((a) => (a ? { ...a, profile } : a))
      return profile
    },
    [auth?.token],
  )

  const value = {
    ready,
    token: auth?.token || null,
    user: auth?.user || null,
    profile: auth?.profile || null,
    isFemale: auth?.profile?.gender === 'nu',
    register,
    login,
    logout,
    updateProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth() phải dùng bên trong <AuthProvider>')
  return ctx
}
