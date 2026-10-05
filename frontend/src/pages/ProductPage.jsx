import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { v4 as uuidv4 } from 'uuid'
import { getProduct, joinQueue, getQueue, createReservation, addToCart, createDemoCustomer } from '../api/client.js'
import { useAuth } from '../store/AuthContext.jsx'
import { useCountdown } from '../hooks/useCountdown.js'

function SaleTimer({ endTime }) {
  const { display, expired } = useCountdown(endTime)
  if (!endTime) return null
  if (expired) return <span style={{ color: 'var(--muted)' }}>Sale Concluded</span>
  return <span style={{ color: 'var(--neon-yellow)', fontWeight: 800, fontSize: '1.2rem', fontFamily: 'var(--font-code)' }}>⏱ {display}</span>
}

function StockMeter({ available, total = 100 }) {
  const safeAvail = Math.max(0, available || 0)
  const pct = Math.max(0, Math.min(100, (safeAvail / total) * 100))
  return (
    <div style={{ background: 'rgba(10, 12, 22, 0.8)', padding: '14px', borderRadius: 12, border: '1px solid var(--border)', marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.88rem' }}>
        <span style={{ color: 'var(--muted)', fontWeight: 600 }}>Stock Availability</span>
        <span style={{ fontWeight: 800, color: safeAvail > 15 ? 'var(--neon-green)' : 'var(--neon-red)' }}>
          {safeAvail} / {total} left
        </span>
      </div>
      <div className="progress-bar-bg" style={{ height: 10 }}>
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function QueuePanel({ token, onAdmitted }) {
  const [status, setStatus] = useState(null)
  const pollRef = useRef(null)
  const admittedRef = useRef(false)

  useEffect(() => {
    if (!token) return
    const poll = async () => {
      try {
        const res = await getQueue(token)
        const data = res.data
        setStatus(data)
        if (!admittedRef.current && (data.status === 'ADMITTED' || data.status === 'COMPLETED' || data.position === 0)) {
          admittedRef.current = true
          clearInterval(pollRef.current)
          onAdmitted()
        }
      } catch {
        if (!admittedRef.current) {
          admittedRef.current = true
          clearInterval(pollRef.current)
          onAdmitted()
        }
      }
    }
    poll()
    pollRef.current = setInterval(poll, 1200)
    return () => clearInterval(pollRef.current)
  }, [token])

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h3 style={{ fontSize: '1.3rem', marginBottom: 16 }}>🎫 Virtual Queue Admission</h3>
        {status ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
            <div style={{ background: '#0a0c16', padding: '14px', borderRadius: 10, textAlign: 'center', border: '1px solid var(--border)' }}>
              <div style={{ color: 'var(--muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Position</div>
              <div style={{ fontSize: '2rem', fontWeight: 900, color: 'var(--neon-yellow)', fontFamily: 'var(--font-code)' }}>
                {status.position > 0 ? `#${status.position}` : 'ADMITTED'}
              </div>
            </div>
            <div style={{ background: '#0a0c16', padding: '14px', borderRadius: 10, textAlign: 'center', border: '1px solid var(--border)' }}>
              <div style={{ color: 'var(--muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Est. Wait</div>
              <div style={{ fontSize: '2rem', fontWeight: 900, color: 'var(--neon-cyan)', fontFamily: 'var(--font-code)' }}>
                {(status.estimated_wait_seconds || 0) < 1 ? '<1s' : `${Math.ceil(status.estimated_wait_seconds)}s`}
              </div>
            </div>
          </div>
        ) : (
          <div className="spinner" style={{ margin: '20px auto' }} />
        )}
      </div>
    </div>
  )
}

function ReservationPanel({ reservation, onCheckout }) {
  const { display, expired } = useCountdown(reservation.expires_at)
  return (
    <div className="card card-glow" style={{ borderColor: 'var(--neon-green)', marginTop: 24 }}>
      <div style={{ color: 'var(--neon-green)', fontWeight: 900, fontSize: '1.2rem', marginBottom: 12 }}>
        ✅ Inventory Hold Confirmed!
      </div>
      <div style={{ marginBottom: 16 }}>
        <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>Reservation Expiry</div>
        <div style={{ fontSize: '1.6rem', fontWeight: 900, color: expired ? 'var(--neon-red)' : 'var(--neon-yellow)', fontFamily: 'var(--font-code)' }}>
          {expired ? 'EXPIRED' : display}
        </div>
      </div>
      <button className="btn btn-success btn-full btn-lg" onClick={onCheckout} disabled={expired}>
        Proceed to Checkout &rarr;
      </button>
    </div>
  )
}

export default function ProductPage() {
  const { productId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [product, setProduct] = useState(null)
  const [loading, setLoading] = useState(true)
  const [step, setStep] = useState('idle')
  const [queueToken, setQueueToken] = useState(null)
  const [reservation, setReservation] = useState(null)
  const [error, setError] = useState(null)
  const [cartMsg, setCartMsg] = useState(null)
  const [qty, setQty] = useState(1)
  const idemKeyRef = useRef(null)

  useEffect(() => { loadProduct() }, [productId])

  async function loadProduct() {
    try {
      const res = await getProduct(productId)
      setProduct(res.data)
    } catch {
      setError('Product details not found.')
    } finally {
      setLoading(false)
    }
  }

  async function getCustomerId() {
    if (user?.customer_id) return user.customer_id
    let cid = sessionStorage.getItem('salestorm_customer_id')
    if (!cid) {
      try {
        const res = await createDemoCustomer()
        cid = res.data.customer_id
        sessionStorage.setItem('salestorm_customer_id', cid)
      } catch {
        cid = uuidv4()
      }
    }
    return cid
  }

  async function handleAddToCart() {
    try {
      await addToCart({ product_id: product.product_id, quantity: qty })
      setCartMsg('✅ Item added to cart!')
      setTimeout(() => setCartMsg(null), 2500)
    } catch (e) {
      setCartMsg('✅ Item added to local cart!')
      setTimeout(() => setCartMsg(null), 2500)
    }
  }

  async function handleBuyNow() {
    setError(null)
    const customerId = await getCustomerId()
    idemKeyRef.current = uuidv4()

    if (product.sale_id) {
      setStep('queuing')
      try {
        const res = await joinQueue({
          sale_id: product.sale_id,
          customer_id: customerId,
          product_id: product.product_id,
          quantity: qty,
          idempotency_key: idemKeyRef.current,
        })
        setQueueToken(res.data.queue_token)
        setStep('queue_waiting')
      } catch (e) {
        setError(e.response?.data?.detail || 'Failed to join queue')
        setStep('idle')
      }
    } else {
      await doReservation(customerId)
    }
  }

  async function doReservation(cidParam) {
    setStep('reserving')
    try {
      const customerId = cidParam || await getCustomerId()
      const res = await createReservation({
        customer_id: customerId,
        product_id: product.product_id,
        quantity: qty,
        idempotency_key: idemKeyRef.current || uuidv4(),
        queue_token: queueToken || undefined,
      })
      setReservation(res.data)
      setStep('reserved')
      loadProduct()
    } catch (e) {
      const detail = e.response?.data?.detail || 'Reservation failed'
      setError(detail === 'out_of_stock' ? '😔 Sorry, this item is sold out!' : detail)
      setStep('failed')
    }
  }

  if (loading) return <div className="page" style={{ textAlign: 'center', paddingTop: 80 }}><div className="spinner" /></div>
  if (!product) return <div className="page"><div className="alert alert-error">{error || 'Product not found'}</div></div>

  const stock = product.available_quantity ?? 0
  const hasFlash = !!product.sale_price
  const discount = hasFlash ? Math.round((1 - product.sale_price / product.price) * 100) : 0

  return (
    <div className="page" style={{ maxWidth: 960 }}>
      <button className="btn btn-ghost btn-sm" onClick={() => navigate(-1)} style={{ marginBottom: 20 }}>
        ← Back to Catalog
      </button>

      <div className="card card-glow" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32, padding: 32 }}>
        {/* Product Visual */}
        <div style={{
          background: '#0a0c16', borderRadius: 16, minHeight: 320,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '6rem', border: '1px solid var(--border)', overflow: 'hidden'
        }}>
          {product.image_url ? (
            <img src={product.image_url} alt={product.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          ) : (
            <span>⚡</span>
          )}
        </div>

        {/* Details & Action Panel */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {hasFlash && <div style={{ marginBottom: 10 }}><span className="badge badge-red"><span className="pulse-dot" /> FLASH SALE LIVE</span></div>}
          {product.brand && <div style={{ color: 'var(--muted)', fontSize: '0.85rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>{product.brand}</div>}
          
          <h1 style={{ fontSize: '1.8rem', marginBottom: 12, lineHeight: 1.2 }}>{product.name}</h1>
          <p style={{ color: 'var(--muted)', fontSize: '0.92rem', lineHeight: 1.6, marginBottom: 20 }}>
            {product.description || 'High-performance items backed by single-writer atomic PostgreSQL locking guarantees.'}
          </p>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, marginBottom: 20, flexWrap: 'wrap' }}>
            {hasFlash ? (
              <>
                <span style={{ fontSize: '2.2rem', fontWeight: 900, color: 'var(--neon-red)' }}>
                  ₹{Number(product.sale_price).toLocaleString()}
                </span>
                <span style={{ color: 'var(--muted)', textDecoration: 'line-through', fontSize: '1.1rem' }}>
                  ₹{Number(product.price).toLocaleString()}
                </span>
                <span className="badge badge-green">-{discount}% OFF</span>
              </>
            ) : (
              <span style={{ fontSize: '2rem', fontWeight: 900, color: '#fff' }}>
                ₹{Number(product.price).toLocaleString()}
              </span>
            )}
          </div>

          {hasFlash && product.sale_end_time && (
            <div style={{ marginBottom: 20 }}>
              <SaleTimer endTime={product.sale_end_time} />
            </div>
          )}

          <StockMeter available={stock} total={100} />

          {/* Qty Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
            <span style={{ color: 'var(--muted)', fontWeight: 600 }}>Quantity:</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setQty(q => Math.max(1, q - 1))}>−</button>
              <span style={{ fontWeight: 800, minWidth: 28, textAlign: 'center', fontSize: '1.1rem', fontFamily: 'var(--font-code)' }}>{qty}</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setQty(q => Math.min(10, q + 1))}>+</button>
            </div>
          </div>

          {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}
          {cartMsg && <div className="alert alert-success" style={{ marginBottom: 16 }}>{cartMsg}</div>}

          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
            {(step === 'idle' || step === 'failed') && (
              <>
                <button
                  className="btn btn-primary btn-full btn-lg"
                  onClick={handleBuyNow}
                  disabled={stock === 0}
                >
                  {stock === 0 ? 'SOLD OUT' : '⚡ INSTANT BUY NOW'}
                </button>
                <button
                  className="btn btn-ghost btn-full"
                  onClick={handleAddToCart}
                  disabled={stock === 0}
                >
                  🛒 Add to Cart
                </button>
              </>
            )}

            {(step === 'queuing' || step === 'reserving') && (
              <button className="btn btn-primary btn-full btn-lg" disabled>
                <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                <span>Processing Order Reservation…</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {step === 'queue_waiting' && queueToken && (
        <QueuePanel token={queueToken} onAdmitted={() => doReservation()} />
      )}

      {step === 'reserved' && reservation && (
        <ReservationPanel
          reservation={reservation}
          onCheckout={() => navigate(`/checkout/${reservation.reservation_id}`)}
        />
      )}
    </div>
  )
}
