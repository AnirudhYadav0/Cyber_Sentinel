'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  AlertTriangle,
  CheckCircle,
  CircleDot,
  FileText,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Search,
  Target,
  X,
} from 'lucide-react'
import {
  incidentsService,
  Incident,
  IncidentStatus,
  IncidentQueryParams,
  DEMO_INCIDENTS,
} from '../../lib/api'
import { useConnection } from '../../lib/context/ConnectionContext'

function Badge({ children }: { children: string }) {
  return <span className={`badge ${children.toLowerCase()}`}>{children}</span>
}

export function IncidentsPage() {
  const { isLive } = useConnection()
  const [incidents, setIncidents] = useState<Incident[]>(DEMO_INCIDENTS)
  const [total, setTotal] = useState<number>(DEMO_INCIDENTS.length)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  // Create incident modal
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newSeverity, setNewSeverity] = useState<'Critical' | 'High' | 'Medium' | 'Low'>('High')
  const [newAssignedTo, setNewAssignedTo] = useState('Alex Morgan')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  // Incident detail modal
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null)
  const [statusUpdatingId, setStatusUpdatingId] = useState<string | null>(null)

  const fetchIncidents = useCallback(async () => {
    if (!isLive) {
      let filtered = [...DEMO_INCIDENTS]
      if (search) {
        const q = search.toLowerCase()
        filtered = filtered.filter(
          (i) =>
            i.id.toLowerCase().includes(q) ||
            i.title.toLowerCase().includes(q) ||
            (i.description && i.description.toLowerCase().includes(q)) ||
            (i.assigned_to && i.assigned_to.toLowerCase().includes(q))
        )
      }
      if (severity) filtered = filtered.filter((i) => i.severity === severity)
      if (statusFilter) filtered = filtered.filter((i) => i.status === statusFilter)
      setTotal(filtered.length)
      setIncidents(filtered)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const params: IncidentQueryParams = {
        search: search || undefined,
        severity: severity || undefined,
        status: statusFilter || undefined,
      }
      const res = await incidentsService.getIncidents(params)
      setIncidents(res.items)
      setTotal(res.total)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve incidents from backend.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [isLive, search, severity, statusFilter])

  useEffect(() => {
    fetchIncidents()
  }, [fetchIncidents])

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    setCreating(true)
    setCreateError(null)

    if (!isLive) {
      const mockNew: Incident = {
        id: `INC-${Math.floor(2000 + Math.random() * 900)}`,
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
        severity: newSeverity,
        status: 'Open',
        assigned_to: newAssignedTo,
        alert_ids: [],
        event_ids: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      setIncidents([mockNew, ...incidents])
      setTotal((t) => t + 1)
      setCreateModalOpen(false)
      setNewTitle('')
      setNewDesc('')
      setCreating(false)
      return
    }

    try {
      const created = await incidentsService.createIncident({
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
        severity: newSeverity,
        assigned_to: newAssignedTo,
      })
      setIncidents([created, ...incidents])
      setTotal((t) => t + 1)
      setCreateModalOpen(false)
      setNewTitle('')
      setNewDesc('')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create incident.'
      setCreateError(msg)
    } finally {
      setCreating(false)
    }
  }

  const handleStatusTransition = async (incident: Incident, nextStatus: IncidentStatus) => {
    setStatusUpdatingId(incident.id)

    if (!isLive) {
      setIncidents((prev) =>
        prev.map((i) => (i.id === incident.id ? { ...i, status: nextStatus, updated_at: new Date().toISOString() } : i))
      )
      if (selectedIncident && selectedIncident.id === incident.id) {
        setSelectedIncident({ ...selectedIncident, status: nextStatus })
      }
      setStatusUpdatingId(null)
      return
    }

    try {
      const updated = await incidentsService.updateIncident(incident.id, { status: nextStatus })
      setIncidents((prev) => prev.map((i) => (i.id === incident.id ? updated : i)))
      if (selectedIncident && selectedIncident.id === incident.id) {
        setSelectedIncident(updated)
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Status update failed.')
    } finally {
      setStatusUpdatingId(null)
    }
  }

  return (
    <>
      <div className='page-header'>
        <div>
          <div className='eyebrow'>SECURITY RESPONSE</div>
          <h1>Incident response</h1>
          <p>
            {isLive
              ? `Tracking ${total} active incident cases in backend database.`
              : 'Tracking demo incidents (backend or database offline).'}
          </p>
        </div>
        <div className='header-actions'>
          <button className='btn secondary' onClick={fetchIncidents} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
          </button>
          <button className='btn' onClick={() => setCreateModalOpen(true)}>
            <Plus size={15} /> New incident
          </button>
        </div>
      </div>

      {error && (
        <div className='connection-banner error'>
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button className='btn secondary' onClick={fetchIncidents}>
            Retry
          </button>
        </div>
      )}

      <div className='toolbar' style={{ marginBottom: '18px' }}>
        <div className='input-wrap'>
          <Search size={16} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder='Search incidents by title, ID, or assigned engineer...'
            aria-label='Search incidents'
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              style={{ background: 'none', border: 0, color: 'var(--muted)', cursor: 'pointer' }}
            >
              <X size={14} />
            </button>
          )}
        </div>

        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
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
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label='Filter by status'
        >
          <option value=''>All statuses</option>
          <option value='Open'>Open</option>
          <option value='Investigating'>Investigating</option>
          <option value='Contained'>Contained</option>
          <option value='Resolved'>Resolved</option>
          <option value='Closed'>Closed</option>
        </select>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
          <RefreshCw size={22} className='spin' style={{ margin: '0 auto 10px', display: 'block' }} />
          Loading incidents...
        </div>
      ) : incidents.length === 0 ? (
        <div className='card empty-state'>
          <Target size={32} />
          <h3>No incidents found</h3>
          <p>No incident response cases match the selected filters.</p>
        </div>
      ) : (
        <div className='incident-grid'>
          {incidents.map((x) => (
            <div
              className='card incident-card'
              key={x.id}
              onClick={() => setSelectedIncident(x)}
              style={{ cursor: 'pointer' }}
            >
              <div className='incident-top'>
                <span>{x.id}</span>
                <Badge>{x.severity}</Badge>
              </div>
              <h3>{x.title}</h3>
              <p
                style={{
                  fontSize: '11px',
                  color: 'var(--muted)',
                  margin: '-10px 0 16px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {x.description || 'No description provided.'}
              </p>
              <div className='incident-status'>
                <CircleDot size={13} />
                <span>{x.status}</span>
              </div>
              <div className='incident-bottom'>
                <div className='avatar small'>
                  {x.assigned_to
                    ? x.assigned_to
                        .split(' ')
                        .map((w) => w[0])
                        .join('')
                        .toUpperCase()
                        .slice(0, 2)
                    : 'AM'}
                </div>
                <span>Assigned to {x.assigned_to || 'Unassigned'}</span>
                <MoreHorizontal size={18} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Incident Modal */}
      {createModalOpen && (
        <div className='modal-backdrop' onClick={() => setCreateModalOpen(false)}>
          <div className='modal-card' onClick={(e) => e.stopPropagation()} style={{ maxWidth: '540px' }}>
            <div className='modal-header'>
              <h2>Create Security Incident Case</h2>
              <button className='icon-btn' onClick={() => setCreateModalOpen(false)}>
                <X size={17} />
              </button>
            </div>
            <form onSubmit={handleCreateSubmit}>
              <div className='modal-body'>
                <div style={{ marginBottom: '14px' }}>
                  <label style={{ display: 'block', fontSize: '11px', color: 'var(--muted)', marginBottom: '5px' }}>
                    Incident Title *
                  </label>
                  <input
                    type='text'
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder='e.g. Distributed Credential Stuffing Campaign'
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

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--muted)', marginBottom: '5px' }}>
                      Severity
                    </label>
                    <select
                      value={newSeverity}
                      onChange={(e) => setNewSeverity(e.target.value as any)}
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
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--muted)', marginBottom: '5px' }}>
                      Assigned Lead
                    </label>
                    <input
                      type='text'
                      value={newAssignedTo}
                      onChange={(e) => setNewAssignedTo(e.target.value)}
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

                <div style={{ marginBottom: '14px' }}>
                  <label style={{ display: 'block', fontSize: '11px', color: 'var(--muted)', marginBottom: '5px' }}>
                    Description & Initial Scope
                  </label>
                  <textarea
                    rows={4}
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    placeholder='Scope, impacted services, and immediate perimeter response...'
                    style={{
                      width: '100%',
                      background: '#091522',
                      border: '1px solid var(--line)',
                      borderRadius: '6px',
                      color: 'var(--text)',
                      padding: '8px 10px',
                      fontSize: '12px',
                      fontFamily: 'inherit',
                    }}
                  />
                </div>

                {createError && (
                  <div className='connection-banner error'>
                    <AlertTriangle size={15} />
                    <span>{createError}</span>
                  </div>
                )}
              </div>
              <div className='modal-footer'>
                <button
                  type='button'
                  className='btn secondary'
                  onClick={() => setCreateModalOpen(false)}
                  disabled={creating}
                >
                  Cancel
                </button>
                <button type='submit' className='btn' disabled={creating || !newTitle.trim()}>
                  {creating ? (
                    <>
                      <RefreshCw size={13} className='spin' /> Creating...
                    </>
                  ) : (
                    'Create Incident'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Incident Details & Workflow Modal */}
      {selectedIncident && (
        <div className='modal-backdrop' onClick={() => setSelectedIncident(null)}>
          <div className='modal-card' onClick={(e) => e.stopPropagation()}>
            <div className='modal-header'>
              <h2>Incident Investigation: {selectedIncident.id}</h2>
              <button className='icon-btn' onClick={() => setSelectedIncident(null)}>
                <X size={17} />
              </button>
            </div>
            <div className='modal-body'>
              <div className='detail-grid'>
                <div className='detail-field'>
                  <label>Severity</label>
                  <span>
                    <Badge>{selectedIncident.severity}</Badge>
                  </span>
                </div>
                <div className='detail-field'>
                  <label>Current Status</label>
                  <span>
                    <Badge>{selectedIncident.status}</Badge>
                  </span>
                </div>
                <div className='detail-field' style={{ gridColumn: 'span 2' }}>
                  <label>Incident Title</label>
                  <b style={{ fontSize: '14px', color: 'var(--text)' }}>{selectedIncident.title}</b>
                </div>
                <div className='detail-field' style={{ gridColumn: 'span 2' }}>
                  <label>Description</label>
                  <span>{selectedIncident.description || 'No description provided.'}</span>
                </div>
                <div className='detail-field'>
                  <label>Assigned Lead</label>
                  <span>{selectedIncident.assigned_to || 'Unassigned'}</span>
                </div>
                <div className='detail-field'>
                  <label>Created Timestamp</label>
                  <span>{new Date(selectedIncident.created_at).toLocaleString()}</span>
                </div>
                {selectedIncident.investigation_notes && (
                  <div className='detail-field' style={{ gridColumn: 'span 2' }}>
                    <label>Investigation Notes</label>
                    <div style={{ padding: '8px', background: '#091522', borderRadius: '4px' }}>
                      {selectedIncident.investigation_notes}
                    </div>
                  </div>
                )}
                {selectedIncident.resolution_summary && (
                  <div className='detail-field' style={{ gridColumn: 'span 2' }}>
                    <label>Resolution Summary</label>
                    <div style={{ padding: '8px', background: '#0e2920', color: '#8de8c6', borderRadius: '4px' }}>
                      {selectedIncident.resolution_summary}
                    </div>
                  </div>
                )}
              </div>

              {/* Status Transition Actions */}
              <div style={{ marginTop: '16px', borderTop: '1px solid var(--line)', paddingTop: '14px' }}>
                <label style={{ display: 'block', fontSize: '10px', color: 'var(--muted)', marginBottom: '8px' }}>
                  WORKFLOW STATUS ACTIONS
                </label>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {selectedIncident.status === 'Open' && (
                    <button
                      className='btn secondary'
                      onClick={() => handleStatusTransition(selectedIncident, 'Investigating')}
                      disabled={statusUpdatingId === selectedIncident.id}
                    >
                      Begin Investigation
                    </button>
                  )}
                  {selectedIncident.status === 'Investigating' && (
                    <button
                      className='btn secondary'
                      onClick={() => handleStatusTransition(selectedIncident, 'Contained')}
                      disabled={statusUpdatingId === selectedIncident.id}
                    >
                      Mark as Contained
                    </button>
                  )}
                  {selectedIncident.status !== 'Resolved' && selectedIncident.status !== 'Closed' && (
                    <button
                      className='btn'
                      onClick={() => handleStatusTransition(selectedIncident, 'Resolved')}
                      disabled={statusUpdatingId === selectedIncident.id}
                    >
                      Resolve Incident
                    </button>
                  )}
                  {selectedIncident.status === 'Resolved' && (
                    <button
                      className='btn secondary'
                      onClick={() => handleStatusTransition(selectedIncident, 'Closed')}
                      disabled={statusUpdatingId === selectedIncident.id}
                    >
                      Close Case
                    </button>
                  )}
                </div>
              </div>
            </div>
            <div className='modal-footer'>
              <button className='btn secondary' onClick={() => setSelectedIncident(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
