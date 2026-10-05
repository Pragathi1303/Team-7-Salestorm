import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/AuthContext.jsx'
import { logout } from '../api/client.js'

export default function ProfilePage() {
  const navigate = useNavigate()
  const { user, logoutUser } = useAuth()

  if (!user) { navigate('/login'); return null }

  async function handleLogout() {
    try { await logout() } catch {}
    logoutUser()
    navigate('/login')
  }

  return (
    <div className="page" style={{ maxWidth: 500 }}>
      <h2 style={{ fontWeight: 800, marginBottom: 24 }}>My Profile</h2>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
          <div style={{
            width: 64, height: 64, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--red), var(--purple))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.5rem', fontWeight: 900, color: '#fff',
          }}>
            {user.name?.[0]?.toUpperCase() || '?'}
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.2rem' }}>{user.name}</div>
            <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{user.email}</div>
            <span className={`badge ${user.role === 'ADMIN' ? 'badge-red' : 'badge-blue'}`} style={{ marginTop: 4 }}>
              {user.role}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[
            { label: 'Customer ID', value: user.customer_id, mono: true },
            { label: 'Email', value: user.email },
            { label: 'Role', value: user.role },
          ].map(row => (
            <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
              <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{row.label}</span>
              <span style={{ fontFamily: row.mono ? 'monospace' : undefined, fontSize: row.mono ? '0.8rem' : undefined }}>
                {row.value}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontWeight: 700, marginBottom: 12 }}>Quick Links</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            { label: '📦 My Orders', path: '/orders' },
            { label: '🔔 Notifications', path: '/notifications' },
            { label: '🛒 Cart', path: '/cart' },
            ...(user.role === 'ADMIN' ? [{ label: '⚙️ Admin Dashboard', path: '/admin' }] : []),
          ].map(link => (
            <button key={link.path} className="btn btn-ghost" style={{ justifyContent: 'flex-start' }}
              onClick={() => navigate(link.path)}>
              {link.label}
            </button>
          ))}
        </div>
      </div>

      <button className="btn btn-danger btn-full" onClick={handleLogout}>Sign Out</button>
    </div>
  )
}
