import { apiRequest } from '../client'
import {
  Incident,
  IncidentCreatePayload,
  IncidentUpdatePayload,
  PaginatedResponse,
} from '../types'

export interface IncidentQueryParams {
  page?: number
  page_size?: number
  search?: string
  severity?: string
  status?: string
  assigned_to?: string
}

export const incidentsService = {
  async getIncidents(
    params: IncidentQueryParams = {},
    signal?: AbortSignal
  ): Promise<PaginatedResponse<Incident>> {
    const cleanedParams: Record<string, unknown> = {}
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        cleanedParams[key] = val
      }
    })

    const res = await apiRequest<PaginatedResponse<Incident>>({
      method: 'GET',
      url: '/api/incidents',
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

  async getIncidentById(incidentId: string, signal?: AbortSignal): Promise<Incident> {
    return apiRequest<Incident>({
      method: 'GET',
      url: `/api/incidents/${encodeURIComponent(incidentId)}`,
      signal,
    })
  },

  async createIncident(
    payload: IncidentCreatePayload,
    signal?: AbortSignal
  ): Promise<Incident> {
    return apiRequest<Incident>({
      method: 'POST',
      url: '/api/incidents',
      data: payload,
      signal,
    })
  },

  async updateIncident(
    incidentId: string,
    payload: IncidentUpdatePayload,
    signal?: AbortSignal
  ): Promise<Incident> {
    return apiRequest<Incident>({
      method: 'PATCH',
      url: `/api/incidents/${encodeURIComponent(incidentId)}`,
      data: payload,
      signal,
    })
  },
}
