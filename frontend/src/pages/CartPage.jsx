import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCart, updateCartItem, removeCartItem, clearCart, validateCoupon } from '../api/client.js'

export default function CartPage() {
  const navigate = useNavigate()
  const [cart, setCart] = useState(null)
  const [loading, setLoading] = useState(true)
  const [coupon, setCoupon] = useState('')
  const [couponResult, setCouponResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadCart()
  }, [])

  async function loadCart() {
    try {
      const res = await getCart()
      setCart(res.data)
    } catch {
      setCart({ items: [], subtotal: 0, item_count: 0 })
    } finally {
      setLoading(false)
    }
  }

  async function handleQtyChange(itemId, qty) {
    try {
      const res = await updateCartItem(itemId, { quantity: qty })
      setCart(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Update failed')
    }
  }

  async function handleRemove(itemId) {
    try {
      const res = await removeCartItem(itemId)
      setCart(res.data)
    } catch {}
  }

  async function handleClear() {
    try {
      await clearCart()
    } catch {}
    loadCart()
  }

  async function handleCoupon() {
    if (!coupon.trim() || !cart) return
    try {
      const res = await validateCoupon({ code: coupon.trim().toUpperCase(), amount: cart.subtotal || 100 })
      setCouponResult(res.data)
    } catch {
      setCouponResult({ valid: false, message: 'Invalid or expired coupon' })
    }
  }

  if (loading) return <div className="page" style={{ textAlign: 'center', paddingTop: 80 }}><div className="spinner" /></div>

  const subtotal = cart?.subtotal || 0
  const discount = couponResult?.valid ? couponResult.discount_amount : 0
  const total = Math.max(0, subtotal - discount)

  return (
    <div className="page" style={{ maxWidth: 740 }}>
      <h1 style={{ fontSize: '2.2rem', marginBottom: 24 }}>🛒 Shopping Cart</h1>

      {error && <div className="alert alert-error" style={{ marginBottom: 20 }}>{error}</div>}

      {!cart || !cart.items || cart.items.length === 0 ? (
        <div className="card card-glow" style={{ textAlign: 'center', padding: 56 }}>
          <div style={{ fontSize: '4rem', marginBottom: 16 }}>🛒</div>
          <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>Your cart is empty</h2>
          <p style={{ color: 'var(--muted)', marginBottom: 28 }}>Browse live flash sales and add items to your cart.</p>
          <button className="btn btn-primary btn-lg" onClick={() => navigate('/')}>
            ⚡ Browse Flash Sales
          </button>
        </div>
      ) : (
        <>
          <div className="card card-glow" style={{ marginBottom: 24 }}>
            {cart.items.map((item, i) => (
              <div key={item.cart_item_id} style={{
                display: 'flex', alignItems: 'center', gap: 20, padding: '16px 0',
                borderBottom: i < cart.items.length - 1 ? '1px solid var(--border)' : 'none',
              }}>
                <div style={{
                  width: 70, height: 70, background: '#0a0c16', borderRadius: 12,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem', flexShrink: 0,
                  border: '1px solid var(--border)', overflow: 'hidden'
                }}>
                  {item.product_image ? (
                    <img src={item.product_image} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  ) : (
                    <span>📦</span>
                  )}
                </div>
                
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 800, fontSize: '1.1rem' }}>{item.product_name}</div>
                  <div style={{ color: 'var(--muted)', fontSize: '0.88rem' }}>₹{Number(item.unit_price).toLocaleString()} each</div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => handleQtyChange(item.cart_item_id, Math.max(1, item.quantity - 1))}>−</button>
                  <span style={{ fontWeight: 800, minWidth: 24, textAlign: 'center', fontFamily: 'var(--font-code)' }}>{item.quantity}</span>
                  <button className="btn btn-ghost btn-sm" onClick={() => handleQtyChange(item.cart_item_id, Math.min(10, item.quantity + 1))}>+</button>
                </div>

                <div style={{ fontWeight: 900, minWidth: 90, textAlign: 'right', fontSize: '1.1rem' }}>
                  ₹{Number(item.subtotal).toLocaleString()}
                </div>

                <button className="btn btn-ghost btn-sm" onClick={() => handleRemove(item.cart_item_id)} style={{ color: 'var(--neon-red)' }}>✕</button>
              </div>
            ))}
          </div>

          {/* Coupon */}
          <div className="card" style={{ marginBottom: 24 }}>
            <label className="form-label">Have a Promo Coupon?</label>
            <div style={{ display: 'flex', gap: 12 }}>
              <input
                className="form-input"
                placeholder="Enter coupon code (e.g. STORM10)"
                value={coupon}
                onChange={e => { setCoupon(e.target.value); setCouponResult(null) }}
                style={{ flex: 1 }}
              />
              <button className="btn btn-neon-cyan" onClick={handleCoupon}>Apply</button>
            </div>
            {couponResult && (
              <div className={`alert ${couponResult.valid ? 'alert-success' : 'alert-error'}`} style={{ marginTop: 12, marginBottom: 0 }}>
                {couponResult.valid
                  ? `✅ ${couponResult.message} — Saved ₹${Number(couponResult.discount_amount).toLocaleString()}`
                  : `❌ ${couponResult.message}`
                }
              </div>
            )}
          </div>

          {/* Cart Summary */}
          <div className="card card-glow">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ color: 'var(--muted)' }}>Subtotal ({cart.item_count} items)</span>
              <span style={{ fontWeight: 700 }}>₹{Number(subtotal).toLocaleString()}</span>
            </div>
            {discount > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10, color: 'var(--neon-green)', fontWeight: 700 }}>
                <span>Coupon Discount</span>
                <span>−₹{Number(discount).toLocaleString()}</span>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 900, fontSize: '1.3rem', borderTop: '1px solid var(--border)', paddingTop: 14, marginTop: 10 }}>
              <span>Total</span>
              <span style={{ color: 'var(--neon-red)' }}>₹{Number(total).toLocaleString()}</span>
            </div>

            <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
              <button className="btn btn-ghost" onClick={handleClear} style={{ flex: 1 }}>Clear Cart</button>
              <button className="btn btn-primary btn-lg" onClick={() => navigate('/')} style={{ flex: 2 }}>
                Continue Shopping &rarr;
              </button>
            </div>

            <div style={{ marginTop: 16, background: 'rgba(10, 12, 22, 0.6)', padding: '12px 16px', borderRadius: 10, border: '1px solid var(--border)', textAlign: 'center' }}>
              <span style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>
                💡 Note: To participate in live flash sales with atomic zero-oversell guarantees, select a product and click ⚡ BUY NOW.
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
