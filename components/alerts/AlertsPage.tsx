'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Edit3,
  FileText,
  Filter,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  X,
} from 'lucide-react'
import {
  alertsService,
  Alert,
  AlertStatus,
  AlertQueryParams,
  DEMO_ALERTS,
} from '../../lib/api'
import { useConnection } from '../../lib/context/ConnectionContext'

function Badge({ children }: { children: string }) {
  return <span className={`badge ${children.toLowerCase()}`}>{children}</span>
}

export function AlertsPage() {
  const { isLive } = useConnection()
  const [alerts, setAlerts] = useState<Alert[]>(DEMO_ALERTS)
  const [total, setTotal] = useState<number>(DEMO_ALERTS.length)
  const [page, setPage] = useState<number>(1)
  const pageSize = 10

  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  // Note editing modal
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null)
  const [notesInput, setNotesInput] = useState('')

  // Detail view modal
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)

  const fetchAlerts = useCallback(async () => {
    if (!isLive) {
      let filtered = [...DEMO_ALERTS]
      if (search) {
        const q = search.toLowerCase()
        filtered = filtered.filter(
          (a) =>
            a.id.toLowerCase().includes(q) ||
            a.title.toLowerCase().includes(q) ||
            a.rule_id.toLowerCase().includes(q) ||
            (a.detail && a.detail.toLowerCase().includes(q))
        )
      }
      if (severity) filtered = filtered.filter((a) => a.severity === severity)
      if (statusFilter) filtered = filtered.filter((a) => a.status === statusFilter)
      setTotal(filtered.length)
      setAlerts(filtered.slice((page - 1) * pageSize, page * pageSize))
      return
    }

    setLoading(true)
    setError(null)
    try {
      const params: AlertQueryParams = {
        page,
        page_size: pageSize,
        search: search || undefined,
        severity: severity || undefined,
        status: statusFilter || undefined,
      }
      const res = await alertsService.getAlerts(params)
      setAlerts(res.items)
      setTotal(res.total)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve alerts from backend.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [isLive, page, pageSize, search, severity, statusFilter])

  useEffect(() => {
    fetchAlerts()
  }, [fetchAlerts])

  const handleStatusChange = async (alertId: string, nextStatus: AlertStatus) => {
    setActionLoadingId(alertId)
    setActionError(null)

    if (!isLive) {
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, status: nextStatus, updated_at: new Date().toISOString() } : a))
      )
      setActionLoadingId(null)
      return
    }

    try {
      const updated = await alertsService.updateAlert(alertId, { status: nextStatus })
      // Update from confirmed backend response
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to transition alert to ${nextStatus}.`
      setActionError(msg)
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleSaveNotes = async () => {
    if (!editingAlert) return
    setActionLoadingId(editingAlert.id)
    setActionError(null)

    if (!isLive) {
      setAlerts((prev) =>
        prev.map((a) => (a.id === editingAlert.id ? { ...a, analyst_notes: notesInput } : a))
      )
      setEditingAlert(null)
      setActionLoadingId(null)
      return
    }

    try {
      const updated = await alertsService.updateAlert(editingAlert.id, { analyst_notes: notesInput })
      setAlerts((prev) => prev.map((a) => (a.id === editingAlert.id ? updated : a)))
      setEditingAlert(null)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save analyst notes.'
      setActionError(msg)
    } finally {
      setActionLoadingId(null)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <>
      <div className='page-header'>
        <div>
          <div className='eyebrow'>TRIAGE & REMEDIATION</div>
          <h1>Alert management</h1>
          <p>
            {isLive
              ? `Managing ${total} threat detection alerts in MongoDB.`
              : 'Managing demo alerts (backend or database unavailable).'}
          </p>
        </div>
        <div className='header-actions'>
          <button className='btn secondary' onClick={fetchAlerts} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className='connection-banner error'>
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button className='btn secondary' onClick={fetchAlerts}>
            Retry
          </button>
        </div>
      )}

      {actionError && (
        <div className='connection-banner error'>
          <AlertTriangle size={16} />
          <span>Action failed: {actionError}</span>
          <button className='btn secondary' onClick={() => setActionError(null)}>
            Dismiss
          </button>
        </div>
      )}

      <section className='card workspace-card'>
        <div className='toolbar'>
          <div className='input-wrap'>
            <Search size={16} />
            <input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              placeholder='Search alerts by title, rule ID, or detail...'
              aria-label='Search alerts'
            />
            {search && (
              <button
                onClick={() => {
                  setSearch('')
                  setPage(1)
                }}
                style={{ background: 'none', border: 0, color: 'var(--muted)', cursor: 'pointer' }}
              >
                <X size={14} />
              </button>
            )}
          </div>

          <select
            value={severity}
            onChange={(e) => {
              setSeverity(e.target.value)
              setPage(1)
            }}
            aria-label='Filter by severity'
          >
            <option value=''>All severities</option>
            <option value='Critical'>Critical</option>
            <option value='High'>High</option>
            <option value='Medium'>Medium</option>
            <option value='Low'>Low</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              setPage(1)
            }}
            aria-label='Filter by status'
          >
            <option value=''>All statuses</option>
            <option value='Open'>Open</option>
            <option value='Investigating'>Investigating</option>
            <option value='Resolved'>Resolved</option>
            <option value='Dismissed'>Dismissed</option>
          </select>
        </div>

        <div className='alert-management'>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '38px', color: 'var(--muted)' }}>
              <RefreshCw size={20} className='spin' style={{ margin: '0 auto 8px', display: 'block' }} />
              Loading alerts...
            </div>
          ) : alerts.length === 0 ? (
            <div className='empty-state'>
              <ShieldAlert size={30} />
              <h3>No security alerts found</h3>
              <p>No alerts match the selected criteria.</p>
              <button
                className='btn secondary'
                onClick={() => {
                  setSearch('')
                  setSeverity('')
                  setStatusFilter('')
                  setPage(1)
                }}
              >
                Reset filters
              </button>
            </div>
          ) : (
            alerts.map((a) => {
              const isMutating = actionLoadingId === a.id
              return (
                <div className='card managed-alert' key={a.id}>
                  <div className={`alert-icon ${a.severity.toLowerCase()}`}>
                    <AlertTriangle size={17} />
                  </div>
                  <div className='managed-main'>
                    <div>
                      <Badge>{a.severity}</Badge>
                      <span className='rule-label'>{a.rule_id}</span>
                      <Badge>{a.status}</Badge>
                    </div>
                    <h3>{a.title}</h3>
                    <p>{a.detail || 'Automated rule correlation finding.'}</p>
                    {a.analyst_notes && (
                      <div
                        style={{
                          margin: '6px 0',
                          padding: '6px 10px',
                          background: '#0a1622',
                          borderLeft: '2px solid var(--cyan)',
                          fontSize: '11px',
                          color: '#b6cbd8',
                        }}
                      >
                        <b>Analyst Notes:</b> {a.analyst_notes}
                      </div>
                    )}
                    <small>
                      {new Date(a.timestamp).toLocaleString()} · Matched events: {a.matched_count}
                      {a.assigned_to ? ` · Assigned to: ${a.assigned_to}` : ''}
                    </small>
                  </div>
                  <div className='managed-actions'>
                    {a.status === 'Open' && (
                      <button
                        className='btn secondary'
                        onClick={() => handleStatusChange(a.id, 'Investigating')}
                        disabled={isMutating}
                      >
                        {isMutating ? <RefreshCw size={12} className='spin' /> : 'Investigate'}
                      </button>
                    )}
                    {a.status !== 'Resolved' && (
                      <button
                        className='btn'
                        onClick={() => handleStatusChange(a.id, 'Resolved')}
                        disabled={isMutating}
                      >
                        {isMutating ? <RefreshCw size={12} className='spin' /> : 'Resolve'}
                      </button>
                    )}
                    <button
                      className='btn secondary'
                      onClick={() => {
                        setEditingAlert(a)
                        setNotesInput(a.analyst_notes || '')
                      }}
                      title='Add or edit notes'
                    >
                      <Edit3 size={13} />
                    </button>
                    <button
                      className='btn secondary'
                      onClick={() => setSelectedAlert(a)}
                      title='View alert telemetry evidence'
                    >
                      <FileText size={13} /> Details
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>

        <div className='pagination-bar'>
          <span>
            Showing {alerts.length > 0 ? (page - 1) * pageSize + 1 : 0} to{' '}
            {Math.min(page * pageSize, total)} of {total} alerts
          </span>
          <div className='pagination-controls'>
            <button
              className='pagination-btn'
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              <ChevronLeft size={13} /> Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              className='pagination-btn'
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Next <ChevronRight size={13} />
            </button>
          </div>
        </div>
      </section>

      {/* Edit Notes Modal */}
      {editingAlert && (
        <div className='modal-backdrop' onClick={() => setEditingAlert(null)}>
          <div className='modal-card' onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
            <div className='modal-header'>
              <h2>Analyst Investigation Notes</h2>
              <button className='icon-btn' onClick={() => setEditingAlert(null)}>
                <X size={17} />
              </button>
            </div>
            <div className='modal-body'>
              <p style={{ color: 'var(--muted)', marginBottom: '12px' }}>
                Document triage observations, containment steps, or forensic links for alert{' '}
                <b>{editingAlert.id}</b>.
              </p>
              <textarea
                value={notesInput}
                onChange={(e) => setNotesInput(e.target.value)}
                rows={5}
                style={{
                  width: '100%',
                  background: '#091522',
                  border: '1px solid var(--line)',
                  borderRadius: '6px',
                  color: 'var(--text)',
                  padding: '10px',
                  fontFamily: 'inherit',
                  fontSize: '12px',
                  outline: 'none',
                }}
                placeholder='Type investigation notes here...'
              />
            </div>
            <div className='modal-footer'>
              <button className='btn secondary' onClick={() => setEditingAlert(null)}>
                Cancel
              </button>
              <button className='btn' onClick={handleSaveNotes} disabled={actionLoadingId === editingAlert.id}>
                {actionLoadingId === editingAlert.id ? (
                  <>
                    <RefreshCw size={13} className='spin' /> Saving...
                  </>
                ) : (
                  'Save Notes'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Alert Details Modal */}
      {selectedAlert && (
        <div className='modal-backdrop' onClick={() => setSelectedAlert(null)}>
          <div className='modal-card' onClick={(e) => e.stopPropagation()}>
            <div className='modal-header'>
              <h2>Alert Telemetry: {selectedAlert.id}</h2>
              <button className='icon-btn' onClick={() => setSelectedAlert(null)}>
                <X size={17} />
              </button>
            </div>
            <div className='modal-body'>
              <div className='detail-grid'>
                <div className='detail-field'>
                  <label>Rule ID</label>
                  <span>{selectedAlert.rule_id}</span>
                </div>
                <div className='detail-field'>
                  <label>Status</label>
                  <span>
                    <Badge>{selectedAlert.status}</Badge>
                  </span>
                </div>
                <div className='detail-field'>
                  <label>Severity</label>
                  <span>
                    <Badge>{selectedAlert.severity}</Badge>
                  </span>
                </div>
                <div className='detail-field'>
                  <label>Matched Event Count</label>
                  <span>{selectedAlert.matched_count}</span>
                </div>
                <div className='detail-field' style={{ gridColumn: 'span 2' }}>
                  <label>Title</label>
                  <span>{selectedAlert.title}</span>
                </div>
                <div className='detail-field' style={{ gridColumn: 'span 2' }}>
                  <label>Detail</label>
                  <span>{selectedAlert.detail || 'N/A'}</span>
                </div>
                <div className='detail-field' style={{ gridColumn: 'span 2' }}>
                  <label>Correlated Event IDs</label>
                  <span style={{ fontFamily: 'monospace', fontSize: '11px', color: 'var(--cyan)' }}>
                    {selectedAlert.event_ids.length > 0
                      ? selectedAlert.event_ids.join(', ')
                      : 'None specified'}
                  </span>
                </div>
              </div>

              <div style={{ marginTop: '16px' }}>
                <label style={{ display: 'block', fontSize: '10px', color: 'var(--muted)', marginBottom: '6px' }}>
                  FULL ALERT RECORD (JSON)
                </label>
                <pre className='json-viewer'>
                  {JSON.stringify(selectedAlert, null, 2)}
                </pre>
              </div>
            </div>
            <div className='modal-footer'>
              <button className='btn secondary' onClick={() => setSelectedAlert(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
