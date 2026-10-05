import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use(config => {
  const token = localStorage.getItem('salestorm_token')
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

// Auth
export const register = (data) => api.post('/api/auth/register', data)
export const login = (data) => api.post('/api/auth/login', data)
export const logout = () => api.post('/api/auth/logout')
export const getMe = () => api.get('/api/auth/me')

// Products
export const getProducts = (params) => api.get('/api/products', { params })
export const getProduct = (id) => api.get(`/api/products/${id}`)
export const getCategories = () => api.get('/api/products/categories')

// Cart
export const getCart = () => api.get('/api/cart')
export const addToCart = (data) => api.post('/api/cart/items', data)
export const updateCartItem = (id, data) => api.put(`/api/cart/items/${id}`, data)
export const removeCartItem = (id) => api.delete(`/api/cart/items/${id}`)
export const clearCart = () => api.delete('/api/cart')

// Queue
export const joinQueue = (data) => api.post('/api/sale/join', data)
export const getQueue = (token) => api.get(`/api/sale/queue/${token}`)

// Reservations
export const createReservation = (data) => api.post('/api/reservations', data)
export const getReservation = (id) => api.get(`/api/reservations/${id}`)
export const cancelReservation = (id, customerId) =>
  api.delete(`/api/reservations/${id}?customer_id=${customerId}`)

// Checkout
export const checkout = (data) => api.post('/api/checkout', data)
export const validateCoupon = (data) => api.post('/api/checkout/validate-coupon', data)

// Payments
export const createPayment = (data) => api.post('/api/payments', data)
export const getPayment = (id) => api.get(`/api/payments/${id}`)

// Orders
export const getOrders = () => api.get('/api/orders')
export const getOrder = (id) => api.get(`/api/orders/${id}`)
export const cancelOrder = (id, data) => api.post(`/api/orders/${id}/cancel`, data || {})

// Shipments
export const getShipment = (id) => api.get(`/api/shipments/${id}`)
export const getShipmentsByOrder = (orderId) => api.get(`/api/shipments/by-order/${orderId}`)

// Notifications
export const getNotifications = () => api.get('/api/notifications')
export const getUnreadCount = () => api.get('/api/notifications/unread-count')
export const markNotificationRead = (id) => api.put(`/api/notifications/${id}/read`)
export const markAllRead = () => api.put('/api/notifications/read-all')

// Admin
const adminHeaders = { headers: { 'x-admin-key': 'admin-demo-key' } }
export const getDashboard = () => api.get('/api/admin/dashboard', adminHeaders)
export const getAdminInventory = () => api.get('/api/admin/inventory', adminHeaders)
export const getAdminOrders = (params) => api.get('/api/admin/orders', { ...adminHeaders, params })
export const updateOrderStatus = (id, status) => api.put(`/api/admin/orders/${id}/status`, { status }, adminHeaders)
export const getAdminPayments = (params) => api.get('/api/admin/payments', { ...adminHeaders, params })
export const getAdminCustomers = (params) => api.get('/api/admin/customers', { ...adminHeaders, params })
export const getAdminShipments = (params) => api.get('/api/admin/shipments', { ...adminHeaders, params })
export const updateShipment = (id, data) => api.put(`/api/admin/shipments/${id}`, data, adminHeaders)
export const getAdminReservations = (params) => api.get('/api/admin/reservations', { ...adminHeaders, params })
export const getAdminSales = () => api.get('/api/admin/sales', adminHeaders)
export const createSale = (data) => api.post('/api/admin/sales', data, adminHeaders)
export const updateSale = (id, data) => api.put(`/api/admin/sales/${id}`, data, adminHeaders)
export const getAdminCoupons = () => api.get('/api/admin/coupons', adminHeaders)
export const createCoupon = (data) => api.post('/api/admin/coupons', data, adminHeaders)
export const deactivateCoupon = (id) => api.delete(`/api/admin/coupons/${id}`, adminHeaders)
export const getAdminQueue = () => api.get('/api/admin/queue', adminHeaders)
export const getAdminAnalytics = () => api.get('/api/admin/analytics', adminHeaders)
export const simulate = (action, extra = {}) =>
  api.post('/api/admin/simulate', { action, ...extra }, adminHeaders)
export const createDemoCustomer = () => api.post('/api/admin/customers/demo', {}, adminHeaders)
export const restockInventory = (data) => api.post('/api/admin/inventory/restock', data, adminHeaders)

export default api
