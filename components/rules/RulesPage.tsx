'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Sliders,
  X,
  Zap,
} from 'lucide-react'
import {
  detectionService,
  DetectionRule,
  RuleUpdatePayload,
  Severity,
  DEMO_RULES,
} from '../../lib/api'
import { useConnection } from '../../lib/context/ConnectionContext'

function Badge({ children }: { children: string }) {
  return <span className={`badge ${children.toLowerCase()}`}>{children}</span>
}

export function RulesPage() {
  const { isLive } = useConnection()
  const [rules, setRules] = useState<DetectionRule[]>(DEMO_RULES)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [togglingId, setTogglingId] = useState<string | null>(null)

  // Edit rule modal
  const [editingRule, setEditingRule] = useState<DetectionRule | null>(null)
  const [editThreshold, setEditThreshold] = useState<number>(5)
  const [editWindow, setEditWindow] = useState<number>(10)
  const [editSeverity, setEditSeverity] = useState<Severity>('High')
  const [savingRule, setSavingRule] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const fetchRules = useCallback(async () => {
    if (!isLive) {
      setRules(DEMO_RULES)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const res = await detectionService.getRules()
      setRules(res)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve detection rules.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [isLive])

  useEffect(() => {
    fetchRules()
  }, [fetchRules])

  const handleToggle = async (rule: DetectionRule) => {
    setTogglingId(rule.id)
    const nextEnabled = !rule.enabled

    if (!isLive) {
      setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, enabled: nextEnabled } : r)))
      setTogglingId(null)
      return
    }

    try {
      const updated = await detectionService.updateRule(rule.id, { enabled: nextEnabled })
      setRules((prev) => prev.map((r) => (r.id === rule.id ? updated : r)))
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to toggle rule state.')
    } finally {
      setTogglingId(null)
    }
  }

  const openEditModal = (rule: DetectionRule) => {
    setEditingRule(rule)
    setEditThreshold(rule.threshold)
    setEditWindow(rule.window_minutes)
    setEditSeverity(rule.severity)
    setSaveError(null)
  }

  const handleSaveRule = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingRule) return
    setSavingRule(true)
    setSaveError(null)

    const payload: RuleUpdatePayload = {
      threshold: Number(editThreshold),
      window_minutes: Number(editWindow),
      severity: editSeverity,
    }

    if (!isLive) {
      setRules((prev) =>
        prev.map((r) => (r.id === editingRule.id ? { ...r, ...payload } : r))
      )
      setEditingRule(null)
      setSavingRule(false)
      return
    }

    try {
      const updated = await detectionService.updateRule(editingRule.id, payload)
      setRules((prev) => prev.map((r) => (r.id === editingRule.id ? updated : r)))
      setEditingRule(null)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update rule configuration.'
      setSaveError(msg)
    } finally {
      setSavingRule(false)
    }
  }

  return (
    <>
      <div className='page-header'>
        <div>
          <div className='eyebrow'>CONTROL PLANE</div>
          <h1>Detection rules</h1>
          <p>
            {isLive
              ? 'Configure thresholds, evaluation windows, and enabled states in detection engine.'
              : 'Managing demo detection rules (backend or database offline).'}
          </p>
        </div>
        <div className='header-actions'>
          <button className='btn secondary' onClick={fetchRules} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className='connection-banner error'>
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button className='btn secondary' onClick={fetchRules}>
            Retry
          </button>
        </div>
      )}

      <div className='rules-list'>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
            <RefreshCw size={20} className='spin' style={{ margin: '0 auto 8px', display: 'block' }} />
            Loading detection rules...
          </div>
        ) : (
          rules.map((r) => {
            const isToggling = togglingId === r.id
            return (
              <div className='card rule-card' key={r.id}>
                <div className='rule-toggle'>
                  <button
                    className={`toggle ${r.enabled ? 'on' : ''}`}
                    onClick={() => handleToggle(r)}
                    disabled={isToggling}
                    title={r.enabled ? 'Click to disable rule' : 'Click to enable rule'}
                  >
                    <span />
                  </button>
                  <div>
                    <b>{r.name}</b>
                    <small>
                      {r.id} · {r.description}
                    </small>
                  </div>
                </div>
                <div className='rule-threshold'>
                  <small>THRESHOLD & WINDOW</small>
                  <b>
                    {r.threshold} events / {r.window_minutes}m
                  </b>
                </div>
                <Badge>{r.severity}</Badge>
                <button className='btn secondary' onClick={() => openEditModal(r)}>
                  Edit rule
                </button>
              </div>
            )
          })
        )}
      </div>

      {/* Edit Rule Modal */}
      {editingRule && (
        <div className='modal-backdrop' onClick={() => setEditingRule(null)}>
          <div className='modal-card' onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
            <div className='modal-header'>
              <h2>Tune Rule: {editingRule.name}</h2>
              <button className='icon-btn' onClick={() => setEditingRule(null)}>
                <X size={17} />
              </button>
            </div>
            <form onSubmit={handleSaveRule}>
              <div className='modal-body'>
                <p style={{ color: 'var(--muted)', marginBottom: '16px' }}>
                  Adjust correlation parameters for <b>{editingRule.id}</b>. Changes take effect on the next detection scan.
                </p>

                <div style={{ marginBottom: '14px' }}>
                  <label style={{ display: 'block', fontSize: '11px', color: 'var(--muted)', marginBottom: '5px' }}>
                    Severity
                  </label>
                  <select
                    value={editSeverity}
                    onChange={(e) => setEditSeverity(e.target.value as Severity)}
                    style={{
                      width: '100%',
                      background: '#091522',
                      border: '1px solid var(--line)',
                      borderRadius: '6px',
                      color: 'var(--text)',
                      padding: '8px 10px',
                      fontSize: '12px',
                    }}
                  >
                    <option value='Critical'>Critical</option>
                    <option value='High'>High</option>
                    <option value='Medium'>Medium</option>
                    <option value='Low'>Low</option>
                    <option value='Info'>Info</option>
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--muted)', marginBottom: '5px' }}>
                      Event Threshold (Count)
                    </label>
                    <input
                      type='number'
                      min={1}
                      max={10000}
                      required
                      value={editThreshold}
                      onChange={(e) => setEditThreshold(Number(e.target.value))}
                      style={{
                        width: '100%',
                        background: '#091522',
                        border: '1px solid var(--line)',
                        borderRadius: '6px',
                        color: 'var(--text)',
                        padding: '8px 10px',
                        fontSize: '12px',
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--muted)', marginBottom: '5px' }}>
                      Rolling Window (Minutes)
                    </label>
                    <input
                      type='number'
                      min={1}
                      max={1440}
                      required
                      value={editWindow}
                      onChange={(e) => setEditWindow(Number(e.target.value))}
                      style={{
                        width: '100%',
                        background: '#091522',
                        border: '1px solid var(--line)',
                        borderRadius: '6px',
                        color: 'var(--text)',
                        padding: '8px 10px',
                        fontSize: '12px',
                      }}
                    />
                  </div>
                </div>

                {saveError && (
                  <div className='connection-banner error'>
                    <AlertTriangle size={15} />
                    <span>{saveError}</span>
                  </div>
                )}
              </div>
              <div className='modal-footer'>
                <button
                  type='button'
                  className='btn secondary'
                  onClick={() => setEditingRule(null)}
                  disabled={savingRule}
                >
                  Cancel
                </button>
                <button type='submit' className='btn' disabled={savingRule}>
                  {savingRule ? (
                    <>
                      <RefreshCw size={13} className='spin' /> Saving...
                    </>
                  ) : (
                    'Save Configuration'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
