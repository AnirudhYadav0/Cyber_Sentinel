import { apiClient, apiRequest } from '../client'
import { SystemHealth, SystemReadiness } from '../types'

export const systemService = {
  async getHealth(signal?: AbortSignal): Promise<SystemHealth> {
    return apiRequest<SystemHealth>({
      method: 'GET',
      url: '/api/health',
      signal,
    })
  },

  async getReadiness(signal?: AbortSignal): Promise<SystemReadiness> {
    try {
      const response = await apiClient.get<SystemReadiness>('/api/ready', {
        signal,
        validateStatus: (status) => status === 200 || status === 503,
      })
      return response.data
    } catch (err: unknown) {
      return {
        status: 'degraded',
        ready: false,
        database: 'disconnected',
        timestamp: new Date().toISOString(),
        message: err instanceof Error ? err.message : 'Database check failed',
      }
    }
  },
}
