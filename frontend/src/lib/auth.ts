/**
 * 認証ユーティリティ
 * ログイン・ログアウト・トークン管理
 */
import apiClient from "./api";
import type { LoginRequest, TokenResponse, UserResponse } from "@/types/api";

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
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
  }

  return data;
}

/**
 * ログアウト処理
 * localStorageからトークンを削除してログインページにリダイレクト
 */
export function logout(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
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
 * 認証済みかどうかを判定
 */
export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}

/**
 * アクセストークンを取得
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}
