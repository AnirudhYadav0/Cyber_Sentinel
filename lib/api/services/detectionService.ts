import { apiRequest } from '../client'
import {
  DetectionRule,
  RuleUpdatePayload,
  DetectionRunSummary,
  PaginatedResponse,
} from '../types'

export interface DetectionRunRequest {
  lookback_minutes?: number
  rule_ids?: string[]
}

export const detectionService = {
  async getRules(signal?: AbortSignal): Promise<DetectionRule[]> {
    return apiRequest<DetectionRule[]>({
      method: 'GET',
      url: '/api/detection/rules',
      signal,
    })
  },

  async updateRule(
    ruleId: string,
    payload: RuleUpdatePayload,
    signal?: AbortSignal
  ): Promise<DetectionRule> {
    return apiRequest<DetectionRule>({
      method: 'PATCH',
      url: `/api/detection/rules/${encodeURIComponent(ruleId)}`,
      data: payload,
      signal,
    })
  },

  async runDetection(
    payload: DetectionRunRequest = { lookback_minutes: 60 },
    signal?: AbortSignal
  ): Promise<DetectionRunSummary> {
    return apiRequest<DetectionRunSummary>({
      method: 'POST',
      url: '/api/detection/run',
      data: payload,
      signal,
    })
  },

  async getHistory(
    page = 1,
    pageSize = 20,
    signal?: AbortSignal
  ): Promise<PaginatedResponse<DetectionRunSummary>> {
    const res = await apiRequest<PaginatedResponse<DetectionRunSummary>>({
      method: 'GET',
      url: '/api/detection/history',
      params: { page, page_size: pageSize },
      signal,
    })
    return {
      items: res.items || [],
      total: res.total ?? 0,
      page: res.page ?? page,
      page_size: res.page_size ?? pageSize,
    }
  },
}
