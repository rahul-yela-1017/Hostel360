import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import api from './api'

const AuthContext = createContext(null)
export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('hostel_user')) } catch { return null }
  })
  const [loading, setLoading] = useState(false)
  const login = async (email, password) => {
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { email, password })
      localStorage.setItem('hostel_token', data.access_token)
      localStorage.setItem('hostel_user', JSON.stringify(data.user))
      setUser(data.user)
      return data.user
    } finally { setLoading(false) }
  }
  const changePassword = async (currentPassword, newPassword) => {
    await api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword })
    const updated = { ...user, must_change_password: false }
    localStorage.setItem('hostel_user', JSON.stringify(updated))
    setUser(updated)
  }
  const logout = () => {
    localStorage.removeItem('hostel_token'); localStorage.removeItem('hostel_user'); setUser(null)
  }
  useEffect(() => {
    const handler = () => setUser(null)
    window.addEventListener('hostel:unauthorized', handler)
    return () => window.removeEventListener('hostel:unauthorized', handler)
  }, [])
  const value = useMemo(() => ({ user, login, logout, changePassword, loading }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export const useAuth = () => useContext(AuthContext)
