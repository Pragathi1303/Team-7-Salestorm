import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import HomePage from './pages/HomePage.jsx'
import SalePage from './pages/SalePage.jsx'
import ProductPage from './pages/ProductPage.jsx'
import CartPage from './pages/CartPage.jsx'
import CheckoutPage from './pages/CheckoutPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import OrderDetailPage from './pages/OrderDetailPage.jsx'
import NotificationsPage from './pages/NotificationsPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import AdminPage from './pages/AdminPage.jsx'
import { getCart, getNotifications } from './api/client.js'
import './index.css'

function Navigation() {
  const location = useLocation()
  const [cartCount, setCartCount] = useState(0)
  const [unreadNotifs, setUnreadNotifs] = useState(0)
  const token = localStorage.getItem('token')
  const customerName = localStorage.getItem('customer_name') || 'Account'

  useEffect(() => {
    // Fetch cart count and notifications if user logged in
    getCart()
      .then(res => setCartCount(res.data.item_count || 0))
      .catch(() => setCartCount(0))

    getNotifications()
      .then(res => {
        const unread = (res.data || []).filter(n => !n.is_read).length
        setUnreadNotifs(unread)
      })
      .catch(() => setUnreadNotifs(0))
  }, [location.pathname])

  const isActive = (path) => location.pathname === path ? 'active' : ''

  return (
    <nav className="navbar">
      <Link to="/" className="nav-brand">
        <span style={{ fontSize: '1.6rem' }}>⚡</span> SALESTORM
      </Link>

      <div className="nav-links">
        <Link to="/" className={`nav-link ${isActive('/')}`}>
          🏠 Home
        </Link>
        <Link to="/sale" className={`nav-link ${isActive('/sale')}`} style={{ color: 'var(--neon-red)' }}>
          <span className="pulse-dot" /> Flash Sale
        </Link>
        <Link to="/cart" className={`nav-link ${isActive('/cart')}`}>
          🛒 Cart {cartCount > 0 && <span className="badge badge-cyan">{cartCount}</span>}
        </Link>
        <Link to="/orders" className={`nav-link ${isActive('/orders')}`}>
          📦 Orders
        </Link>
        <Link to="/admin" className={`nav-link ${isActive('/admin')}`}>
          📊 Admin
        </Link>
      </div>

      <div className="nav-spacer" />

      <div className="nav-actions">
        <Link to="/notifications" className="nav-link" style={{ position: 'relative' }}>
          🔔
          {unreadNotifs > 0 && (
            <span className="badge badge-red" style={{ position: 'absolute', top: 0, right: -4, padding: '2px 5px', fontSize: '0.65rem' }}>
              {unreadNotifs}
            </span>
          )}
        </Link>

        {token ? (
          <Link to="/profile" className="btn btn-ghost btn-sm">
            👤 {customerName}
          </Link>
        ) : (
          <div style={{ display: 'flex', gap: 8 }}>
            <Link to="/login" className="btn btn-ghost btn-sm">Sign In</Link>
            <Link to="/register" className="btn btn-primary btn-sm">Register</Link>
          </div>
        )}
      </div>
    </nav>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Navigation />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/sale" element={<SalePage />} />
        <Route path="/products" element={<HomePage />} />
        <Route path="/products/:productId" element={<ProductPage />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/checkout/:reservationId" element={<CheckoutPage />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/orders/:orderId" element={<OrderDetailPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
