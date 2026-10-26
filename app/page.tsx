'use client'

import dynamic from 'next/dynamic'
import React, { useState } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  Bell,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Search,
  Settings,
  Shield,
  ShieldAlert,
  SlidersHorizontal,
  Target,
  X,
  Zap,
} from 'lucide-react'
import { ConnectionProvider, useConnection } from '../lib/context/ConnectionContext'
import { API_BASE_URL } from '../lib/api'
import { Dashboard } from '../components/dashboard/Dashboard'
import { EventsPage } from '../components/events/EventsPage'
import { AlertsPage } from '../components/alerts/AlertsPage'
import { IncidentsPage } from '../components/incidents/IncidentsPage'
import { ThreatsPage } from '../components/threats/ThreatsPage'
import { RulesPage } from '../components/rules/RulesPage'
import { AnalyticsPage } from '../components/analytics/AnalyticsPage'
import { SettingsPage } from '../components/settings/SettingsPage'

const nav = [
  { label: 'Overview', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Threats', href: '/threats', icon: ShieldAlert, badge: 'Live' },
  { label: 'Events', href: '/events', icon: Activity },
  { label: 'Alerts', href: '/alerts', icon: Bell, badge: 'SOC' },
  { label: 'Incidents', href: '/incidents', icon: Target },
  { label: 'Analytics', href: '/analytics', icon: SlidersHorizontal },
]

const manage = [
  { label: 'Detection rules', href: '/rules', icon: Zap },
  { label: 'Settings', href: '/settings', icon: Settings },
]

function NavItem({
  item,
  active,
  collapsed,
}: {
  item: { label: string; href: string; icon: React.ComponentType<{ size?: number }>; badge?: string }
  active: boolean
  collapsed: boolean
}) {
  const Icon = item.icon
  return (
    <Link
      className={`nav-item ${active ? 'active' : ''}`}
      to={item.href}
      title={collapsed ? item.label : undefined}
    >
      <Icon size={17} />
      {!collapsed && (
        <>
          <span>{item.label}</span>
          {item.badge && <em>{item.badge}</em>}
        </>
      )}
    </Link>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const [mobile, setMobile] = useState(false)
  const location = useLocation()
  const { status, health, checkConnection, setDemoMode } = useConnection()

  const currentPage =
    nav.concat(manage).find((x) => x.href === location.pathname)?.label || 'Overview'

  const getStatusDotClass = () => {
    switch (status) {
      case 'connected':
        return 'green'
      case 'database_unavailable':
        return 'amber'
      case 'backend_unavailable':
        return 'red'
      case 'connecting':
        return 'amber pulsing'
      default:
        return 'green'
    }
  }

  return (
    <div className='app-shell'>
      <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobile ? 'mobile-open' : ''}`}>
        <div className='brand'>
          <div className='brand-mark'>
            <Shield size={19} />
          </div>
          {!collapsed && (
            <div>
              <strong>
                Cyber<span>Sentinel</span>
              </strong>
              <small>SOC COMMAND CENTER</small>
            </div>
          )}
          <button
            className='icon-btn sidebar-close'
            onClick={() => setMobile(false)}
            aria-label='Close menu'
          >
            <X size={17} />
          </button>
        </div>

        {/* Honest Connection & Demo Pill */}
        {!collapsed && (
          <div
            className='demo-pill'
            style={
              status === 'connected'
                ? { background: '#0e2b26', borderColor: '#23655b', color: 'var(--green)' }
                : status === 'database_unavailable'
                ? { background: '#2c2211', borderColor: '#734e1c', color: 'var(--amber)' }
                : status === 'backend_unavailable'
                ? { background: '#2c1418', borderColor: '#6c2933', color: 'var(--red)' }
                : {}
            }
          >
            <span className={`status-dot ${getStatusDotClass()}`} style={{ margin: 0 }} />
            <span>
              {status === 'connected'
                ? 'LIVE BACKEND'
                : status === 'database_unavailable'
                ? 'DB OFFLINE (DEMO)'
                : status === 'backend_unavailable'
                ? 'OFFLINE (DEMO)'
                : status === 'connecting'
                ? 'CONNECTING...'
                : 'DEMO MODE'}
            </span>
          </div>
        )}

        <nav>
          <div className='nav-label'>WORKSPACE</div>
          {nav.map((item) => (
            <NavItem
              key={item.href}
              item={item}
              active={location.pathname === item.href}
              collapsed={collapsed}
            />
          ))}
        </nav>

        <nav className='nav-manage'>
          <div className='nav-label'>MANAGE</div>
          {manage.map((item) => (
            <NavItem
              key={item.href}
              item={item}
              active={location.pathname === item.href}
              collapsed={collapsed}
            />
          ))}
        </nav>

        <div className='sidebar-footer'>
          {!collapsed && (
            <div className='health-mini'>
              <span className={`status-dot ${getStatusDotClass()}`} />
              <div>
                <b>
                  {status === 'connected'
                    ? 'All systems operational'
                    : status === 'database_unavailable'
                    ? 'Database offline'
                    : status === 'backend_unavailable'
                    ? 'Backend unavailable'
                    : 'Checking connection...'}
                </b>
                <small>
                  {status === 'connected'
                    ? `API v${health?.version || '0.1.0'} · DB connected`
                    : status === 'database_unavailable'
                    ? 'API online · Demo fallback'
                    : status === 'backend_unavailable'
                    ? 'Running demo dataset'
                    : 'Contacting FastAPI...'}
                </small>
                {status !== 'connected' && (
                  <button
                    onClick={() => checkConnection()}
                    style={{
                      background: 'none',
                      border: 0,
                      color: 'var(--cyan)',
                      fontSize: '9px',
                      padding: '2px 0 0',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <RefreshCw size={10} /> Retry connection
                  </button>
                )}
              </div>
            </div>
          )}
          <button
            className='collapse-btn'
            onClick={() => setCollapsed(!collapsed)}
            aria-label='Toggle sidebar width'
          >
            {collapsed ? (
              <ChevronRight size={16} />
            ) : (
              <>
                <ChevronLeft size={16} /> Collapse
              </>
            )}
          </button>
        </div>
      </aside>

      <main className='main'>
        <header className='topbar'>
          <button
            className='icon-btn mobile-menu'
            onClick={() => setMobile(true)}
            aria-label='Open menu'
          >
            <Menu size={20} />
          </button>
          <div className='crumb'>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <b>{currentPage}</b>
          </div>
          <div className='top-actions'>
            <button className='search-btn' aria-label='Search anything'>
              <Search size={17} />
              <span>Search anything</span>
              <kbd>⌘ K</kbd>
            </button>
            <button className='icon-btn notification' aria-label='Notifications'>
              <Bell size={18} />
              <i />
            </button>
            <div className='profile'>
              <div className='avatar'>AM</div>
              <div className='profile-copy'>
                <b>Alex Morgan</b>
                <small>Security Analyst</small>
              </div>
              <ChevronDown size={15} />
            </div>
          </div>
        </header>

        <div className='page-content'>
          {/* Connection status warning banners */}
          {status === 'backend_unavailable' && (
            <div className='connection-banner error'>
              <AlertTriangle size={16} />
              <span>
                Backend API unreachable at <code>{API_BASE_URL}</code>. CyberSentinel is operating in offline
                demonstration mode with synthetic telemetry.
              </span>
              <button className='btn secondary' onClick={() => checkConnection()}>
                <RefreshCw size={13} /> Retry Connection
              </button>
            </div>
          )}

          {status === 'database_unavailable' && (
            <div className='connection-banner warning'>
              <AlertTriangle size={16} />
              <span>
                Backend API is online, but MongoDB Atlas database is disconnected. Operating with demo fallback
                dataset.
              </span>
              <button className='btn secondary' onClick={() => checkConnection()}>
                <RefreshCw size={13} /> Check Database
              </button>
            </div>
          )}

          {status === 'demo_mode' && (
            <div className='connection-banner info'>
              <CircleDot size={16} />
              <span>Demonstration Mode active. Synthetic telemetry is displayed.</span>
              <button className='btn secondary' onClick={() => setDemoMode(false)}>
                Switch to Live Data
              </button>
            </div>
          )}

          {children}
        </div>
      </main>
    </div>
  )
}

function Login() {
  return (
    <div className='login-page'>
      <div className='login-panel'>
        <div className='brand'>
          <div className='brand-mark'>
            <Shield size={19} />
          </div>
          <div>
            <strong>
              Cyber<span>Sentinel</span>
            </strong>
            <small>SOC COMMAND CENTER</small>
          </div>
        </div>
        <div className='demo-pill'>
          <CircleDot size={11} /> DEMO MODE
        </div>
        <h1>
          See Threats.
          <br />
          <span>Act Before Impact.</span>
        </h1>
        <p>Explore the security operations center with a live and demo workspace.</p>
        <Link className='btn login-btn' to='/dashboard'>
          Enter workspace <ChevronRight size={16} />
        </Link>
        <small className='login-note'>Phase 4 integrated environment. Live backend connected when online.</small>
      </div>
      <div className='login-art'>
        <div className='radar'>
          <div />
          <div />
          <div />
          <span>
            LIVE
            <br />
            MONITOR
          </span>
        </div>
        <div className='art-copy'>
          <span className='status-dot' /> Systems monitored <b>Active</b>
        </div>
      </div>
    </div>
  )
}

function App() {
  return (
    <ConnectionProvider>
      <BrowserRouter>
        <Routes>
          <Route path='/login' element={<Login />} />
          <Route
            path='*'
            element={
              <Shell>
                <Routes>
                  <Route path='/dashboard' element={<Dashboard />} />
                  <Route path='/threats' element={<ThreatsPage />} />
                  <Route path='/events' element={<EventsPage />} />
                  <Route path='/alerts' element={<AlertsPage />} />
                  <Route path='/incidents' element={<IncidentsPage />} />
                  <Route path='/analytics' element={<AnalyticsPage />} />
                  <Route path='/rules' element={<RulesPage />} />
                  <Route path='/settings' element={<SettingsPage />} />
                  <Route path='*' element={<Navigate to='/dashboard' replace />} />
                </Routes>
              </Shell>
            }
          />
        </Routes>
      </BrowserRouter>
    </ConnectionProvider>
  )
}

export default dynamic(() => Promise.resolve(App), { ssr: false })
