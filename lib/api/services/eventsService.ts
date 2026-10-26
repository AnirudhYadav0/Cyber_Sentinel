import { apiRequest, apiClient } from '../client'
import {
  SecurityEvent,
  PaginatedResponse,
  IngestionResponse,
} from '../types'

export interface EventQueryParams {
  page?: number
  page_size?: number
  search?: string
  event_type?: string
  severity?: string
  outcome?: string
  start_time?: string
  end_time?: string
  sort_by?: 'timestamp' | 'severity' | 'event_type' | 'source' | 'outcome'
  sort_dir?: 'asc' | 'desc'
}

export const eventsService = {
  async getEvents(
    params: EventQueryParams = {},
    signal?: AbortSignal
  ): Promise<PaginatedResponse<SecurityEvent>> {
    const cleanedParams: Record<string, unknown> = {}
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        cleanedParams[key] = val
      }
    })

    const res = await apiRequest<PaginatedResponse<SecurityEvent>>({
      method: 'GET',
      url: '/api/events',
      params: cleanedParams,
      signal,
    })

    // Normalize items array (in case backend provides events or items)
    const items = res.items || res.events || []
    return {
      items,
      events: items,
      total: res.total ?? items.length,
      page: res.page ?? 1,
      page_size: res.page_size ?? items.length,
    }
  },

  async getEventById(eventId: string, signal?: AbortSignal): Promise<SecurityEvent> {
    return apiRequest<SecurityEvent>({
      method: 'GET',
      url: `/api/events/${encodeURIComponent(eventId)}`,
      signal,
    })
  },

  async uploadLogsFile(file: File, signal?: AbortSignal): Promise<IngestionResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post<IngestionResponse>('/api/events/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      signal,
    })
    return response.data
  },

  async ingestEvents(
    events: Partial<SecurityEvent>[],
    signal?: AbortSignal
  ): Promise<IngestionResponse> {
    return apiRequest<IngestionResponse>({
      method: 'POST',
      url: '/api/events/ingest',
      data: events,
      signal,
    })
  },
}
