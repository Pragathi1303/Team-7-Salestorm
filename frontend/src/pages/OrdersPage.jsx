import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getOrders } from '../api/client.js'

const STATUS_BADGE = {
  CONFIRMED: 'badge-green', PROCESSING: 'badge-cyan', SHIPPED: 'badge-cyan',
  OUT_FOR_DELIVERY: 'badge-cyan', DELIVERED: 'badge-green',
  CANCELLED: 'badge-red', FAILED: 'badge-red', REFUNDED: 'badge-muted',
}

export default function OrdersPage() {
  const navigate = useNavigate()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getOrders()
      .then(res => setOrders(res.data || []))
      .catch(() => setOrders([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="page" style={{ textAlign: 'center', paddingTop: 80 }}><div className="spinner" /></div>

  return (
    <div className="page" style={{ maxWidth: 840 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: '2.2rem' }}>📦 Order History & Tracking</h1>
          <p style={{ color: 'var(--muted)', fontSize: '0.92rem' }}>
            Track your confirmed flash sale orders, shipments, and live delivery status.
          </p>
        </div>
      </div>

      {orders.length === 0 ? (
        <div className="card card-glow" style={{ textAlign: 'center', padding: 56 }}>
          <div style={{ fontSize: '4rem', marginBottom: 16 }}>📦</div>
          <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>No orders found</h2>
          <p style={{ color: 'var(--muted)', marginBottom: 28 }}>Place your first flash sale order to view live shipment tracking.</p>
          <button className="btn btn-primary btn-lg" onClick={() => navigate('/sale')}>
            ⚡ Join Live Flash Sale
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {orders.map(order => (
            <div
              key={order.order_id}
              className="card card-glow"
              style={{ cursor: 'pointer', transition: 'all 0.25s ease' }}
              onClick={() => navigate(`/orders/${order.order_id}`)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                <div>
                  <div style={{ fontFamily: 'var(--font-code)', fontSize: '0.85rem', color: 'var(--neon-cyan)', marginBottom: 4 }}>
                    #{order.order_id.slice(0, 8).toUpperCase()}
                  </div>
                  <h3 style={{ fontSize: '1.15rem', marginBottom: 4 }}>
                    {order.items?.[0]?.product_name || 'Flash Sale Item'}
                    {order.items?.length > 1 && ` +${order.items.length - 1} more`}
                  </h3>
                  <div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>
                    Placed on: {new Date(order.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 900, fontSize: '1.3rem', color: 'var(--neon-red)', marginBottom: 6 }}>
                    ₹{Number(order.total_amount).toLocaleString()}
                  </div>
                  <span className={`badge ${STATUS_BADGE[order.status] || 'badge-muted'}`}>{order.status}</span>
                </div>
              </div>

              {order.shipments?.[0] && (
                <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, fontSize: '0.85rem', color: 'var(--muted)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span>🚚 Carrier: <strong style={{ color: '#fff' }}>{order.shipments[0].carrier}</strong></span>
                    <span>Tracking: <code style={{ color: 'var(--neon-cyan)' }}>{order.shipments[0].tracking_number}</code></span>
                  </div>
                  <span className={`badge ${STATUS_BADGE[order.shipments[0].status] || 'badge-muted'}`}>
                    {order.shipments[0].status}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
