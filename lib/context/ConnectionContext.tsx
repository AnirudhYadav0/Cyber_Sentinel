'use client'

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import {
  ConnectionStatus,
  SystemHealth,
  SystemReadiness,
  systemService,
} from '../api'

interface ConnectionContextValue {
  status: ConnectionStatus
  isLive: boolean
  isDegraded: boolean
  isOffline: boolean
  demoMode: boolean
  setDemoMode: (val: boolean) => void
  lastChecked: Date | null
  health: SystemHealth | null
  readiness: SystemReadiness | null
  checkConnection: () => Promise<void>
  error: string | null
}

const ConnectionContext = createContext<ConnectionContextValue>({
  status: 'connecting',
  isLive: false,
  isDegraded: false,
  isOffline: false,
  demoMode: false,
  setDemoMode: () => {},
  lastChecked: null,
  health: null,
  readiness: null,
  checkConnection: async () => {},
  error: null,
})

export function ConnectionProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [readiness, setReadiness] = useState<SystemReadiness | null>(null)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [demoMode, setDemoModeState] = useState<boolean>(false)

  const checkConnection = useCallback(async () => {
    setStatus('connecting')
    setError(null)

    try {
      // 1. Check health
      const h = await systemService.getHealth()
      setHealth(h)

      // 2. Check readiness
      const r = await systemService.getReadiness()
      setReadiness(r)
      setLastChecked(new Date())

      if (!r.ready) {
        setStatus('database_unavailable')
        setError(r.message || 'Database is not connected. Configure MONGODB_URI in backend .env.')
      } else {
        setStatus(demoMode ? 'demo_mode' : 'connected')
      }
    } catch (err: unknown) {
      setHealth(null)
      setReadiness(null)
      setLastChecked(new Date())
      setStatus('backend_unavailable')
      const msg = err instanceof Error ? err.message : 'Could not contact CyberSentinel backend'
      setError(msg)
    }
  }, [demoMode])

  useEffect(() => {
    checkConnection()
  }, [checkConnection])

  const setDemoMode = (val: boolean) => {
    setDemoModeState(val)
    if (val) {
      setStatus('demo_mode')
    } else {
      checkConnection()
    }
  }

  const isLive = status === 'connected'
  const isDegraded = status === 'database_unavailable'
  const isOffline = status === 'backend_unavailable'

  return (
    <ConnectionContext.Provider
      value={{
        status,
        isLive,
        isDegraded,
        isOffline,
        demoMode,
        setDemoMode,
        lastChecked,
        health,
        readiness,
        checkConnection,
        error,
      }}
    >
      {children}
    </ConnectionContext.Provider>
  )
}

export function useConnection() {
  return useContext(ConnectionContext)
}
