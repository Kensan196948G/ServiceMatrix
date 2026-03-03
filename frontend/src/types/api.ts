/**
 * ServiceMatrix APIレスポンス型定義
 * バックエンドPydanticスキーマと対応
 */

// --- 認証 ---

/** ログインリクエスト */
export interface LoginRequest {
  username: string;
  password: string;
}

/** トークンレスポンス */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/** ユーザー情報 */
export interface UserResponse {
  user_id: string;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
}

// --- インシデント管理 ---

export interface IncidentResponse {
  incident_id: string;
  incident_number: string;
  title: string;
  description: string | null;
  priority: "P1" | "P2" | "P3" | "P4";
  status: string;
  assigned_to: string | null;
  assigned_team_id: string | null;
  reported_by: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  sla_response_due_at: string | null;
  sla_resolution_due_at: string | null;
  sla_breached: boolean;
  category: string | null;
  affected_service: string | null;
  resolution_notes: string | null;
  ai_triage_notes: string | null;
  created_at: string;
  updated_at: string;
}

// --- 変更管理 ---

export type ChangeType = "Standard" | "Normal" | "Emergency" | "Major";
export type ImpactLevel = "Low" | "Medium" | "High";

export interface ChangeResponse {
  change_id: string;
  change_number: string;
  title: string;
  description: string | null;
  change_type: ChangeType;
  status: string;
  risk_score: number;
  risk_level: string | null;
  impact_level: ImpactLevel | null;
  urgency_level: ImpactLevel | null;
  requested_by: string | null;
  assigned_to: string | null;
  cab_approved_by: string | null;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  actual_start_at: string | null;
  actual_end_at: string | null;
  cab_reviewed_at: string | null;
  implementation_plan: string | null;
  rollback_plan: string | null;
  test_plan: string | null;
  cab_notes: string | null;
  created_at: string;
  updated_at: string;
}

// --- 問題管理 ---

export interface ProblemResponse {
  problem_id: string;
  problem_number: string;
  title: string;
  description: string | null;
  priority: "P1" | "P2" | "P3" | "P4";
  status: string;
  root_cause: string | null;
  known_error: boolean;
  workaround: string | null;
  assigned_to: string | null;
  reported_by: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  category: string | null;
  affected_service: string | null;
  created_at: string;
  updated_at: string;
}

// --- サービスリクエスト ---

export interface ServiceRequestResponse {
  request_id: string;
  request_number: string;
  title: string;
  description: string | null;
  priority: "P1" | "P2" | "P3" | "P4";
  status: string;
  category: string | null;
  requested_by: string | null;
  assigned_to: string | null;
  approved_by: string | null;
  approved_at: string | null;
  fulfilled_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

// --- 共通 ---

/** APIページネーションレスポンス */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

/** ヘルスチェックレスポンス */
export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

/** ダッシュボード統計 */
export interface DashboardStats {
  incidents: number;
  changes: number;
  problems: number;
  service_requests: number;
}

// --- SLA監視 ---

/** SLA優先度別達成率サマリー（1エントリ） */
export interface SLAPrioritySummary {
  total: number;
  breached: number;
  compliance_rate: number;
}

/** SLA達成率サマリー（優先度キー→サマリー値） */
export type SLASummaryResponse = Record<string, SLAPrioritySummary>;

/** SLA警告情報 */
export interface SLAWarning {
  incident_id: string;
  incident_number: string;
  title: string;
  priority: "P1" | "P2" | "P3" | "P4";
  sla_type: "response" | "resolution";
  warning_level: "warning_70" | "warning_90";
  progress_percent: number;
  deadline: string | null;
}

/** SLA警告一覧レスポンス */
export interface SLAWarningsResponse {
  warnings: SLAWarning[];
  count: number;
}

/** SLA個別ステータスのSLA情報 */
export interface SLADetail {
  deadline: string;
  met: boolean;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
  warning_level: string;
  progress_percent: number;
}

/** SLA個別ステータスレスポンス */
export interface SLAStatusResponse {
  incident_id: string;
  incident_number: string;
  priority: string;
  status: string;
  sla_breached: boolean;
  sla_breached_at: string | null;
  response_sla?: SLADetail;
  resolution_sla?: SLADetail;
}

/** SLA手動チェックレスポンス */
export interface SLACheckResponse {
  checked: boolean;
  timestamp: string;
  breaches_detected: number;
  warnings_detected: number;
}
