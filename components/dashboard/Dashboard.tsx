'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ChevronRight,
  Download,
  MoreHorizontal,
  Play,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Target,
  X,
  Zap,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  analyticsService,
  eventsService,
  alertsService,
  detectionService,
  DashboardSummary,
  TrendsResponse,
  SeverityResponse,
  SecurityEvent,
  Alert,
  DetectionRunSummary,
  DEMO_SUMMARY,
  DEMO_TRENDS,
  DEMO_SEVERITY,
  DEMO_EVENTS,
  DEMO_ALERTS,
} from '../../lib/api'
import { useConnection } from '../../lib/context/ConnectionContext'

interface KpiProps {
  label: string
  value: string | number
  delta: string
  icon: React.ComponentType<{ size?: number }>
  color: string
}

function Kpi({ label, value, delta, icon: Icon, color }: KpiProps) {
  return (
    <div className='card kpi'>
      <div className={`kpi-icon ${color}`}>
        <Icon size={18} />
      </div>
      <div>
        <span>{label}</span>
        <strong>{typeof value === 'number' ? value.toLocaleString() : value}</strong>
        <small className={delta.startsWith('+') ? 'positive' : ''}>{delta}</small>
      </div>
      <MoreHorizontal size={17} className='kpi-more' />
    </div>
  )
}

function CardTitle({
  title,
  meta,
  action,
  link,
}: {
  title: string
  meta?: string
  action?: React.ReactNode
  link?: string
}) {
  return (
    <div className='card-title'>
      <div>
        <h2>{title}</h2>
        {meta && link ? (
          <Link to={link}>
            {meta}
            <ChevronRight size={13} />
          </Link>
        ) : meta ? (
          <span>{meta}</span>
        ) : null}
      </div>
      {action}
    </div>
  )
}

function Badge({ children }: { children: string }) {
  return <span className={`badge ${children.toLowerCase()}`}>{children}</span>
}

export function Dashboard() {
  const { isLive, status, health, checkConnection } = useConnection()
  const [range, setRange] = useState<'24h' | '7d'>('24h')
  const [summary, setSummary] = useState<DashboardSummary>(DEMO_SUMMARY)
  const [trends, setTrends] = useState<TrendsResponse>(DEMO_TRENDS)
  const [severity, setSeverity] = useState<SeverityResponse>(DEMO_SEVERITY)
  const [recentEvents, setRecentEvents] = useState<SecurityEvent[]>(DEMO_EVENTS)
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>(DEMO_ALERTS)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState<DetectionRunSummary | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)

  const loadDashboardData = useCallback(async () => {
    if (!isLive) {
      // Use demo data layer if not connected to live database
      setSummary(DEMO_SUMMARY)
      setTrends(DEMO_TRENDS)
      setSeverity(DEMO_SEVERITY)
      setRecentEvents(DEMO_EVENTS.slice(0, 4))
      setRecentAlerts(DEMO_ALERTS.slice(0, 3))
      return
    }

    setLoading(true)
    try {
      const [sumRes, trendRes, sevRes, evtRes, altRes] = await Promise.allSettled([
        analyticsService.getSummary(),
        analyticsService.getTrends(range),
        analyticsService.getSeverity(),
        eventsService.getEvents({ page: 1, page_size: 4, sort_by: 'timestamp', sort_dir: 'desc' }),
        alertsService.getAlerts({ page: 1, page_size: 3 }),
      ])

      if (sumRes.status === 'fulfilled') setSummary(sumRes.value)
      if (trendRes.status === 'fulfilled') setTrends(trendRes.value)
      if (sevRes.status === 'fulfilled') setSeverity(sevRes.value)
      if (evtRes.status === 'fulfilled') setRecentEvents(evtRes.value.items)
      if (altRes.status === 'fulfilled') setRecentAlerts(altRes.value.items)
    } catch {
      // Handled by Promise.allSettled
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [isLive, range])

  useEffect(() => {
    loadDashboardData()
  }, [loadDashboardData])

  const handleRefresh = async () => {
    setRefreshing(true)
    await checkConnection()
    await loadDashboardData()
  }

  const handleRunScan = async () => {
    if (scanning) return
    setScanning(true)
    setScanError(null)

    if (!isLive) {
      // Fallback demo simulation
      setTimeout(() => {
        setScanResult({
          run_id: 'RUN-DEMO-01',
          timestamp: new Date().toISOString(),
          lookback_minutes: 60,
          events_examined: 24891,
          rules_evaluated: 4,
          detections_generated: 3,
          alerts_created: 1,
          alerts_deduplicated: 2,
          detections: [],
        })
        setScanning(false)
      }, 900)
      return
    }

    try {
      const result = await detectionService.runDetection({ lookback_minutes: 60 })
      setScanResult(result)
      // Refresh alerts and summary after scan
      loadDashboardData()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Detection scan execution failed.'
      setScanError(msg)
    } finally {
      setScanning(false)
    }
  }

  // Format severity pie chart data
  const pieData = [
    { n: 'Critical', v: severity.alerts_by_severity['Critical'] || 0, c: '#f2636b' },
    { n: 'High', v: severity.alerts_by_severity['High'] || 0, c: '#f09a52' },
    { n: 'Medium', v: severity.alerts_by_severity['Medium'] || 0, c: '#e9c46a' },
    { n: 'Low', v: severity.alerts_by_severity['Low'] || 0, c: '#4de0d2' },
  ]
  const totalPieAlerts = pieData.reduce((acc, curr) => acc + curr.v, 0)

  const formatTimeAgo = (iso?: string) => {
    if (!iso) return 'just now'
    try {
      const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
      if (diff <= 1) return '1 min ago'
      if (diff < 60) return `${diff} min ago`
      const hours = Math.floor(diff / 60)
      if (hours < 24) return `${hours}h ago`
      return `${Math.floor(hours / 24)}d ago`
    } catch {
      return iso
    }
  }

  const exportCurrentMetrics = () => {
    const csvContent =
      'Metric,Value\n' +
      `Total Security Events,${summary.total_events}\n` +
      `Active Threat Alerts,${summary.active_alerts}\n` +
      `Open Incidents,${summary.open_incidents}\n` +
      `Detection Coverage,${summary.detection_coverage_pct}%\n` +
      `Rules Triggered,${summary.rules_triggered}\n`

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `cybersentinel_overview_${range}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <>
      <div className='page-header'>
        <div>
          <div className='eyebrow'>SECURITY OPERATIONS</div>
          <h1>Security overview</h1>
          <p>
            {isLive
              ? 'Real-time telemetry and posture streamed from MongoDB backend.'
              : 'Viewing demonstration security telemetry (live backend offline).'}
          </p>
        </div>
        <div className='header-actions'>
          <button className='btn secondary' onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <button className='btn secondary' onClick={exportCurrentMetrics}>
            <Download size={14} /> Export
          </button>
          <button className='btn' onClick={handleRunScan} disabled={scanning}>
            {scanning ? (
              <>
                <RefreshCw size={14} className='spin' /> Running scan...
              </>
            ) : (
              <>
                <Play size={14} /> Run detection scan
              </>
            )}
          </button>
        </div>
      </div>

      {scanResult && (
        <div className='scan-banner'>
          <Sparkles size={17} />
          <span>
            Detection scan <b>{scanResult.run_id}</b> complete ({scanResult.lookback_minutes}m lookback) —{' '}
            {scanResult.events_examined} events examined against {scanResult.rules_evaluated} rules.
            Generated {scanResult.detections_generated} detection(s), {scanResult.alerts_created} alert(s) created,{' '}
            {scanResult.alerts_deduplicated} deduplicated.
          </span>
          <button onClick={() => setScanResult(null)}>
            <X size={15} />
          </button>
        </div>
      )}

      {scanError && (
        <div className='connection-banner error'>
          <AlertTriangle size={17} />
          <span>Detection scan error: {scanError}</span>
          <button className='btn secondary' onClick={() => setScanError(null)}>
            Dismiss
          </button>
        </div>
      )}

      <div className='kpi-grid'>
        <Kpi
          label='Total security events'
          value={summary.total_events}
          delta={isLive ? 'Live count' : '+12.4%'}
          icon={Activity}
          color='cyan'
        />
        <Kpi
          label='Active threat alerts'
          value={summary.active_alerts}
          delta={isLive ? `${summary.active_alerts} open` : '+3 today'}
          icon={ShieldAlert}
          color='red'
        />
        <Kpi
          label='Open incidents'
          value={summary.open_incidents}
          delta={isLive ? `${summary.open_incidents} active` : '-2 this week'}
          icon={Target}
          color='orange'
        />
        <Kpi
          label='Detection coverage'
          value={`${summary.detection_coverage_pct}%`}
          delta={`${summary.enabled_rules}/${summary.total_rules} rules`}
          icon={Zap}
          color='green'
        />
      </div>

      <div className='dashboard-grid'>
        <section className='card chart-card'>
          <CardTitle
            title='Security events'
            meta={`Last ${range === '24h' ? '24 hours' : '7 days'}`}
            action={
              <select
                value={range}
                onChange={(e) => setRange(e.target.value as '24h' | '7d')}
                aria-label='Select trend timeframe'
              >
                <option value='24h'>Last 24 hours</option>
                <option value='7d'>Last 7 days</option>
              </select>
            }
          />
          <div className='chart-legend'>
            <span>
              <i className='legend-cyan' /> Events
            </span>
            <span className='muted'>
              {trends.peak_label || `Total in period: ${trends.total_in_period}`}
            </span>
          </div>
          <ResponsiveContainer width='100%' height={245}>
            <AreaChart data={trends.points}>
              <defs>
                <linearGradient id='area' x1='0' y1='0' x2='0' y2='1'>
                  <stop offset='0%' stopColor='#4de0d2' stopOpacity={0.3} />
                  <stop offset='100%' stopColor='#4de0d2' stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke='#1d2c3b' />
              <XAxis dataKey='d' axisLine={false} tickLine={false} tick={{ fill: '#718296', fontSize: 11 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: '#718296', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: '#101b28',
                  border: '1px solid #26394a',
                  borderRadius: 8,
                  color: '#dce8ef',
                }}
              />
              <Area type='monotone' dataKey='v' stroke='#4de0d2' strokeWidth={2} fill='url(#area)' />
            </AreaChart>
          </ResponsiveContainer>
        </section>

        <section className='card severity-card'>
          <CardTitle title='Threat severity' meta='Active alerts breakdown' />
          <div className='donut-wrap'>
            <ResponsiveContainer width='55%' height={190}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey='v'
                  innerRadius={55}
                  outerRadius={78}
                  paddingAngle={4}
                >
                  {pieData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.c} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className='severity-total'>
              <b>{totalPieAlerts}</b>
              <span>Total alerts</span>
            </div>
          </div>
          <div className='severity-list'>
            {pieData.map((item) => (
              <div key={item.n}>
                <span>
                  <i style={{ background: item.c }} />
                  {item.n}
                </span>
                <b>{item.v}</b>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className='dashboard-grid lower'>
        <section className='card table-card'>
          <CardTitle title='Recent events' meta='View all events' link='/events' />
          <div className='table-wrap'>
            <table>
              <thead>
                <tr>
                  <th>EVENT</th>
                  <th>SOURCE</th>
                  <th>USER</th>
                  <th>TIME</th>
                  <th>SEVERITY</th>
                </tr>
              </thead>
              <tbody>
                {recentEvents.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '28px', color: 'var(--muted)' }}>
                      No events recorded in this period.
                    </td>
                  </tr>
                ) : (
                  recentEvents.map((e) => (
                    <tr key={e.id}>
                      <td>
                        <b>{e.event_type}</b>
                        <small>{e.id}</small>
                      </td>
                      <td>{e.source || 'system'}</td>
                      <td>{e.username || 'unknown'}</td>
                      <td>{formatTimeAgo(e.timestamp)}</td>
                      <td>
                        <Badge>{e.severity}</Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className='card alert-card'>
          <CardTitle title='Recent alerts' meta='View all alerts' link='/alerts' />
          <div className='alert-list'>
            {recentAlerts.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '35px 20px', color: 'var(--muted)' }}>
                No active security alerts.
              </div>
            ) : (
              recentAlerts.map((a) => (
                <div className='alert-row' key={a.id || a.rule_id}>
                  <div className={`alert-icon ${a.severity.toLowerCase()}`}>
                    <AlertTriangle size={15} />
                  </div>
                  <div>
                    <b>{a.title}</b>
                    <small>{a.detail || `Triggered by rule ${a.rule_id}`}</small>
                  </div>
                  <div className='alert-time'>
                    <Badge>{a.severity}</Badge>
                    <small>{formatTimeAgo(a.timestamp)}</small>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <div className='system-strip'>
        <span
          className={`status-dot ${
            status === 'connected' ? 'green' : status === 'database_unavailable' ? 'amber' : 'red'
          }`}
        />
        <b>System health</b>
        <span>
          FastAPI Engine <i style={{ background: isLive ? 'var(--green)' : 'var(--red)' }} />
        </span>
        <span>
          MongoDB Atlas{' '}
          <i
            style={{
              background: status === 'connected' ? 'var(--green)' : 'var(--amber)',
            }}
          />
        </span>
        <span>
          Detection Pipeline <i style={{ background: isLive ? 'var(--green)' : 'var(--green)' }} />
        </span>
        <span className='system-updated'>
          {health?.version ? `API v${health.version}` : 'Local Demo Runtime'} · Checked just now
        </span>
      </div>
    </>
  )
}
