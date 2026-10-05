import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { v4 as uuidv4 } from 'uuid'
import {
  getProducts, joinQueue, getQueue, createReservation, createDemoCustomer, getProduct
} from '../api/client.js'
import { useCountdown } from '../hooks/useCountdown.js'

function SaleCountdown({ endTime }) {
  const { display, expired } = useCountdown(endTime)
  if (!endTime) return null
  if (expired) return <span style={{ color: 'var(--muted)' }}>Flash Sale Concluded</span>
  return (
    <div style={{ color: 'var(--neon-yellow)', fontWeight: 800, fontSize: '1.2rem', fontFamily: 'var(--font-code)' }}>
      ⏱ {display}
    </div>
  )
}

function StockMeter({ available, total = 100 }) {
  const safeAvail = Math.max(0, available || 0)
  const pct = Math.max(0, Math.min(100, (safeAvail / total) * 100))
  return (
    <div style={{ background: 'rgba(10, 12, 22, 0.8)', padding: '16px', borderRadius: 12, border: '1px solid var(--border)', marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.9rem' }}>
        <span style={{ color: 'var(--muted)', fontWeight: 600 }}>Live System Inventory</span>
        <span style={{ fontWeight: 800, color: safeAvail > 15 ? 'var(--neon-green)' : 'var(--neon-red)' }}>
          {safeAvail} / {total} units left
        </span>
      </div>
      <div className="progress-bar-bg" style={{ height: 12 }}>
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <span className="pulse-dot" />
          <h3 style={{ fontSize: '1.4rem' }}>Adaptive Virtual Queue Active</h3>
        </div>

        <p style={{ color: 'var(--muted)', fontSize: '0.92rem', marginBottom: 24 }}>
          Absorbing incoming user traffic spike before sending request to single-writer inventory allocator.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
          <div style={{ background: '#0a0c16', padding: '16px', borderRadius: 12, border: '1px solid var(--border)', textAlign: 'center' }}>
            <div style={{ color: 'var(--muted)', fontSize: '0.8rem', textTransform: 'uppercase' }}>Queue Position</div>
            <div style={{ fontSize: '2.4rem', fontWeight: 900, color: 'var(--neon-yellow)', fontFamily: 'var(--font-code)' }}>
              {status?.position > 0 ? `#${status.position}` : 'ADMITTED'}
            </div>
          </div>
          <div style={{ background: '#0a0c16', padding: '16px', borderRadius: 12, border: '1px solid var(--border)', textAlign: 'center' }}>
            <div style={{ color: 'var(--muted)', fontSize: '0.8rem', textTransform: 'uppercase' }}>Est. Admission Wait</div>
            <div style={{ fontSize: '2.4rem', fontWeight: 900, color: 'var(--neon-cyan)', fontFamily: 'var(--font-code)' }}>
              {(status?.estimated_wait_seconds || 0) < 1 ? '<1s' : `${Math.ceil(status.estimated_wait_seconds)}s`}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="badge badge-cyan">STATUS: {status?.status || 'POLLING'}</span>
          <span style={{ fontFamily: 'var(--font-code)', fontSize: '0.8rem', color: 'var(--muted)' }}>
            TOKEN: {token}
          </span>
        </div>
      </div>
    </div>
  )
}

function ReservationPanel({ reservation, onCheckout }) {
  const { display, expired } = useCountdown(reservation.expires_at)
  return (
    <div className="card" style={{ borderColor: 'var(--neon-green)', marginTop: 24, boxShadow: '0 0 30px rgba(0, 230, 118, 0.2)' }}>
      <div style={{ color: 'var(--neon-green)', fontWeight: 900, fontSize: '1.3rem', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        <span>✅</span> Inventory Allocated & Held!
      </div>
      <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginBottom: 16 }}>
        Your item has been reserved in PostgreSQL via single-writer row-level lock.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        <div>
          <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>Reservation ID</div>
          <div style={{ fontFamily: 'var(--font-code)', fontSize: '0.85rem', color: 'var(--neon-cyan)', wordBreak: 'break-all' }}>
            {reservation.reservation_id.slice(0, 16)}…
          </div>
        </div>
        <div>
          <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>Hold Expiry Countdown</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 900, color: expired ? 'var(--neon-red)' : 'var(--neon-yellow)', fontFamily: 'var(--font-code)' }}>
            {expired ? 'EXPIRED' : display}
          </div>
        </div>
      </div>

      <button
        className="btn btn-success btn-full btn-lg"
        onClick={onCheckout}
        disabled={expired}
      >
        Proceed to Checkout ({reservation.quantity} item) &rarr;
      </button>
    </div>
  )
}

export default function SalePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const targetProductId = searchParams.get('product_id')

  const [product, setProduct] = useState(null)
  const [loading, setLoading] = useState(true)
  const [step, setStep] = useState('idle')
  const [queueToken, setQueueToken] = useState(null)
  const [reservation, setReservation] = useState(null)
  const [error, setError] = useState(null)
  const [customerId, setCustomerId] = useState(null)
  const [logs, setLogs] = useState([])
  const idemKeyRef = useRef(null)

  useEffect(() => {
    loadProduct()
    ensureCustomer()
  }, [targetProductId])

  function addLog(msg) {
    const time = new Date().toLocaleTimeString()
    setLogs(prev => [`[${time}] ${msg}`, ...prev.slice(0, 6)])
  }

  async function loadProduct() {
    try {
      if (targetProductId) {
        const res = await getProduct(targetProductId)
        setProduct(res.data)
      } else {
        const res = await getProducts()
        const flash = (res.data || []).find(p => p.sale_price) || res.data?.[0]
        if (flash) setProduct(flash)
        else setError('No active products available for flash sale.')
      }
    } catch {
      setError('Could not load flash sale data. Ensure backend is running.')
    } finally {
      setLoading(false)
    }
  }

  async function ensureCustomer() {
    let cid = sessionStorage.getItem('salestorm_customer_id')
    if (!cid) {
      try {
        const res = await createDemoCustomer()
        cid = res.data.customer_id
        sessionStorage.setItem('salestorm_customer_id', cid)
      } catch (e) {
        console.error('Could not create demo customer', e)
      }
    }
    setCustomerId(cid)
  }

  async function handleBuyNow() {
    if (!product || !customerId) return
    setError(null)
    idemKeyRef.current = uuidv4()
    addLog(`BUY NOW clicked for ${product.name}. Generating idempotency_key=${idemKeyRef.current.slice(0, 8)}…`)

    if (product.sale_id) {
      setStep('queuing')
      addLog(`Submitting request to Adaptive Virtual Queue (sale_id=${product.sale_id.slice(0, 8)})`)
      try {
        const res = await joinQueue({
          sale_id: product.sale_id,
          customer_id: customerId,
          product_id: product.product_id,
          quantity: 1,
          idempotency_key: idemKeyRef.current,
        })
        setQueueToken(res.data.queue_token)
        addLog(`Admitted to queue. Token: ${res.data.queue_token}`)
        setStep('queue_waiting')
      } catch (e) {
        setError(e.response?.data?.detail || 'Failed to join virtual queue')
        setStep('idle')
      }
    } else {
      await doReservation()
    }
  }

  async function doReservation() {
    setStep('reserving')
    addLog(`Calling Inventory Allocator with row-level lock SELECT FOR UPDATE…`)
    try {
      const res = await createReservation({
        customer_id: customerId,
        product_id: product.product_id,
        quantity: 1,
        idempotency_key: idemKeyRef.current || uuidv4(),
        queue_token: queueToken || undefined,
      })
      setReservation(res.data)
      setStep('reserved')
      addLog(`✅ Inventory locked successfully! reservation_id=${res.data.reservation_id.slice(0, 8)}`)
      loadProduct()
    } catch (e) {
      const detail = e.response?.data?.detail || 'Reservation failed'
      addLog(`❌ Allocation rejected: ${detail}`)
      if (detail === 'out_of_stock' || detail.includes('out_of_stock')) {
        setError('😔 Sorry, this item sold out! Zero overselling enforced.')
      } else {
        setError(detail)
      }
      setStep('failed')
    }
  }

  if (loading) {
    return (
      <div className="page" style={{ textAlign: 'center', paddingTop: 80 }}>
        <div className="spinner" style={{ marginBottom: 16 }} />
        <div style={{ color: 'var(--muted)' }}>Connecting to Flash Sale System…</div>
      </div>
    )
  }

  return (
    <div className="page">
      <div style={{ maxWidth: 680, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h1 style={{ fontSize: '2.2rem' }}>⚡ Flash Sale Arena</h1>
              <span className="badge badge-red">LIVE ARENA</span>
            </div>
            <p style={{ color: 'var(--muted)', fontSize: '0.92rem' }}>
              Real-time high concurrency simulation room with atomic inventory lock guarantees.
            </p>
          </div>
        </div>

        {error && (
          <div className="card" style={{ borderColor: 'var(--neon-red)', marginBottom: 24, background: 'rgba(255, 46, 99, 0.1)' }}>
            <div style={{ color: 'var(--neon-red)', fontWeight: 700, fontSize: '1rem' }}>⚠️ {error}</div>
          </div>
        )}

        {product && (
          <div className="card card-glow" style={{ padding: 32 }}>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 24 }}>
              <div style={{
                width: 140, height: 140, borderRadius: 16, background: '#0a0c16', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '4rem'
              }}>
                {product.image_url ? <img src={product.image_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 16 }} /> : '⚡'}
              </div>

              <div style={{ flex: 1, minWidth: 240 }}>
                <span className="badge badge-purple" style={{ marginBottom: 8 }}>{product.brand || 'PREMIUM'}</span>
                <h2 style={{ fontSize: '1.6rem', marginBottom: 8 }}>{product.name}</h2>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 12 }}>
                  <span style={{ fontSize: '2.2rem', fontWeight: 900, color: 'var(--neon-red)' }}>
                    ₹{Number(product.sale_price || product.price).toLocaleString()}
                  </span>
                  {product.sale_price && (
                    <span style={{ color: 'var(--muted)', textDecoration: 'line-through', fontSize: '1.1rem' }}>
                      ₹{Number(product.price).toLocaleString()}
                    </span>
                  )}
                </div>
                {product.sale_end_time && <SaleCountdown endTime={product.sale_end_time} />}
              </div>
            </div>

            <StockMeter available={product.available_quantity ?? 0} total={100} />

            {(step === 'idle' || step === 'failed') && (
              <button
                className="btn btn-primary btn-full btn-lg"
                onClick={handleBuyNow}
                disabled={!customerId || (product.available_quantity ?? 0) === 0}
              >
                {(product.available_quantity ?? 0) === 0 ? 'SOLD OUT — 0 UNITS REMAINING' : '⚡ CLICK BUY NOW'}
              </button>
            )}

            {(step === 'queuing' || step === 'reserving') && (
              <button className="btn btn-primary btn-full btn-lg" disabled>
                <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                <span>Processing Order through Virtual Queue…</span>
              </button>
            )}
          </div>
        )}

        {step === 'queue_waiting' && queueToken && (
          <QueuePanel token={queueToken} onAdmitted={doReservation} />
        )}

        {step === 'reserved' && reservation && (
          <ReservationPanel
            reservation={reservation}
            onCheckout={() => navigate(`/checkout/${reservation.reservation_id}`)}
          />
        )}

        {/* System Logs Console */}
        {logs.length > 0 && (
          <div style={{ marginTop: 32 }}>
            <h4 style={{ color: 'var(--muted)', fontSize: '0.85rem', textTransform: 'uppercase', marginBottom: 10 }}>
              💻 Architecture Execution Trace
            </h4>
            <div className="code-block">
              {logs.map((l, i) => (
                <div key={i} style={{ marginBottom: 4 }}>{l}</div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
