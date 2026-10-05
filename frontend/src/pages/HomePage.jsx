import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { getProducts, getCategories } from '../api/client.js'
import { useCountdown } from '../hooks/useCountdown.js'

function FlashBadge() {
  return (
    <span className="badge badge-red">
      <span className="pulse-dot" /> FLASH SALE
    </span>
  )
}

function SaleTimer({ endTime }) {
  const { display, expired } = useCountdown(endTime)
  if (!endTime || expired) return null
  return (
    <div style={{ color: 'var(--neon-yellow)', fontWeight: 700, fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: 6 }}>
      ⏱ Ends in: <span style={{ fontFamily: 'var(--font-code)' }}>{display}</span>
    </div>
  )
}

function StockMeter({ available, initial = 100 }) {
  const pct = Math.max(0, Math.min(100, Math.round((available / initial) * 100)))
  return (
    <div style={{ margin: '8px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--muted)', marginBottom: 4 }}>
        <span>Stock Available</span>
        <span style={{ color: available > 10 ? 'var(--neon-green)' : 'var(--neon-red)', fontWeight: 700 }}>
          {available > 0 ? `${available} left` : 'SOLD OUT'}
        </span>
      </div>
      <div className="progress-bar-bg">
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function ProductCard({ product, onClick }) {
  const hasFlash = !!product.sale_price
  const discount = hasFlash
    ? Math.round((1 - product.sale_price / product.price) * 100)
    : 0
  const stock = product.available_quantity ?? 0

  return (
    <div className="product-card" onClick={onClick}>
      <div className="product-img-wrap">
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} />
        ) : (
          <div style={{ fontSize: '3.5rem', opacity: 0.8 }}>⚡</div>
        )}
        {hasFlash && (
          <div style={{ position: 'absolute', top: 12, left: 12 }}>
            <FlashBadge />
          </div>
        )}
        {discount > 0 && (
          <div style={{ position: 'absolute', top: 12, right: 12 }}>
            <span className="badge badge-green">-{discount}%</span>
          </div>
        )}
        {stock === 0 && (
          <div style={{
            position: 'absolute', inset: 0, background: 'rgba(5, 6, 12, 0.85)',
            backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span className="badge badge-red" style={{ fontSize: '1rem', padding: '8px 16px' }}>SOLD OUT</span>
          </div>
        )}
      </div>

      <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', flex: 1 }}>
        {product.brand && (
          <div style={{ color: 'var(--muted)', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>
            {product.brand}
          </div>
        )}
        <h3 style={{ fontSize: '1.1rem', marginBottom: 8, lineHeight: 1.3 }}>
          {product.name}
        </h3>
        
        <p style={{ color: 'var(--muted)', fontSize: '0.88rem', marginBottom: 16, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {product.description || 'High-performance flash sale item with atomic inventory lock guarantees.'}
        </p>

        <div style={{ marginTop: 'auto' }}>
          <StockMeter available={stock} initial={100} />

          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 12, marginBottom: 12 }}>
            {hasFlash ? (
              <>
                <span style={{ fontWeight: 900, color: 'var(--neon-red)', fontSize: '1.3rem' }}>
                  ₹{Number(product.sale_price).toLocaleString()}
                </span>
                <span style={{ color: 'var(--muted)', textDecoration: 'line-through', fontSize: '0.9rem' }}>
                  ₹{Number(product.price).toLocaleString()}
                </span>
              </>
            ) : (
              <span style={{ fontWeight: 800, fontSize: '1.2rem', color: '#fff' }}>
                ₹{Number(product.price).toLocaleString()}
              </span>
            )}
          </div>

          {hasFlash && product.sale_end_time && (
            <div style={{ marginBottom: 14 }}>
              <SaleTimer endTime={product.sale_end_time} />
            </div>
          )}

          <button
            className={`btn ${hasFlash ? 'btn-primary' : 'btn-ghost'} btn-full`}
            onClick={e => { e.stopPropagation(); onClick() }}
            disabled={stock === 0}
          >
            {stock === 0 ? 'Out of Stock' : hasFlash ? '⚡ Join Flash Sale' : 'View Details'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    Promise.all([getProducts(), getCategories()])
      .then(([pRes, cRes]) => {
        setProducts(pRes.data || [])
        setCategories(cRes.data || [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const flashProducts = products.filter(p => p.sale_price)
  const filtered = products.filter(p => {
    const matchCat = !selectedCategory || p.category_id === selectedCategory
    const matchSearch = !search || p.name.toLowerCase().includes(search.toLowerCase())
    return matchCat && matchSearch
  })

  return (
    <div className="page-wide">
      {/* Hero Banner */}
      <div className="card card-glow" style={{
        background: 'linear-gradient(135deg, rgba(26, 16, 60, 0.9) 0%, rgba(42, 10, 62, 0.9) 50%, rgba(9, 10, 18, 0.9) 100%)',
        borderRadius: 24, padding: '48px 36px', marginBottom: 40,
        boxShadow: '0 20px 50px rgba(255, 46, 99, 0.15)',
        border: '1px solid rgba(255, 46, 99, 0.3)',
      }}>
        <div style={{ maxWidth: 840, margin: '0 auto', textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 16px', borderRadius: 30, background: 'rgba(255, 46, 99, 0.15)', border: '1px solid rgba(255, 46, 99, 0.4)', marginBottom: 20 }}>
            <span className="pulse-dot" />
            <span style={{ color: 'var(--neon-red)', fontWeight: 800, fontSize: '0.85rem', letterSpacing: 1 }}>
              PRODUCTION-GRADE FLASH SALE ENGINE
            </span>
          </div>

          <h1 style={{ fontSize: '3rem', fontWeight: 900, marginBottom: 16, lineHeight: 1.15 }}>
            High-Scale Concurrency. <br />
            <span className="text-neon-red">Zero Overselling Guarantee.</span>
          </h1>

          <p style={{ color: 'var(--muted)', fontSize: '1.15rem', marginBottom: 32, lineHeight: 1.6 }}>
            Powered by an Adaptive Virtual Queue, Product-Partitioned Serializer, and Single-Writer Inventory Allocator with row-level PostgreSQL locks.
          </p>

          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 40 }}>
            <Link to="/sale" className="btn btn-primary btn-lg">
              ⚡ Launch Flash Sale Demo
            </Link>
            <Link to="/admin" className="btn btn-neon-cyan btn-lg">
              📊 Live System Dashboard
            </Link>
          </div>

          {/* Key Architecture Badges */}
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16,
            padding: '20px', background: 'rgba(10, 12, 22, 0.6)', borderRadius: 16, border: '1px solid var(--border)'
          }}>
            <div>
              <div style={{ color: 'var(--neon-cyan)', fontWeight: 900, fontSize: '1.4rem' }}>10,000+</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>Concurrent Users</div>
            </div>
            <div>
              <div style={{ color: 'var(--neon-green)', fontWeight: 900, fontSize: '1.4rem' }}>0</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>Oversold Units</div>
            </div>
            <div>
              <div style={{ color: 'var(--neon-yellow)', fontWeight: 900, fontSize: '1.4rem' }}>&lt; 200ms</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>Queue Admission Latency</div>
            </div>
            <div>
              <div style={{ color: 'var(--neon-purple)', fontWeight: 900, fontSize: '1.4rem' }}>30s</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>Reservation Auto-Expiry</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div style={{ display: 'flex', gap: 16, justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', marginBottom: 32 }}>
        <div style={{ flex: 1, minWidth: 280, maxWidth: 500 }}>
          <input
            className="form-input"
            placeholder="🔍 Search live products by name or SKU…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {categories.length > 0 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              className={`btn btn-sm ${!selectedCategory ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setSelectedCategory(null)}
            >All Items</button>
            {categories.map(c => (
              <button
                key={c.category_id}
                className={`btn btn-sm ${selectedCategory === c.category_id ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setSelectedCategory(c.category_id)}
              >{c.category_name}</button>
            ))}
          </div>
        )}
      </div>

      {/* Live Flash Sales Section */}
      {flashProducts.length > 0 && !search && !selectedCategory && (
        <div style={{ marginBottom: 44 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <h2 style={{ fontSize: '1.8rem' }}>⚡ Active Flash Sales</h2>
              <span className="badge badge-red">LIVE</span>
            </div>
            <Link to="/sale" style={{ color: 'var(--neon-cyan)', fontWeight: 700, fontSize: '0.92rem' }}>
              View Queue Status &rarr;
            </Link>
          </div>

          <div className="product-grid">
            {flashProducts.map(p => (
              <ProductCard
                key={p.product_id}
                product={p}
                onClick={() => navigate(`/sale?product_id=${p.product_id}`)}
              />
            ))}
          </div>
        </div>
      )}

      {/* All Products Grid */}
      <div>
        <h2 style={{ fontSize: '1.8rem', marginBottom: 20 }}>
          {search || selectedCategory ? 'Search Results' : 'Catalog Products'}
          <span style={{ color: 'var(--muted)', fontSize: '1rem', fontWeight: 500, marginLeft: 10 }}>
            ({filtered.length} items)
          </span>
        </h2>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><div className="spinner" /></div>
        ) : filtered.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: 60 }}>
            <div style={{ fontSize: '2.5rem', marginBottom: 12 }}>🔍</div>
            <h3 style={{ marginBottom: 8 }}>No matching products found</h3>
            <p style={{ color: 'var(--muted)' }}>Try adjusting your search criteria or filter tags.</p>
          </div>
        ) : (
          <div className="product-grid">
            {filtered.map(p => (
              <ProductCard
                key={p.product_id}
                product={p}
                onClick={() => navigate(`/products/${p.product_id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
