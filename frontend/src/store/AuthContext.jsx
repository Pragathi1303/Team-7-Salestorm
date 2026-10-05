import React, { createContext, useContext, useState, useEffect } from 'react'
import { getMe } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('salestorm_token')
    if (token) {
      getMe()
        .then(res => setUser(res.data))
        .catch(() => {
          localStorage.removeItem('salestorm_token')
          localStorage.removeItem('salestorm_user')
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  function loginUser(token, userData) {
    localStorage.setItem('salestorm_token', token)
    localStorage.setItem('salestorm_user', JSON.stringify(userData))
    setUser(userData)
  }

  function logoutUser() {
    localStorage.removeItem('salestorm_token')
    localStorage.removeItem('salestorm_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, loginUser, logoutUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
