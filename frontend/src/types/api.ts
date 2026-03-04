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

/** SLA計測値 */
export interface SLAMeasurement {
  measurement_id: string;
  incident_id: string;
  sla_type: "response" | "resolution";
  target_minutes: number;
  actual_minutes: number | null;
  breached: boolean;
  measured_at: string;
  created_at: string;
}
