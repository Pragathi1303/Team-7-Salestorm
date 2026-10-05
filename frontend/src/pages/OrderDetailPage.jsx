import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getOrder, cancelOrder } from '../api/client.js'
import { useAuth } from '../store/AuthContext.jsx'

const STATUS_BADGE = {
  CONFIRMED: 'badge-green', PROCESSING: 'badge-blue', SHIPPED: 'badge-blue',
  OUT_FOR_DELIVERY: 'badge-blue', DELIVERED: 'badge-green',
  CANCELLED: 'badge-red', FAILED: 'badge-red', REFUNDED: 'badge-muted',
  SUCCESS: 'badge-green', TIMEOUT: 'badge-muted',
  CREATED: 'badge-yellow', PACKED: 'badge-yellow',
}

const SHIPMENT_STEPS = ['CREATED', 'PACKED', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED']

function ShipmentTracker({ shipment }) {
  const currentIdx = SHIPMENT_STEPS.indexOf(shipment.status)
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <div style={{ fontWeight: 600 }}>🚚 {shipment.carrier || 'Carrier'}</div>
          <div style={{ color: 'var(--muted)', fontSize: '0.8rem', fontFamily: 'monospace' }}>
            {shipment.tracking_number}
          </div>
        </div>
        <span className={`badge ${STATUS_BADGE[shipment.status] || 'badge-muted'}`}>{shipment.status}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
        {SHIPMENT_STEPS.map((step, i) => (
          <React.Fragment key={step}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%',
                background: i <= currentIdx ? 'var(--green)' : 'var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '0.7rem', fontWeight: 700, color: i <= currentIdx ? '#000' : 'var(--muted)',
                transition: 'background 0.3s',
              }}>
                {i <= currentIdx ? '✓' : i + 1}
              </div>
              <div style={{ fontSize: '0.65rem', color: i <= currentIdx ? 'var(--green)' : 'var(--muted)', marginTop: 4, textAlign: 'center' }}>
                {step.replace('_', ' ')}
              </div>
            </div>
            {i < SHIPMENT_STEPS.length - 1 && (
              <div style={{
                height: 2, flex: 2, marginBottom: 20,
                background: i < currentIdx ? 'var(--green)' : 'var(--border)',
                transition: 'background 0.3s',
              }} />
            )}
          </React.Fragment>
        ))}
      </div>
      {shipment.estimated_delivery && (
        <div style={{ marginTop: 12, color: 'var(--muted)', fontSize: '0.8rem' }}>
          Estimated delivery: {new Date(shipment.estimated_delivery).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
        </div>
      )}
    </div>
  )
}

export default function OrderDetailPage() {
  const { orderId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [order, setOrder] = useState(null)
  const [loading, setLoading] = useState(true)
  const [cancelling, setCancelling] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getOrder(orderId)
      .then(res => setOrder(res.data))
      .catch(() => setError('Order not found'))
      .finally(() => setLoading(false))
  }, [orderId])

  async function handleCancel() {
    if (!window.confirm('Cancel this order?')) return
    setCancelling(true)
    try {
      const res = await cancelOrder(orderId)
      setOrder(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Cannot cancel order')
    } finally {
      setCancelling(false)
    }
  }

  if (loading) return <div className="page" style={{ textAlign: 'center', paddingTop: 80 }}><div className="spinner" /></div>
  if (error || !order) return <div className="page"><div className="alert alert-error">{error || 'Order not found'}</div></div>

  const canCancel = ['CONFIRMED', 'PROCESSING'].includes(order.status)

  return (
    <div className="page" style={{ maxWidth: 700 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/orders')}>← Orders</button>
        <h2 style={{ fontWeight: 800 }}>Order #{order.order_id.slice(0, 8).toUpperCase()}</h2>
        <span className={`badge ${STATUS_BADGE[order.status] || 'badge-muted'}`}>{order.status}</span>
      </div>

      {/* Items */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontWeight: 700, marginBottom: 12 }}>Items</div>
        {order.items.map(item => (
          <div key={item.order_item_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
            <div>
              <div style={{ fontWeight: 600 }}>{item.product_name}</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>Qty: {item.quantity} × ₹{Number(item.unit_price).toLocaleString()}</div>
            </div>
            <div style={{ fontWeight: 700 }}>₹{Number(item.subtotal).toLocaleString()}</div>
          </div>
        ))}
        <div style={{ marginTop: 12 }}>
          {order.discount_amount > 0 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--green)', marginBottom: 6 }}>
              <span>Discount {order.coupon_code && `(${order.coupon_code})`}</span>
              <span>−₹{Number(order.discount_amount).toLocaleString()}</span>
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 800, fontSize: '1.1rem' }}>
            <span>Total</span>
            <span style={{ color: 'var(--red)' }}>₹{Number(order.total_amount).toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Shipment */}
      {order.shipments?.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 700, marginBottom: 16 }}>Shipment Tracking</div>
          <ShipmentTracker shipment={order.shipments[0]} />
        </div>
      )}

      {/* Payment */}
      {order.payments?.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 700, marginBottom: 12 }}>Payment</div>
          {order.payments.map(p => (
            <div key={p.payment_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600 }}>{p.payment_method}</div>
                <div style={{ color: 'var(--muted)', fontSize: '0.75rem', fontFamily: 'monospace' }}>{p.payment_reference}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontWeight: 700 }}>₹{Number(p.amount).toLocaleString()}</div>
                <span className={`badge ${STATUS_BADGE[p.status] || 'badge-muted'}`}>{p.status}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Shipping address */}
      {order.shipping_address && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Shipping Address</div>
          {(() => {
            try {
              const addr = JSON.parse(order.shipping_address)
              return (
                <div style={{ color: 'var(--muted)', fontSize: '0.9rem', lineHeight: 1.8 }}>
                  <div>{addr.full_name}</div>
                  <div>{addr.line1}</div>
                  <div>{addr.city}, {addr.state} {addr.pincode}</div>
                  <div>{addr.country}</div>
                </div>
              )
            } catch { return <div style={{ color: 'var(--muted)' }}>{order.shipping_address}</div> }
          })()}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 10 }}>
        {canCancel && (
          <button className="btn btn-danger" onClick={handleCancel} disabled={cancelling}>
            {cancelling ? 'Cancelling…' : 'Cancel Order'}
          </button>
        )}
        <button className="btn btn-ghost" onClick={() => navigate('/orders')}>← All Orders</button>
      </div>
    </div>
  )
}
