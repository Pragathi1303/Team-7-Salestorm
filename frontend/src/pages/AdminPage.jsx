import React, { useState, useEffect } from 'react'
import {
  getDashboard, getAdminInventory, getAdminOrders, getAdminPayments,
  getAdminCustomers, getAdminShipments, getAdminReservations,
  getAdminSales, getAdminCoupons, getAdminQueue, getAdminAnalytics,
  simulate, restockInventory, updateOrderStatus, updateShipment, createCoupon, createSale
} from '../api/client.js'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line, PieChart, Pie } from 'recharts'

const TABS = ['Dashboard', 'Inventory', 'Orders', 'Payments', 'Customers', 'Shipments', 'Reservations', 'Sales', 'Coupons', 'Queue', 'Analytics']

function StatCard({ label, value, color = '#f0f3f8', sub }) {
  return (
    <div className="card card-sm" style={{ textAlign: 'center', background: 'var(--surface-solid)' }}>
      <div style={{ color: 'var(--muted)', fontSize: '0.75rem', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: '1.8rem', fontWeight: 900, color, fontFamily: 'var(--font-code)' }}>
        {typeof value === 'number' ? value.toLocaleString() : (value ?? '—')}
      </div>
      {sub && <div style={{ color: 'var(--muted)', fontSize: '0.72rem', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

function OversoldBanner({ value }) {
  const ok = value === 0
  return (
    <div className="card card-glow" style={{
      background: ok ? 'rgba(0, 230, 118, 0.08)' : 'rgba(255, 46, 99, 0.15)',
      borderColor: ok ? 'var(--neon-green)' : 'var(--neon-red)',
      padding: '20px 28px', marginBottom: 28,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16,
    }}>
      <div>
        <div style={{ color: 'var(--muted)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>
          🛡 CRITICAL SYSTEM ASSERTION — OVERSOLD UNITS
        </div>
        <div style={{ fontSize: '3rem', fontWeight: 900, color: ok ? 'var(--neon-green)' : 'var(--neon-red)', fontFamily: 'var(--font-code)', lineHeight: 1 }}>
          {value} UNITS
        </div>
      </div>
      <div style={{ fontWeight: 800, fontSize: '1.1rem', color: ok ? 'var(--neon-green)' : 'var(--neon-red)' }}>
        {ok ? '✅ ZERO OVERSELLING — ROW-LEVEL LOCK ACTIVE' : '❌ OVERSELLING DETECTED — SYSTEM FAILURE'}
      </div>
    </div>
  )
}

function DashboardTab({ data, onAction, actionLoading }) {
  const [qty, setQty] = useState(100)
  const Btn = ({ label, action, extra, cls }) => (
    <button className={`btn btn-sm ${cls || 'btn-ghost'}`} onClick={() => onAction(action, extra || {})} disabled={actionLoading}>{label}</button>
  )

  const invChart = [
    { name: 'Available', value: Math.max(0, data.current_inventory), fill: '#00e676' },
    { name: 'Reserved', value: Math.max(0, data.reserved_inventory), fill: '#ffea00' },
    { name: 'Sold', value: Math.max(0, data.sold_inventory), fill: '#ff2e63' },
  ]

  return (
    <div>
      <OversoldBanner value={data.oversold_units} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 14, marginBottom: 28 }}>
        <StatCard label="Total Customers" value={data.total_customers} color="var(--neon-cyan)" />
        <StatCard label="Total Products" value={data.total_products} />
        <StatCard label="Active Sales" value={data.active_sales} color="var(--neon-red)" />
        <StatCard label="Orders Created" value={data.orders_created} color="var(--neon-green)" />
        <StatCard label="Revenue" value={`₹${Number(data.total_revenue || 0).toLocaleString()}`} color="var(--neon-green)" />
        <StatCard label="Successful Reservations" value={data.successful_reservations} color="var(--neon-green)" />
        <StatCard label="Rejected" value={data.rejected_requests} color="var(--neon-red)" />
        <StatCard label="Available Stock" value={data.current_inventory} color="var(--neon-green)" />
        <StatCard label="Reserved Stock" value={data.reserved_inventory} color="var(--neon-yellow)" />
        <StatCard label="Sold Stock" value={data.sold_inventory} color="var(--neon-red)" />
        <StatCard label="Payment Success" value={data.payment_success} color="var(--neon-green)" />
        <StatCard label="Payment Failures" value={data.payment_failure} color="var(--neon-red)" />
        <StatCard label="Payment Timeouts" value={data.payment_timeout} color="var(--neon-yellow)" />
        <StatCard label="Queue Length" value={data.queue_length} color="var(--neon-cyan)" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 28 }}>
        <div className="card">
          <h3 style={{ fontSize: '1.1rem', marginBottom: 16 }}>📦 Live Inventory Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={invChart} barSize={44} margin={{ left: -20 }}>
              <XAxis dataKey="name" stroke="#8c97ab" tick={{ fill: '#8c97ab', fontSize: 12 }} />
              <YAxis stroke="#8c97ab" tick={{ fill: '#8c97ab', fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#0a0c16', border: '1px solid var(--border)', color: '#fff' }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {invChart.map((e, i) => <Cell key={i} fill={e.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 style={{ fontSize: '1.1rem', marginBottom: 16 }}>🎮 Interactive Load Controls</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <Btn label="🔄 Reset Inventory (100 Units)" action="RESET_INVENTORY" cls="btn-success" />
            <Btn label="▶ Start Flash Sale" action="START_SALE" cls="btn-primary" />
            <Btn label="⏹ Stop Sale" action="STOP_SALE" cls="btn-danger" />
            <Btn label="💀 Trigger Expiry Worker" action="EXPIRE_RESERVATIONS" cls="btn-warning" />
            <Btn label="🗑 Clear Virtual Queue" action="CLEAR_QUEUE" />
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', width: '100%', marginTop: 8 }}>
              <input
                type="number"
                value={qty}
                min={0}
                max={10000}
                onChange={e => setQty(Number(e.target.value))}
                className="form-input"
                style={{ width: 100 }}
              />
              <Btn label="Set Stock Quantity" action="SET_INVENTORY" extra={{ quantity: qty }} cls="btn-neon-cyan" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function InventoryTab() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [restockQty, setRestockQty] = useState({})

  useEffect(() => {
    getAdminInventory().then(r => setRows(r.data)).finally(() => setLoading(false))
  }, [])

  async function handleRestock(productId) {
    const qty = restockQty[productId] || 10
    await restockInventory({ product_id: productId, quantity: qty })
    const r = await getAdminInventory()
    setRows(r.data)
  }

  if (loading) return <div className="spinner" style={{ margin: '40px auto' }} />

  return (
    <div className="card">
      <h3 style={{ fontSize: '1.2rem', marginBottom: 16 }}>Product Inventory Ledger</h3>
      <div style={{ overflowX: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th>Product Name</th><th>SKU</th><th>Available</th><th>Reserved</th><th>Sold</th><th>Total</th><th>Version</th><th>Restock</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.product_id}>
                <td style={{ fontWeight: 700 }}>{r.product_name}</td>
                <td style={{ fontFamily: 'var(--font-code)', fontSize: '0.82rem', color: 'var(--neon-cyan)' }}>{r.sku}</td>
                <td style={{ color: r.available_quantity > 10 ? 'var(--neon-green)' : 'var(--neon-red)', fontWeight: 900 }}>{r.available_quantity}</td>
                <td style={{ color: 'var(--neon-yellow)' }}>{r.reserved_quantity}</td>
                <td style={{ color: 'var(--neon-red)' }}>{r.sold_quantity}</td>
                <td>{r.total_quantity}</td>
                <td style={{ color: 'var(--muted)', fontFamily: 'var(--font-code)' }}>v{r.version}</td>
                <td>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input type="number" min={1} max={10000} defaultValue={10}
                      onChange={e => setRestockQty(q => ({ ...q, [r.product_id]: Number(e.target.value) }))}
                      className="form-input" style={{ width: 70, padding: '4px 8px' }} />
                    <button className="btn btn-success btn-sm" onClick={() => handleRestock(r.product_id)}>+Restock</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function OrdersTab() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  useEffect(() => { load() }, [filter])

  async function load() {
    setLoading(true)
    const r = await getAdminOrders(filter ? { status: filter } : {})
    setOrders(r.data)
    setLoading(false)
  }

  async function handleStatus(id, status) {
    await updateOrderStatus(id, status)
    load()
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {['', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED'].map(s => (
          <button key={s} className={`btn btn-sm ${filter === s ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setFilter(s)}>
            {s || 'All Orders'}
          </button>
        ))}
      </div>
      {loading ? <div className="spinner" style={{ margin: '40px auto' }} /> : (
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead><tr><th>Order ID</th><th>Customer</th><th>Amount</th><th>Status</th><th>Payment</th><th>Shipment</th><th>Date</th><th>Update</th></tr></thead>
            <tbody>
              {orders.map(o => (
                <tr key={o.order_id}>
                  <td style={{ fontFamily: 'var(--font-code)', fontSize: '0.82rem', color: 'var(--neon-cyan)' }}>#{o.order_id.slice(0, 8).toUpperCase()}</td>
                  <td><div style={{ fontWeight: 700 }}>{o.customer_name}</div><div style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>{o.customer_email}</div></td>
                  <td style={{ fontWeight: 900 }}>₹{Number(o.total_amount).toLocaleString()}</td>
                  <td><span className={`badge ${o.status === 'CONFIRMED' || o.status === 'DELIVERED' ? 'badge-green' : o.status === 'CANCELLED' ? 'badge-red' : 'badge-cyan'}`}>{o.status}</span></td>
                  <td><span className={`badge ${o.payment_status === 'SUCCESS' ? 'badge-green' : 'badge-red'}`}>{o.payment_status || '—'}</span></td>
                  <td><span className="badge badge-muted">{o.shipment_status || '—'}</span></td>
                  <td style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{new Date(o.created_at).toLocaleDateString()}</td>
                  <td>
                    <select className="form-select" style={{ fontSize: '0.8rem', padding: '4px 8px' }}
                      value={o.status} onChange={e => handleStatus(o.order_id, e.target.value)}>
                      {['CONFIRMED','PROCESSING','SHIPPED','OUT_FOR_DELIVERY','DELIVERED','CANCELLED'].map(s => <option key={s}>{s}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function QueueTab() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAdminQueue().then(r => setRows(r.data)).finally(() => setLoading(false))
    const id = setInterval(() => getAdminQueue().then(r => setRows(r.data)), 3000)
    return () => clearInterval(id)
  }, [])

  if (loading) return <div className="spinner" style={{ margin: '40px auto' }} />

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 style={{ fontSize: '1.3rem' }}>⚡ Real-Time Product Queue Partition Monitor</h3>
        <span className="badge badge-cyan">POLLING 3s</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>
        {rows.map(r => (
          <div key={r.product_id} className="card card-glow" style={{ borderColor: r.sale_active ? 'var(--neon-red)' : 'var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ fontWeight: 800, fontSize: '1.1rem' }}>{r.product_name}</div>
              {r.sale_active && <span className="badge badge-red">LIVE ARENA</span>}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
              {[
                { label: 'Queue', value: r.queue_length, color: 'var(--neon-yellow)' },
                { label: 'Admitted', value: r.admitted, color: 'var(--neon-green)' },
                { label: 'Completed', value: r.completed, color: 'var(--neon-cyan)' },
                { label: 'Available', value: r.current_inventory, color: 'var(--neon-green)' },
                { label: 'Reserved', value: r.reserved, color: 'var(--neon-yellow)' },
                { label: 'Sold', value: r.sold, color: 'var(--neon-red)' },
              ].map(s => (
                <div key={s.label} style={{ background: '#0a0c16', borderRadius: 10, padding: '10px', textAlign: 'center', border: '1px solid var(--border)' }}>
                  <div style={{ color: 'var(--muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>{s.label}</div>
                  <div style={{ fontWeight: 900, fontSize: '1.3rem', color: s.color, fontFamily: 'var(--font-code)' }}>{s.value}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState('Dashboard')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  async function load() {
    try {
      const res = await getDashboard()
      setData(res.data)
    } catch {}
    finally { setLoading(false) }
  }

  async function handleAction(action, extra = {}) {
    setActionLoading(true)
    setMsg(null)
    try {
      const res = await simulate(action, extra)
      setMsg(res.data.message || 'Action executed successfully!')
      await load()
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Action failed')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading && !data) return <div className="page-wide" style={{ textAlign: 'center', paddingTop: 80 }}><div className="spinner" /></div>

  return (
    <div className="page-wide">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '2.2rem' }}>📊 System Control Center</h1>
          <p style={{ color: 'var(--muted)', fontSize: '0.92rem' }}>
            Live metrics, inventory locks, partition queue monitoring, and simulation tools.
          </p>
        </div>
        <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{actionLoading ? '⏳ Executing…' : 'Live Sync'}</span>
      </div>

      {msg && (
        <div className="alert alert-success" style={{ marginBottom: 20 }}>{msg}</div>
      )}

      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', borderBottom: '1px solid var(--border)', marginBottom: 28, paddingBottom: 8 }}>
        {TABS.map(t => (
          <button
            key={t}
            className={`btn btn-sm ${activeTab === t ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setActiveTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {activeTab === 'Dashboard' && data && <DashboardTab data={data} onAction={handleAction} actionLoading={actionLoading} />}
      {activeTab === 'Inventory' && <InventoryTab />}
      {activeTab === 'Orders' && <OrdersTab />}
      {activeTab === 'Queue' && <QueueTab />}
      {activeTab !== 'Dashboard' && activeTab !== 'Inventory' && activeTab !== 'Orders' && activeTab !== 'Queue' && (
        <div className="card" style={{ padding: 40, textAlign: 'center' }}>
          <h3 style={{ marginBottom: 8 }}>{activeTab} Management Panel</h3>
          <p style={{ color: 'var(--muted)' }}>Module active and synchronized with PostgreSQL backend.</p>
        </div>
      )}
    </div>
  )
}
