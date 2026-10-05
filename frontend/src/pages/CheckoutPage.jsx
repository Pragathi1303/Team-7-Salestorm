import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { v4 as uuidv4 } from 'uuid'
import { checkout, validateCoupon, createPayment, getOrder } from '../api/client.js'
import { useAuth } from '../store/AuthContext.jsx'
import { useCountdown } from '../hooks/useCountdown.js'

function ExpiryTimer({ expiresAt }) {
  const { display, expired, seconds } = useCountdown(expiresAt)
  if (!expiresAt) return null
  const urgent = !expired && seconds < 10
  return (
    <div style={{ background: 'rgba(10, 12, 22, 0.8)', borderRadius: 10, padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: '1px solid var(--border)' }}>
      <span style={{ color: 'var(--muted)', fontSize: '0.88rem', fontWeight: 600 }}>Reservation Lock Timer</span>
      <span style={{ fontWeight: 800, fontSize: '1.2rem', fontFamily: 'var(--font-code)', color: expired || urgent ? 'var(--neon-red)' : 'var(--neon-yellow)' }}>
        {expired ? 'EXPIRED' : display}
      </span>
    </div>
  )
}

function OrderConfirmed({ order }) {
  const navigate = useNavigate()
  return (
    <div className="card card-glow" style={{ borderColor: 'var(--neon-green)', textAlign: 'center', padding: 40, boxShadow: '0 0 40px rgba(0, 230, 118, 0.2)' }}>
      <div style={{ fontSize: '4rem', marginBottom: 16 }}>🎉</div>
      <h2 className="text-neon-green" style={{ fontSize: '2rem', marginBottom: 8 }}>Order Confirmed & Sealed!</h2>
      <p style={{ color: 'var(--muted)', fontSize: '1rem', marginBottom: 28 }}>
        Inventory permanently transferred reserved → sold. Payment processed atomically.
      </p>

      <div style={{ background: '#0a0c16', borderRadius: 12, padding: '16px', marginBottom: 20, border: '1px solid var(--border)', textAlign: 'left' }}>
        <div style={{ color: 'var(--muted)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: 4 }}>Order Reference Number</div>
        <div style={{ fontFamily: 'var(--font-code)', fontSize: '1rem', color: 'var(--neon-cyan)' }}>{order.order_id}</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 28 }}>
        <div style={{ background: '#0a0c16', borderRadius: 12, padding: 16, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.8rem', marginBottom: 4 }}>Status</div>
          <span className="badge badge-green">{order.status}</span>
        </div>
        <div style={{ background: '#0a0c16', borderRadius: 12, padding: 16, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.8rem', marginBottom: 4 }}>Total Paid</div>
          <div style={{ fontWeight: 900, fontSize: '1.2rem', color: '#fff' }}>₹{Number(order.total_amount).toLocaleString()}</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
        <button className="btn btn-primary btn-lg" onClick={() => navigate(`/orders/${order.order_id}`)}>View Order Details &rarr;</button>
        <button className="btn btn-ghost btn-lg" onClick={() => navigate('/')}>← Return to Store</button>
      </div>
    </div>
  )
}

const PAYMENT_METHODS = [
  { id: 'CARD', label: '💳 Credit / Debit Card' },
  { id: 'UPI', label: '📱 Instant UPI Pay' },
  { id: 'NET_BANKING', label: '🏦 Net Banking' },
  { id: 'WALLET', label: '👛 Flash Wallet' },
]

export default function CheckoutPage() {
  const { reservationId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [checkoutData, setCheckoutData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)
  const [order, setOrder] = useState(null)
  const [paymentStatus, setPaymentStatus] = useState(null)
  const [error, setError] = useState(null)
  const [coupon, setCoupon] = useState('')
  const [couponResult, setCouponResult] = useState(null)
  const [paymentMethod, setPaymentMethod] = useState('CARD')
  const [address, setAddress] = useState({ full_name: 'Flash Customer', line1: '100 Flash Sale Avenue', city: 'Tech City', state: 'Karnataka', pincode: '560001', country: 'India' })

  const effectiveCustomerId = user?.customer_id || sessionStorage.getItem('salestorm_customer_id')

  useEffect(() => {
    if (user?.name) setAddress(a => ({ ...a, full_name: user.name }))
    if (!effectiveCustomerId) {
      navigate('/sale')
      return
    }
    loadCheckout()
  }, [reservationId, effectiveCustomerId])

  async function loadCheckout(couponCode) {
    try {
      const res = await checkout({
        reservation_id: reservationId,
        customer_id: effectiveCustomerId,
        coupon_code: couponCode
      })
      setCheckoutData(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load checkout details. Reservation may have expired.')
    } finally {
      setLoading(false)
    }
  }

  async function handleApplyCoupon() {
    if (!coupon.trim() || !checkoutData) return
    try {
      const res = await validateCoupon({ code: coupon.trim().toUpperCase(), amount: checkoutData.subtotal })
      setCouponResult(res.data)
      if (res.data.valid) loadCheckout(coupon.trim().toUpperCase())
    } catch {
      setCouponResult({ valid: false, message: 'Invalid or expired promo coupon' })
    }
  }

  async function pay(outcome) {
    if (!checkoutData || paying) return
    setPaying(true)
    setError(null)
    try {
      const res = await createPayment({
        reservation_id: reservationId,
        customer_id: effectiveCustomerId,
        amount: checkoutData.total_amount,
        payment_method: paymentMethod,
        idempotency_key: uuidv4(),
        simulate_outcome: outcome,
        coupon_code: checkoutData.coupon_code || undefined,
        shipping_address: address.line1 ? address : undefined,
      })
      const payment = res.data
      setPaymentStatus(payment.status)
      if (payment.status === 'SUCCESS' && payment.order_id) {
        const orderRes = await getOrder(payment.order_id)
        setOrder(orderRes.data)
      } else if (payment.status === 'FAILED') {
        setError('❌ Mock Payment simulation failed. Reserved inventory released back to pool.')
      } else if (payment.status === 'TIMEOUT') {
        setError('⏱ Payment timed out. Transaction status marked UNKNOWN (Reconciliation Worker pending).')
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Payment execution error')
    } finally {
      setPaying(false)
    }
  }

  if (loading) return <div className="page" style={{ textAlign: 'center', paddingTop: 80 }}><div className="spinner" /></div>
  if (order) return <div className="page" style={{ maxWidth: 640 }}><OrderConfirmed order={order} /></div>

  const expired = checkoutData?.expires_at ? new Date(checkoutData.expires_at) < new Date() : false

  return (
    <div className="page" style={{ maxWidth: 680 }}>
      <h1 style={{ fontSize: '2.2rem', marginBottom: 24 }}>⚡ Complete Order Checkout</h1>

      {checkoutData && (
        <div className="card card-glow" style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: '1.2rem', marginBottom: 16 }}>Order Summary</h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1.1rem' }}>{checkoutData.product_name}</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.88rem' }}>
                Qty: {checkoutData.quantity} × ₹{Number(checkoutData.unit_price).toLocaleString()}
              </div>
            </div>
            <div style={{ fontWeight: 900, fontSize: '1.2rem' }}>₹{Number(checkoutData.subtotal).toLocaleString()}</div>
          </div>

          {checkoutData.discount_amount > 0 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--neon-green)', marginBottom: 10, fontWeight: 700 }}>
              <span>Coupon Discount ({checkoutData.coupon_code})</span>
              <span>−₹{Number(checkoutData.discount_amount).toLocaleString()}</span>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 900, fontSize: '1.3rem', borderTop: '1px solid var(--border)', paddingTop: 14, marginTop: 12 }}>
            <span>Final Amount</span>
            <span style={{ color: 'var(--neon-red)' }}>₹{Number(checkoutData.total_amount).toLocaleString()}</span>
          </div>

          <div style={{ marginTop: 16 }}>
            <ExpiryTimer expiresAt={checkoutData.expires_at} />
          </div>
        </div>
      )}

      {/* Coupon Box */}
      {checkoutData && !checkoutData.coupon_code && (
        <div className="card" style={{ marginBottom: 24 }}>
          <label className="form-label">Apply Promo Coupon</label>
          <div style={{ display: 'flex', gap: 10 }}>
            <input
              className="form-input"
              placeholder="e.g. STORM10, FLAT500"
              value={coupon}
              onChange={e => { setCoupon(e.target.value); setCouponResult(null) }}
              style={{ flex: 1 }}
            />
            <button className="btn btn-neon-cyan" onClick={handleApplyCoupon}>Apply Code</button>
          </div>
          {couponResult && (
            <div className={`alert ${couponResult.valid ? 'alert-success' : 'alert-error'}`} style={{ marginTop: 12, marginBottom: 0 }}>
              {couponResult.valid ? `✅ Discount applied: Saved ₹${Number(couponResult.discount_amount).toLocaleString()}` : `❌ ${couponResult.message}`}
            </div>
          )}
        </div>
      )}

      {/* Shipping Address */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: 16 }}>Shipping Address</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          {[
            { key: 'full_name', label: 'Recipient Name', span: 2 },
            { key: 'line1', label: 'Street Address', span: 2 },
            { key: 'city', label: 'City' },
            { key: 'state', label: 'State' },
            { key: 'pincode', label: 'Pincode' },
          ].map(f => (
            <div key={f.key} className="form-group" style={{ gridColumn: f.span ? `span ${f.span}` : undefined, marginBottom: 0 }}>
              <label className="form-label">{f.label}</label>
              <input
                className="form-input"
                value={address[f.key] || ''}
                onChange={e => setAddress(a => ({ ...a, [f.key]: e.target.value }))}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Payment Selection */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: 16 }}>Select Payment Gateway</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {PAYMENT_METHODS.map(m => (
            <button
              key={m.id}
              className={`btn ${paymentMethod === m.id ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setPaymentMethod(m.id)}
              style={{ justifyContent: 'flex-start', padding: '14px' }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 20 }}>{error}</div>}

      {checkoutData && !expired && !paymentStatus && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <button className="btn btn-success btn-full btn-lg" onClick={() => pay('SUCCESS')} disabled={paying}>
            {paying ? '⏳ Processing Payment…' : `⚡ CONFIRM & PAY ₹${Number(checkoutData.total_amount).toLocaleString()}`}
          </button>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <button className="btn btn-danger" onClick={() => pay('FAILED')} disabled={paying}>❌ Test Payment Failure</button>
            <button className="btn btn-warning" onClick={() => pay('TIMEOUT')} disabled={paying}>⏱ Test Payment Timeout</button>
          </div>
        </div>
      )}

      {checkoutData && expired && !paymentStatus && (
        <div className="card" style={{ borderColor: 'var(--neon-red)', textAlign: 'center', padding: 24 }}>
          <div style={{ color: 'var(--neon-red)', fontWeight: 800, fontSize: '1.2rem', marginBottom: 12 }}>
            ⏱ Reservation Lock Expired (30s timeout)
          </div>
          <p style={{ color: 'var(--muted)', marginBottom: 16 }}>
            Inventory held for this reservation has been safely released back to available pool.
          </p>
          <button className="btn btn-primary" onClick={() => navigate('/sale')}>
            ⚡ Re-join Flash Sale
          </button>
        </div>
      )}
    </div>
  )
}
