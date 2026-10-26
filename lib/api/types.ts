export type Severity = 'Critical' | 'High' | 'Medium' | 'Low' | 'Info'

export type AlertStatus = 'Open' | 'Investigating' | 'Resolved' | 'Dismissed'

export type IncidentStatus = 'Open' | 'Investigating' | 'Contained' | 'Resolved' | 'Closed'

export interface SecurityEvent {
  id: string
  timestamp: string
  event_type: string
  source_ip?: string | null
  username?: string | null
  outcome?: string | null
  source?: string | null
  severity: Severity
  description?: string | null
  metadata?: Record<string, unknown>
}

export interface PaginatedResponse<T> {
  items: T[]
  events?: T[]
  total: number
  page: number
  page_size: number
}

export interface IngestionResponse {
  created: number
  rejected: number
  duplicates: number
  errors: string[]
}

export interface Alert {
  id: string
  rule_id: string
  title: string
  detail?: string | null
  severity: Severity
  status: AlertStatus
  matched_count: number
  event_ids: string[]
  dedup_key?: string | null
  analyst_notes?: string | null
  assigned_to?: string | null
  timestamp: string
  updated_at: string
}

export interface AlertUpdatePayload {
  status?: AlertStatus
  analyst_notes?: string
  assigned_to?: string
}

export interface Incident {
  id: string
  title: string
  description?: string | null
  severity: 'Critical' | 'High' | 'Medium' | 'Low'
  status: IncidentStatus
  assigned_to?: string | null
  alert_ids: string[]
  event_ids: string[]
  investigation_notes?: string | null
  resolution_summary?: string | null
  created_at: string
  updated_at: string
}

export interface IncidentCreatePayload {
  title: string
  description?: string
  severity?: 'Critical' | 'High' | 'Medium' | 'Low'
  status?: IncidentStatus
  assigned_to?: string
  alert_ids?: string[]
  event_ids?: string[]
  investigation_notes?: string
}

export interface IncidentUpdatePayload {
  title?: string
  description?: string
  severity?: 'Critical' | 'High' | 'Medium' | 'Low'
  status?: IncidentStatus
  assigned_to?: string
  alert_ids?: string[]
  event_ids?: string[]
  investigation_notes?: string
  resolution_summary?: string
}

export interface DetectionRule {
  id: string
  name: string
  description: string
  enabled: boolean
  severity: Severity
  threshold: number
  window_minutes: number
  event_types: string[]
  parameters: Record<string, unknown>
}

export interface RuleUpdatePayload {
  enabled?: boolean
  severity?: Severity
  threshold?: number
  window_minutes?: number
  parameters?: Record<string, unknown>
}

export interface DetectionResult {
  rule_id: string
  title: string
  severity: string
  detection_time: string
  matched_event_ids: string[]
  matched_event_count: number
  detection_reason: string
  evidence_summary: string
  source_identifier?: string | null
  group_key: string
  dedup_key: string
  status: string
}

export interface DetectionRunSummary {
  run_id: string
  timestamp: string
  lookback_minutes: number
  events_examined: number
  rules_evaluated: number
  detections_generated: number
  alerts_created: number
  alerts_deduplicated: number
  detections: DetectionResult[]
}

export interface DashboardSummary {
  total_events: number
  active_alerts: number
  open_incidents: number
  detection_coverage_pct: number
  rules_triggered: number
  total_rules: number
  enabled_rules: number
}

export interface TrendPoint {
  d: string
  v: number
}

export interface TrendsResponse {
  time_range: string
  points: TrendPoint[]
  peak_label?: string | null
  total_in_period: number
}

export interface SeverityResponse {
  alerts_by_severity: Record<string, number>
  events_by_severity: Record<string, number>
  total_alerts: number
  total_events: number
}

export interface SourceDistributionPoint {
  d: string
  v: number
}

export interface SourceDistributionResponse {
  items: SourceDistributionPoint[]
  total: number
}

export interface SystemHealth {
  status: string
  service: string
  version: string
  environment: string
  timestamp: string
}

export interface SystemReadiness {
  status: string
  ready: boolean
  database: string
  timestamp: string
  message?: string
}

export type ConnectionStatus =
  | 'connected'
  | 'connecting'
  | 'backend_unavailable'
  | 'database_unavailable'
  | 'demo_mode'
