'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Play,
  RefreshCw,
  Shield,
  ShieldAlert,
  Sparkles,
  Zap,
} from 'lucide-react'
import {
  detectionService,
  DetectionRunSummary,
  DetectionRule,
  DEMO_RULES,
} from '../../lib/api'
import { useConnection } from '../../lib/context/ConnectionContext'

function Badge({ children }: { children: string }) {
  return <span className={`badge ${children.toLowerCase()}`}>{children}</span>
}

export function ThreatsPage() {
  const { isLive } = useConnection()
  const [rules, setRules] = useState<DetectionRule[]>(DEMO_RULES)
  const [lookbackMinutes, setLookbackMinutes] = useState(60)
  const [runningScan, setRunningScan] = useState(false)
  const [lastSummary, setLastSummary] = useState<DetectionRunSummary | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)
  const [rulesLoading, setRulesLoading] = useState(false)

  const fetchRules = useCallback(async () => {
    if (!isLive) {
      setRules(DEMO_RULES)
      return
    }
    setRulesLoading(true)
    try {
      const res = await detectionService.getRules()
      setRules(res)
    } catch {
      // Fallback
    } finally {
      setRulesLoading(false)
    }
  }, [isLive])

  useEffect(() => {
    fetchRules()
  }, [fetchRules])

  const handleRunDetection = async () => {
    if (runningScan) return
    setRunningScan(true)
    setScanError(null)

    if (!isLive) {
      setTimeout(() => {
        setLastSummary({
          run_id: 'RUN-DEMO-SCAN',
          timestamp: new Date().toISOString(),
          lookback_minutes: lookbackMinutes,
          events_examined: 24891,
          rules_evaluated: rules.filter((r) => r.enabled).length,
          detections_generated: 3,
          alerts_created: 1,
          alerts_deduplicated: 2,
          detections: [
            {
              rule_id: 'AUTH-001',
              title: 'Repeated Failed Logins',
              severity: 'Critical',
              detection_time: new Date().toISOString(),
              matched_event_ids: ['EVT-8F29A', 'EVT-8F26D'],
              matched_event_count: 5,
              detection_reason: '5 failed login attempts observed within 10-minute window.',
              evidence_summary: 'Source IP: 185.22.14.8 exceeded threshold.',
              source_identifier: '185.22.14.8',
              group_key: 'source_ip:185.22.14.8',
              dedup_key: 'AUTH-001:185.22.14.8',
              status: 'Open',
            },
          ],
        })
        setRunningScan(false)
      }, 800)
      return
    }

    try {
      const summary = await detectionService.runDetection({ lookback_minutes: lookbackMinutes })
      setLastSummary(summary)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Threat detection run failed on backend.'
      setScanError(msg)
    } finally {
      setRunningScan(false)
    }
  }

  return (
    <>
      <div className='page-header'>
        <div>
          <div className='eyebrow'>DETECTION ENGINE</div>
          <h1>Threat detection</h1>
          <p>
            {isLive
              ? 'Execute on-demand rule correlation scans across stored security telemetry.'
              : 'Execute simulated detection scans against demo telemetry.'}
          </p>
        </div>
        <div className='header-actions'>
          <button
            className='btn'
            onClick={handleRunDetection}
            disabled={runningScan}
            title={runningScan ? 'Scan currently in progress' : 'Run detection scan now'}
          >
            {runningScan ? (
              <>
                <RefreshCw size={14} className='spin' /> Running detection...
              </>
            ) : (
              <>
                <Play size={14} /> Run detection scan
              </>
            )}
          </button>
        </div>
      </div>

      <div className='threat-callout'>
        <div className='kpi-icon green'>
          <Sparkles size={18} />
        </div>
        <div>
          <b>Rule-based threat correlation engine ready</b>
          <p>
            Evaluates enabled threat detection rules across historical security events within the chosen lookback window.
            Creates deduplicated alerts in MongoDB Atlas for analyst triage.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <select
            value={lookbackMinutes}
            onChange={(e) => setLookbackMinutes(Number(e.target.value))}
            style={{
              background: '#091522',
              border: '1px solid var(--line)',
              color: 'var(--text)',
              padding: '7px 10px',
              borderRadius: '6px',
              fontSize: '11px',
            }}
            disabled={runningScan}
            aria-label='Lookback window'
          >
            <option value={15}>15 minutes lookback</option>
            <option value={30}>30 minutes lookback</option>
            <option value={60}>60 minutes lookback</option>
            <option value={180}>3 hours lookback</option>
            <option value={1440}>24 hours lookback</option>
          </select>
          <button className='btn' onClick={handleRunDetection} disabled={runningScan}>
            {runningScan ? <RefreshCw size={14} className='spin' /> : <Play size={14} />} Run detection
          </button>
        </div>
      </div>

      {scanError && (
        <div className='connection-banner error'>
          <AlertTriangle size={16} />
          <span>{scanError}</span>
          <button className='btn secondary' onClick={() => setScanError(null)}>
            Dismiss
          </button>
        </div>
      )}

      {lastSummary && (
        <section className='card' style={{ padding: '22px', marginBottom: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <span style={{ fontSize: '10px', color: 'var(--cyan)', letterSpacing: '1px', textTransform: 'uppercase' }}>
                LATEST DETECTION RUN
              </span>
              <h2 style={{ margin: '4px 0 0', fontSize: '18px' }}>Execution Run: {lastSummary.run_id}</h2>
            </div>
            <Badge>{new Date(lastSummary.timestamp).toLocaleTimeString()}</Badge>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: '12px',
              padding: '16px',
              background: '#08141f',
              borderRadius: '8px',
              border: '1px solid var(--line)',
              marginBottom: '20px',
            }}
          >
            <div>
              <small style={{ color: 'var(--muted)', display: 'block', fontSize: '9px' }}>LOOKBACK</small>
              <b style={{ fontSize: '16px' }}>{lastSummary.lookback_minutes}m</b>
            </div>
            <div>
              <small style={{ color: 'var(--muted)', display: 'block', fontSize: '9px' }}>EVENTS EXAMINED</small>
              <b style={{ fontSize: '16px', color: 'var(--cyan)' }}>{lastSummary.events_examined.toLocaleString()}</b>
            </div>
            <div>
              <small style={{ color: 'var(--muted)', display: 'block', fontSize: '9px' }}>RULES EVALUATED</small>
              <b style={{ fontSize: '16px' }}>{lastSummary.rules_evaluated}</b>
            </div>
            <div>
              <small style={{ color: 'var(--muted)', display: 'block', fontSize: '9px' }}>DETECTIONS GENERATED</small>
              <b style={{ fontSize: '16px', color: lastSummary.detections_generated > 0 ? 'var(--orange)' : 'var(--text)' }}>
                {lastSummary.detections_generated}
              </b>
            </div>
            <div>
              <small style={{ color: 'var(--muted)', display: 'block', fontSize: '9px' }}>ALERTS CREATED</small>
              <b style={{ fontSize: '16px', color: lastSummary.alerts_created > 0 ? 'var(--red)' : 'var(--green)' }}>
                {lastSummary.alerts_created}
              </b>
            </div>
          </div>

          <h3 style={{ fontSize: '13px', margin: '0 0 12px' }}>Matched Detection Findings</h3>
          {lastSummary.detections.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px', color: 'var(--muted)', background: '#091522', borderRadius: '6px' }}>
              <CheckCircle2 size={24} style={{ color: 'var(--green)', margin: '0 auto 6px', display: 'block' }} />
              <b>No suspicious patterns exceeded rule thresholds during this window.</b>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '10px' }}>
              {lastSummary.detections.map((d, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '14px',
                    background: '#091624',
                    border: '1px solid var(--line)',
                    borderRadius: '6px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <Badge>{d.severity}</Badge>
                      <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Rule: {d.rule_id}</span>
                      <b style={{ fontSize: '13px' }}>{d.title}</b>
                    </div>
                    <small style={{ color: 'var(--muted)', fontSize: '10px' }}>
                      {new Date(d.detection_time).toLocaleTimeString()}
                    </small>
                  </div>
                  <p style={{ margin: '8px 0 6px', color: '#b5cad6', fontSize: '12px' }}>
                    {d.detection_reason}
                  </p>
                  <div style={{ fontSize: '11px', color: 'var(--muted)' }}>
                    <b>Evidence:</b> {d.evidence_summary} · Matched {d.matched_event_count} telemetry event(s)
                    {d.matched_event_ids.length > 0 && (
                      <span style={{ marginLeft: '10px', color: 'var(--cyan)', fontFamily: 'monospace' }}>
                        [{d.matched_event_ids.join(', ')}]
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Configured Rules Summary */}
      <section className='card' style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <h2 style={{ fontSize: '14px', margin: 0 }}>Active Detection Rules ({rules.filter((r) => r.enabled).length}/{rules.length})</h2>
          <a href='/rules' style={{ fontSize: '11px', color: 'var(--cyan)' }}>
            Configure rules in Control Plane →
          </a>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
          {rules.map((r) => (
            <div
              key={r.id}
              style={{
                padding: '12px 14px',
                background: '#08141f',
                border: '1px solid var(--line)',
                borderRadius: '6px',
                opacity: r.enabled ? 1 : 0.6,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '11px', fontWeight: 'bold' }}>{r.id}</span>
                <Badge>{r.severity}</Badge>
              </div>
              <b style={{ fontSize: '12px', display: 'block', color: 'var(--text)' }}>{r.name}</b>
              <small style={{ color: 'var(--muted)', display: 'block', marginTop: '4px', fontSize: '10px' }}>
                Threshold: {r.threshold} events / {r.window_minutes}m · {r.enabled ? 'Active' : 'Disabled'}
              </small>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
