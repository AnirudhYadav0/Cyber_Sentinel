'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Activity,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Download,
  FileJson,
  Filter,
  RefreshCw,
  Search,
  UploadCloud,
  X,
} from 'lucide-react'
import {
  eventsService,
  SecurityEvent,
  EventQueryParams,
  DEMO_EVENTS,
  IngestionResponse,
} from '../../lib/api'
import { useConnection } from '../../lib/context/ConnectionContext'

function Badge({ children }: { children: string }) {
  return <span className={`badge ${children.toLowerCase()}`}>{children}</span>
}

export function EventsPage() {
  const { isLive } = useConnection()
  const [events, setEvents] = useState<SecurityEvent[]>(DEMO_EVENTS)
  const [total, setTotal] = useState<number>(DEMO_EVENTS.length)
  const [page, setPage] = useState<number>(1)
  const pageSize = 15

  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState('')
  const [eventType, setEventType] = useState('')
  const [outcome, setOutcome] = useState('')
  const [sortBy, setSortBy] = useState<'timestamp' | 'severity' | 'event_type' | 'source' | 'outcome'>('timestamp')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Drawer / modal states
  const [selectedEvent, setSelectedEvent] = useState<SecurityEvent | null>(null)
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<IngestionResponse | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchEvents = useCallback(async () => {
    if (!isLive) {
      let filtered = [...DEMO_EVENTS]
      if (search) {
        const q = search.toLowerCase()
        filtered = filtered.filter(
          (e) =>
            e.id.toLowerCase().includes(q) ||
            e.event_type.toLowerCase().includes(q) ||
            (e.description && e.description.toLowerCase().includes(q)) ||
            (e.source && e.source.toLowerCase().includes(q)) ||
            (e.username && e.username.toLowerCase().includes(q))
        )
      }
      if (severity) filtered = filtered.filter((e) => e.severity === severity)
      if (eventType) filtered = filtered.filter((e) => e.event_type === eventType)
      if (outcome) filtered = filtered.filter((e) => e.outcome === outcome)
      setTotal(filtered.length)
      setEvents(filtered.slice((page - 1) * pageSize, page * pageSize))
      return
    }

    setLoading(true)
    setError(null)
    try {
      const params: EventQueryParams = {
        page,
        page_size: pageSize,
        search: search || undefined,
        severity: severity || undefined,
        event_type: eventType || undefined,
        outcome: outcome || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
      }
      const res = await eventsService.getEvents(params)
      setEvents(res.items)
      setTotal(res.total)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve security events from backend.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [isLive, page, pageSize, search, severity, eventType, outcome, sortBy, sortDir])

  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const handleExportCSV = () => {
    if (events.length === 0) return
    const headers = ['ID', 'Timestamp', 'Event Type', 'Severity', 'Source', 'Source IP', 'User', 'Outcome', 'Description']
    const rows = events.map((e) => [
      `"${e.id}"`,
      `"${e.timestamp}"`,
      `"${e.event_type}"`,
      `"${e.severity}"`,
      `"${e.source || ''}"`,
      `"${e.source_ip || ''}"`,
      `"${e.username || ''}"`,
      `"${e.outcome || ''}"`,
      `"${(e.description || '').replace(/"/g, '""')}"`,
    ])
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `security_events_page_${page}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!uploadFile) return
    setUploading(true)
    setUploadError(null)
    setUploadResult(null)

    if (!isLive) {
      setTimeout(() => {
        setUploadResult({
          created: 5,
          rejected: 0,
          duplicates: 0,
          errors: [],
        })
        setUploading(false)
        setUploadFile(null)
      }, 700)
      return
    }

    try {
      const res = await eventsService.uploadLogsFile(uploadFile)
      setUploadResult(res)
      setUploadFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      // Refresh events
      fetchEvents()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'File upload failed.'
      setUploadError(msg)
    } finally {
      setUploading(false)
    }
  }

  return (
    <>
      <div className='page-header'>
        <div>
          <div className='eyebrow'>EVENT STREAM</div>
          <h1>Security events</h1>
          <p>
            {isLive
              ? `Displaying ${total} event records from active database.`
              : 'Displaying demo events (backend or database unavailable).'}
          </p>
        </div>
        <div className='header-actions'>
          <button className='btn secondary' onClick={() => setUploadModalOpen(true)}>
            <UploadCloud size={14} /> Upload logs
          </button>
          <button className='btn secondary' onClick={handleExportCSV}>
            <Download size={14} /> Export CSV
          </button>
          <button className='btn secondary' onClick={fetchEvents} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      {error && (
        <div className='connection-banner error'>
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button className='btn secondary' onClick={fetchEvents}>
            Retry
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
              placeholder='Search events, sources, or IDs...'
              aria-label='Search events'
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
            <option value='Info'>Info</option>
          </select>

          <select
            value={eventType}
            onChange={(e) => {
              setEventType(e.target.value)
              setPage(1)
            }}
            aria-label='Filter by event type'
          >
            <option value=''>All event types</option>
            <option value='auth.login_failed'>auth.login_failed</option>
            <option value='auth.login_success'>auth.login_success</option>
            <option value='auth.access_denied'>auth.access_denied</option>
            <option value='api.request'>api.request</option>
            <option value='privilege.action'>privilege.action</option>
            <option value='network.anomaly'>network.anomaly</option>
          </select>

          <select
            value={outcome}
            onChange={(e) => {
              setOutcome(e.target.value)
              setPage(1)
            }}
            aria-label='Filter by outcome'
          >
            <option value=''>All outcomes</option>
            <option value='success'>success</option>
            <option value='failure'>failure</option>
            <option value='denied'>denied</option>
          </select>

          <select
            value={`${sortBy}-${sortDir}`}
            onChange={(e) => {
              const [f, d] = e.target.value.split('-')
              setSortBy(f as any)
              setSortDir(d as any)
              setPage(1)
            }}
            aria-label='Sort order'
          >
            <option value='timestamp-desc'>Newest first</option>
            <option value='timestamp-asc'>Oldest first</option>
            <option value='severity-desc'>Severity (desc)</option>
            <option value='severity-asc'>Severity (asc)</option>
          </select>
        </div>

        <div className='table-wrap'>
          <table>
            <thead>
              <tr>
                <th>EVENT</th>
                <th>SOURCE</th>
                <th>USER / IP</th>
                <th>TIMESTAMP</th>
                <th>OUTCOME</th>
                <th>SEVERITY</th>
                <th>DETAILS</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '36px', color: 'var(--muted)' }}>
                    <RefreshCw size={18} className='spin' style={{ margin: '0 auto 8px', display: 'block' }} />
                    Loading events...
                  </td>
                </tr>
              ) : events.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <div className='empty-state'>
                      <Activity size={28} />
                      <h3>No events found</h3>
                      <p>Try adjusting your search query or filters.</p>
                      <button
                        className='btn secondary'
                        onClick={() => {
                          setSearch('')
                          setSeverity('')
                          setEventType('')
                          setOutcome('')
                          setPage(1)
                        }}
                      >
                        Reset filters
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                events.map((e) => (
                  <tr
                    key={e.id}
                    onClick={() => setSelectedEvent(e)}
                    style={{ cursor: 'pointer' }}
                    title='Click to view raw JSON & details'
                  >
                    <td>
                      <b>{e.event_type}</b>
                      <small>{e.id}</small>
                    </td>
                    <td>{e.source || 'system'}</td>
                    <td>
                      <b>{e.username || 'unknown'}</b>
                      <small>{e.source_ip || '-'}</small>
                    </td>
                    <td>
                      <small>{new Date(e.timestamp).toLocaleString()}</small>
                    </td>
                    <td>
                      <span style={{ textTransform: 'capitalize' }}>{e.outcome || 'unknown'}</span>
                    </td>
                    <td>
                      <Badge>{e.severity}</Badge>
                    </td>
                    <td>
                      <button
                        className='btn secondary'
                        style={{ padding: '4px 8px', fontSize: '10px' }}
                        onClick={(ev) => {
                          ev.stopPropagation()
                          setSelectedEvent(e)
                        }}
                      >
                        <FileJson size={12} /> JSON
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className='pagination-bar'>
          <span>
            Showing {events.length > 0 ? (page - 1) * pageSize + 1 : 0} to{' '}
            {Math.min(page * pageSize, total)} of {total} records
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

      {/* Event Details & Raw JSON Modal */}
      {selectedEvent && (
        <div className='modal-backdrop' onClick={() => setSelectedEvent(null)}>
          <div className='modal-card' onClick={(e) => e.stopPropagation()}>
            <div className='modal-header'>
              <h2>Event Investigation: {selectedEvent.id}</h2>
              <button
                className='icon-btn'
                onClick={() => setSelectedEvent(null)}
                aria-label='Close drawer'
              >
                <X size={17} />
              </button>
            </div>
            <div className='modal-body'>
              <div className='detail-grid'>
                <div className='detail-field'>
                  <label>Event Type</label>
                  <span>{selectedEvent.event_type}</span>
                </div>
                <div className='detail-field'>
                  <label>Severity</label>
                  <span>
                    <Badge>{selectedEvent.severity}</Badge>
                  </span>
                </div>
                <div className='detail-field'>
                  <label>Source</label>
                  <span>{selectedEvent.source || 'system'}</span>
                </div>
                <div className='detail-field'>
                  <label>Source IP</label>
                  <span>{selectedEvent.source_ip || 'N/A'}</span>
                </div>
                <div className='detail-field'>
                  <label>Username</label>
                  <span>{selectedEvent.username || 'unknown'}</span>
                </div>
                <div className='detail-field'>
                  <label>Outcome</label>
                  <span style={{ textTransform: 'capitalize' }}>{selectedEvent.outcome || 'unknown'}</span>
                </div>
                <div className='detail-field' style={{ gridColumn: 'span 2' }}>
                  <label>Description</label>
                  <span>{selectedEvent.description || 'No description provided.'}</span>
                </div>
                <div className='detail-field' style={{ gridColumn: 'span 2' }}>
                  <label>Timestamp</label>
                  <span>{new Date(selectedEvent.timestamp).toUTCString()}</span>
                </div>
              </div>

              <div style={{ marginTop: '16px' }}>
                <label style={{ display: 'block', fontSize: '10px', color: 'var(--muted)', marginBottom: '6px' }}>
                  RAW TELEMETRY PAYLOAD (JSON)
                </label>
                <pre className='json-viewer'>
                  {JSON.stringify(selectedEvent, null, 2)}
                </pre>
              </div>
            </div>
            <div className='modal-footer'>
              <button className='btn secondary' onClick={() => setSelectedEvent(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Logs File Modal */}
      {uploadModalOpen && (
        <div className='modal-backdrop' onClick={() => setUploadModalOpen(false)}>
          <div className='modal-card' onClick={(e) => e.stopPropagation()}>
            <div className='modal-header'>
              <h2>Upload Security Telemetry</h2>
              <button className='icon-btn' onClick={() => setUploadModalOpen(false)} aria-label='Close'>
                <X size={17} />
              </button>
            </div>
            <form onSubmit={handleUploadSubmit}>
              <div className='modal-body'>
                <p style={{ color: 'var(--muted)', marginBottom: '16px' }}>
                  Select a <code>.json</code>, <code>.jsonl</code>, <code>.ndjson</code>, or <code>.log</code> file containing
                  normalized security telemetry to ingest into MongoDB.
                </p>

                <div
                  style={{
                    border: '2px dashed var(--line)',
                    padding: '24px',
                    borderRadius: '8px',
                    textAlign: 'center',
                    background: '#091522',
                  }}
                >
                  <input
                    type='file'
                    ref={fileInputRef}
                    accept='.json,.jsonl,.ndjson,.log'
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    style={{ display: 'none' }}
                    id='log-file-input'
                  />
                  <label htmlFor='log-file-input' style={{ cursor: 'pointer' }}>
                    <UploadCloud size={32} style={{ color: 'var(--cyan)', margin: '0 auto 8px', display: 'block' }} />
                    <b style={{ color: 'var(--text)' }}>
                      {uploadFile ? uploadFile.name : 'Choose log file or click to browse'}
                    </b>
                    <small style={{ display: 'block', color: 'var(--muted)', marginTop: '4px' }}>
                      Max file size: 10MB. Maximum 5,000 records per upload batch.
                    </small>
                  </label>
                </div>

                {uploadResult && (
                  <div
                    style={{
                      marginTop: '16px',
                      padding: '12px',
                      background: '#0e2b26',
                      border: '1px solid #23655b',
                      borderRadius: '6px',
                      color: 'var(--text)',
                      fontSize: '11px',
                    }}
                  >
                    <b>Ingestion Complete:</b>
                    <div style={{ marginTop: '4px' }}>
                      ✓ Created: {uploadResult.created} record(s)
                      <br />
                      ✓ Duplicates skipped: {uploadResult.duplicates}
                      <br />
                      {uploadResult.rejected > 0 && <span>⚠ Rejected: {uploadResult.rejected} record(s)</span>}
                    </div>
                  </div>
                )}

                {uploadError && (
                  <div className='connection-banner error' style={{ marginTop: '16px' }}>
                    <AlertTriangle size={15} />
                    <span>{uploadError}</span>
                  </div>
                )}
              </div>
              <div className='modal-footer'>
                <button
                  type='button'
                  className='btn secondary'
                  onClick={() => setUploadModalOpen(false)}
                  disabled={uploading}
                >
                  Cancel
                </button>
                <button type='submit' className='btn' disabled={!uploadFile || uploading}>
                  {uploading ? (
                    <>
                      <RefreshCw size={13} className='spin' /> Ingesting...
                    </>
                  ) : (
                    'Upload and Ingest'
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
