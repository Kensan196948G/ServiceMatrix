/**
 * 認証状態管理フック（Zustand）
 * ログイン・ログアウト・ユーザー情報をグローバルに管理
 */
"use client";

import { create } from "zustand";
import type { UserResponse, LoginRequest } from "@/types/api";
import { login as apiLogin, logout as apiLogout, getCurrentUser } from "@/lib/auth";

/** 認証ストアの型定義 */
interface AuthState {
  /** 現在のユーザー情報 */
  user: UserResponse | null;
  /** 認証済みフラグ */
  isAuthenticated: boolean;
  /** ローディング状態 */
  isLoading: boolean;
  /** エラーメッセージ */
  error: string | null;
  /** ログイン処理 */
  login: (credentials: LoginRequest) => Promise<void>;
  /** ログアウト処理 */
  logout: () => void;
  /** ユーザー情報の再取得 */
  fetchUser: () => Promise<void>;
  /** 初期化（トークン存在時にユーザー取得） */
  initialize: () => Promise<void>;
}

/**
 * Zustand認証ストア
 * アプリ全体で認証状態を共有
 */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (credentials: LoginRequest) => {
    set({ isLoading: true, error: null });
    try {
      await apiLogin(credentials);
      const user = await getCurrentUser();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "ログインに失敗しました";
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: () => {
    set({ user: null, isAuthenticated: false });
    apiLogout();
  },

  fetchUser: async () => {
    try {
      const user = await getCurrentUser();
      set({ user, isAuthenticated: true });
    } catch {
      set({ user: null, isAuthenticated: false });
    }
  },

  initialize: async () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("access_token");
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }
    set({ isLoading: true });
    try {
      const user = await getCurrentUser();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
