'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  Activity,
  AlertTriangle,
  Download,
  MoreHorizontal,
  RefreshCw,
  ShieldAlert,
  Target,
  Zap,
} from 'lucide-react'
import {
  Bar,
  BarChart,
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
  DashboardSummary,
  TrendsResponse,
  SeverityResponse,
  SourceDistributionResponse,
  DEMO_SUMMARY,
  DEMO_TRENDS,
  DEMO_SEVERITY,
} from '../../lib/api'
import { useConnection } from '../../lib/context/ConnectionContext'

function Kpi({
  label,
  value,
  delta,
  icon: Icon,
  color,
}: {
  label: string
  value: string | number
  delta: string
  icon: React.ComponentType<{ size?: number }>
  color: string
}) {
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
}: {
  title: string
  meta?: string
  action?: React.ReactNode
}) {
  return (
    <div className='card-title'>
      <div>
        <h2>{title}</h2>
        {meta && <span>{meta}</span>}
      </div>
      {action}
    </div>
  )
}

export function AnalyticsPage() {
  const { isLive } = useConnection()
  const [range, setRange] = useState<'24h' | '7d'>('7d')
  const [summary, setSummary] = useState<DashboardSummary>(DEMO_SUMMARY)
  const [trends, setTrends] = useState<TrendsResponse>(DEMO_TRENDS)
  const [severity, setSeverity] = useState<SeverityResponse>(DEMO_SEVERITY)
  const [sources, setSources] = useState<SourceDistributionResponse>({
    items: [
      { d: 'auth-service', v: 48 },
      { d: 'api-gateway', v: 36 },
      { d: 'edge-proxy', v: 29 },
      { d: 'admin-console', v: 14 },
      { d: 'database', v: 9 },
    ],
    total: 136,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAnalytics = useCallback(async () => {
    if (!isLive) {
      setSummary(DEMO_SUMMARY)
      setTrends(DEMO_TRENDS)
      setSeverity(DEMO_SEVERITY)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const [sumRes, trendRes, sevRes, srcRes] = await Promise.allSettled([
        analyticsService.getSummary(),
        analyticsService.getTrends(range),
        analyticsService.getSeverity(),
        analyticsService.getSources(range),
      ])

      if (sumRes.status === 'fulfilled') setSummary(sumRes.value)
      if (trendRes.status === 'fulfilled') setTrends(trendRes.value)
      if (sevRes.status === 'fulfilled') setSeverity(sevRes.value)
      if (srcRes.status === 'fulfilled') setSources(srcRes.value)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch analytics.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [isLive, range])

  useEffect(() => {
    fetchAnalytics()
  }, [fetchAnalytics])

  const exportReport = () => {
    let csv = 'SECTION,LABEL,COUNT\n'
    // Summary
    csv += `Summary,Total Events,${summary.total_events}\n`
    csv += `Summary,Active Alerts,${summary.active_alerts}\n`
    csv += `Summary,Open Incidents,${summary.open_incidents}\n`
    csv += `Summary,Rules Triggered,${summary.rules_triggered}\n`
    csv += `Summary,Coverage,${summary.detection_coverage_pct}%\n`

    // Trends
    trends.points.forEach((p) => {
      csv += `Trends,${p.d},${p.v}\n`
    })

    // Severity
    Object.entries(severity.alerts_by_severity).forEach(([k, v]) => {
      csv += `Alert Severity,${k},${v}\n`
    })

    // Sources
    sources.items.forEach((s) => {
      csv += `Sources,${s.d},${s.v}\n`
    })

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `cybersentinel_analytics_${range}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Format source bar data
  const barData = sources.items.length > 0 ? sources.items : trends.points

  return (
    <>
      <div className='page-header'>
        <div>
          <div className='eyebrow'>SECURITY INTELLIGENCE</div>
          <h1>Security analytics</h1>
          <p>
            {isLive
              ? 'Aggregated telemetry metrics and trend distribution across your environment.'
              : 'Demonstration analytics reports (backend or database offline).'}
          </p>
        </div>
        <div className='header-actions'>
          <button className='btn secondary' onClick={fetchAnalytics} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
          </button>
          <button className='btn secondary' onClick={exportReport}>
            <Download size={15} /> Export report
          </button>
        </div>
      </div>

      {error && (
        <div className='connection-banner error'>
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button className='btn secondary' onClick={fetchAnalytics}>
            Retry
          </button>
        </div>
      )}

      <div className='analytics-grid'>
        <section className='card analytics-chart'>
          <CardTitle
            title='Telemetry by source / interval'
            meta={`Last ${range === '7d' ? '7 days' : '24 hours'}`}
            action={
              <select
                value={range}
                onChange={(e) => setRange(e.target.value as '24h' | '7d')}
                aria-label='Analytics timeframe'
              >
                <option value='24h'>Last 24 hours</option>
                <option value='7d'>Last 7 days</option>
              </select>
            }
          />
          <ResponsiveContainer width='100%' height={280}>
            <BarChart data={barData}>
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
              <Bar dataKey='v' fill='#4de0d2' radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <div className='analytics-stats'>
          <Kpi
            label='Total Telemetry Volume'
            value={summary.total_events}
            delta={isLive ? 'Recorded' : '+12.4%'}
            icon={Activity}
            color='cyan'
          />
          <Kpi
            label='Open Incident Cases'
            value={summary.open_incidents}
            delta={isLive ? 'Active' : '-6.4%'}
            icon={Target}
            color='cyan'
          />
          <Kpi
            label='Rules Triggered (Alerts)'
            value={summary.rules_triggered}
            delta={isLive ? 'Detections' : '+8.9%'}
            icon={ShieldAlert}
            color='orange'
          />
        </div>
      </div>
    </>
  )
}
