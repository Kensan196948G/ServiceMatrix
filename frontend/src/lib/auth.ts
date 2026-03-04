/**
 * 認証ユーティリティ
 * ログイン・ログアウト・トークン管理・JWT有効期限検証
 */
import apiClient from "./api";
import { authStorage } from "./token";
import type { LoginRequest, TokenResponse, UserResponse } from "@/types/api";

export { authStorage } from "./token";

/**
 * ログイン処理
 * サーバーに認証情報を送信し、トークンをlocalStorageに保存
 */
export async function login(
  credentials: LoginRequest
): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>(
    "/auth/login",
    credentials
  );
  const data = response.data;

  if (typeof window !== "undefined") {
    authStorage.setToken(data.access_token);
    if (data.refresh_token) {
      authStorage.setRefreshToken(data.refresh_token);
    }
  }

  return data;
}

/**
 * ログアウト処理
 * localStorageからトークンを削除してログインページにリダイレクト
 */
export function logout(): void {
  if (typeof window !== "undefined") {
    authStorage.removeToken();
    window.location.href = "/login";
  }
}

/**
 * 現在のユーザー情報を取得
 */
export async function getCurrentUser(): Promise<UserResponse> {
  const response = await apiClient.get<UserResponse>("/auth/me");
  return response.data;
}

/**
 * 認証済みかどうかを判定（トークン有効期限も検証）
 */
export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  const token = authStorage.getToken();
  if (!token) return false;
  return !authStorage.isTokenExpired(token);
}

/**
 * アクセストークンを取得
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return authStorage.getToken();
}
