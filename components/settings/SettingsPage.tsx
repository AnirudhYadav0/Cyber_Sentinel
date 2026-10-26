'use client'

import React, { useState } from 'react'
import { CheckCircle2, RefreshCw, Shield, AlertTriangle } from 'lucide-react'
import { useConnection } from '../../lib/context/ConnectionContext'
import { API_BASE_URL } from '../../lib/api'

function CardTitle({ title }: { title: string }) {
  return (
    <div className='card-title'>
      <div>
        <h2>{title}</h2>
      </div>
    </div>
  )
}

export function SettingsPage() {
  const { status, isLive, demoMode, setDemoMode, health, readiness, checkConnection } = useConnection()
  const [checking, setChecking] = useState(false)
  const [savedBanner, setSavedBanner] = useState(false)

  const handleCheck = async () => {
    setChecking(true)
    await checkConnection()
    setChecking(false)
  }

  const handleSave = () => {
    setSavedBanner(true)
    setTimeout(() => setSavedBanner(false), 3000)
  }

  return (
    <>
      <div className='page-header'>
        <div>
          <div className='eyebrow'>SYSTEM CONFIGURATION</div>
          <h1>Settings</h1>
          <p>Manage workspace preferences, API connections, and demonstration modes.</p>
        </div>
      </div>

      {savedBanner && (
        <div className='connection-banner info'>
          <CheckCircle2 size={16} />
          <span>Workspace preferences saved successfully.</span>
        </div>
      )}

      <div className='settings-grid'>
        <section className='card settings-card'>
          <CardTitle title='Backend API Connection' />
          <div style={{ margin: '14px 0', fontSize: '11px', color: 'var(--muted)' }}>
            <div>
              <b>Configured Base URL:</b>{' '}
              <code style={{ color: 'var(--cyan)' }}>{API_BASE_URL}</code>
            </div>
            <div style={{ marginTop: '6px' }}>
              <b>Status:</b>{' '}
              <span
                style={{
                  color:
                    status === 'connected'
                      ? 'var(--green)'
                      : status === 'database_unavailable'
                      ? 'var(--amber)'
                      : 'var(--red)',
                  fontWeight: 'bold',
                  textTransform: 'uppercase',
                }}
              >
                {status.replace('_', ' ')}
              </span>
            </div>
            {health && (
              <div style={{ marginTop: '6px' }}>
                <b>API Version:</b> {health.version} ({health.environment})
              </div>
            )}
            {readiness && (
              <div style={{ marginTop: '6px' }}>
                <b>Database:</b> {readiness.database}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
            <button className='btn secondary' onClick={handleCheck} disabled={checking}>
              <RefreshCw size={13} className={checking ? 'spin' : ''} />
              {checking ? 'Checking...' : 'Check Connection'}
            </button>
            <button
              className='btn secondary'
              onClick={() => setDemoMode(!demoMode)}
              title='Toggle between live backend and local demo mode'
            >
              {demoMode ? 'Disable Demo Mode' : 'Force Demo Mode'}
            </button>
          </div>
        </section>

        <section className='card settings-card'>
          <CardTitle title='Workspace Profile' />
          <label>
            Workspace name
            <input defaultValue='CyberSentinel Command Center' />
          </label>
          <label>
            Timezone
            <select defaultValue='UTC'>
              <option value='UTC'>UTC</option>
              <option value='America/New_York'>America/New_York (EST)</option>
              <option value='Europe/London'>Europe/London (GMT)</option>
              <option value='Asia/Tokyo'>Asia/Tokyo (JST)</option>
            </select>
          </label>
          <button className='btn' onClick={handleSave}>
            Save changes
          </button>
        </section>

        <section className='card settings-card' style={{ gridColumn: 'span 2' }}>
          <CardTitle title='SOC Notifications & Subscriptions' />
          {['Critical threat alerts', 'Incident case assignments', 'Weekly security digest and audit report'].map(
            (x, i) => (
              <label className='check-row' key={x}>
                <span>
                  {x}
                  <small>Receive automated notification broadcasts for {x.toLowerCase()}.</small>
                </span>
                <input type='checkbox' defaultChecked={i < 2} />
              </label>
            )
          )}
        </section>
      </div>
    </>
  )
}
