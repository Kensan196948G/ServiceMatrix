/**
 * 認証関連の型定義
 * バックエンドのJWT認証レスポンスと対応
 */

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  user_id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface AuthState {
  user: UserInfo | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
