import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../api/client.js'
import { useAuth } from '../store/AuthContext.jsx'

export default function LoginPage() {
  const navigate = useNavigate()
  const { loginUser } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await login(form)
      const { access_token, ...userData } = res.data
      loginUser(access_token, userData)
      navigate('/')
    } catch (e) {
      setError(e.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page" style={{ maxWidth: 420, paddingTop: 80 }}>
      <div className="card">
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: '2rem', marginBottom: 8 }}>⚡</div>
          <h2 style={{ fontWeight: 800 }}>Sign in to SALESTORM</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.85rem', marginTop: 4 }}>
            Demo: demo@salestorm.io / demo1234
          </p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              className="form-input"
              type="email"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              placeholder="you@example.com"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              className="form-input"
              type="password"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              placeholder="••••••••"
              required
            />
          </div>
          <button className="btn btn-primary btn-full btn-lg" type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: 20, color: 'var(--muted)', fontSize: '0.85rem' }}>
          No account?{' '}
          <Link to="/register" style={{ color: 'var(--red)' }}>Create one</Link>
        </p>
      </div>
    </div>
  )
}
