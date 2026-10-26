import { apiRequest } from '../client'
import {
  DashboardSummary,
  TrendsResponse,
  SeverityResponse,
  SourceDistributionResponse,
} from '../types'

export const analyticsService = {
  async getSummary(signal?: AbortSignal): Promise<DashboardSummary> {
    return apiRequest<DashboardSummary>({
      method: 'GET',
      url: '/api/analytics/summary',
      signal,
    })
  },

  async getTrends(range: '24h' | '7d' | '30d' = '24h', signal?: AbortSignal): Promise<TrendsResponse> {
    return apiRequest<TrendsResponse>({
      method: 'GET',
      url: '/api/analytics/trends',
      params: { range },
      signal,
    })
  },

  async getSeverity(signal?: AbortSignal): Promise<SeverityResponse> {
    return apiRequest<SeverityResponse>({
      method: 'GET',
      url: '/api/analytics/severity',
      signal,
    })
  },

  async getSources(range: '24h' | '7d' | '30d' = '7d', signal?: AbortSignal): Promise<SourceDistributionResponse> {
    return apiRequest<SourceDistributionResponse>({
      method: 'GET',
      url: '/api/analytics/sources',
      params: { range },
      signal,
    })
  },
}
