import { apiRequest } from '../client'
import {
  Alert,
  AlertUpdatePayload,
  PaginatedResponse,
} from '../types'

export interface AlertQueryParams {
  page?: number
  page_size?: number
  search?: string
  severity?: string
  status?: string
  rule_id?: string
  start_time?: string
  end_time?: string
}

export const alertsService = {
  async getAlerts(
    params: AlertQueryParams = {},
    signal?: AbortSignal
  ): Promise<PaginatedResponse<Alert>> {
    const cleanedParams: Record<string, unknown> = {}
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        cleanedParams[key] = val
      }
    })

    const res = await apiRequest<PaginatedResponse<Alert>>({
      method: 'GET',
      url: '/api/alerts',
      params: cleanedParams,
      signal,
    })

    const items = res.items || []
    return {
      items,
      total: res.total ?? items.length,
      page: res.page ?? 1,
      page_size: res.page_size ?? items.length,
    }
  },

  async getAlertById(alertId: string, signal?: AbortSignal): Promise<Alert> {
    return apiRequest<Alert>({
      method: 'GET',
      url: `/api/alerts/${encodeURIComponent(alertId)}`,
      signal,
    })
  },

  async updateAlert(
    alertId: string,
    payload: AlertUpdatePayload,
    signal?: AbortSignal
  ): Promise<Alert> {
    return apiRequest<Alert>({
      method: 'PATCH',
      url: `/api/alerts/${encodeURIComponent(alertId)}`,
      data: payload,
      signal,
    })
  },
}
