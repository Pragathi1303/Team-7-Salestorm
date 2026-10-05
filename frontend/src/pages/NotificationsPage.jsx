import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getNotifications, markNotificationRead, markAllRead } from '../api/client.js'
import { useAuth } from '../store/AuthContext.jsx'

const TYPE_ICON = {
  ORDER_CONFIRMED: '🎉', PAYMENT_FAILED: '❌', PAYMENT_SUCCESS: '✅',
  RESERVATION_CREATED: '🎫', RESERVATION_EXPIRED: '⏰',
  ORDER_SHIPPED: '🚚', ORDER_DELIVERED: '📦', ORDER_CANCELLED: '🚫',
}

export default function NotificationsPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) { navigate('/login'); return }
    load()
  }, [user])

  async function load() {
    try {
      const res = await getNotifications()
      setNotifications(res.data)
    } catch {}
    finally { setLoading(false) }
  }

  async function handleRead(id) {
    await markNotificationRead(id)
    setNotifications(ns => ns.map(n => n.notification_id === id ? { ...n, is_read: true } : n))
  }

  async function handleReadAll() {
    await markAllRead()
    setNotifications(ns => ns.map(n => ({ ...n, is_read: true })))
  }

  const unread = notifications.filter(n => !n.is_read).length

  if (loading) return <div className="page" style={{ textAlign: 'center', paddingTop: 80 }}><div className="spinner" /></div>

  return (
    <div className="page" style={{ maxWidth: 700 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ fontWeight: 800 }}>
          Notifications
          {unread > 0 && <span className="badge badge-red" style={{ marginLeft: 10 }}>{unread}</span>}
        </h2>
        {unread > 0 && (
          <button className="btn btn-ghost btn-sm" onClick={handleReadAll}>Mark all read</button>
        )}
      </div>

      {notifications.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <div style={{ fontSize: '3rem', marginBottom: 12 }}>🔔</div>
          <div style={{ color: 'var(--muted)' }}>No notifications yet</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {notifications.map(n => (
            <div
              key={n.notification_id}
              className="card card-sm"
              style={{
                borderColor: n.is_read ? 'var(--border)' : 'var(--blue)',
                background: n.is_read ? 'var(--surface)' : 'rgba(74,158,255,0.05)',
                cursor: n.is_read ? 'default' : 'pointer',
              }}
              onClick={() => !n.is_read && handleRead(n.notification_id)}
            >
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{ fontSize: '1.5rem', flexShrink: 0 }}>
                  {TYPE_ICON[n.notification_type] || '🔔'}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ fontWeight: n.is_read ? 400 : 700 }}>{n.title}</div>
                    <div style={{ color: 'var(--muted)', fontSize: '0.75rem', flexShrink: 0, marginLeft: 8 }}>
                      {new Date(n.created_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: '0.85rem', marginTop: 4 }}>{n.message}</div>
                  {n.order_id && (
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ marginTop: 8, fontSize: '0.75rem' }}
                      onClick={e => { e.stopPropagation(); navigate(`/orders/${n.order_id}`) }}
                    >
                      View Order →
                    </button>
                  )}
                </div>
                {!n.is_read && (
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--blue)', flexShrink: 0, marginTop: 6 }} />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
