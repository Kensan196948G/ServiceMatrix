/**
 * AuthContext - React Context版 認証状態管理
 * useAuthStore (Zustand) と連携し、Context APIで認証状態を提供
 * ProtectedRoute等のコンポーネントから利用
 */
"use client";

import {
  createContext,
  useContext,
  useEffect,
  type ReactNode,
} from "react";
import { useAuthStore } from "@/hooks/useAuth";
import type { UserResponse, LoginRequest } from "@/types/api";

interface AuthContextType {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * AuthProvider
 * アプリ起動時にlocalStorageからトークンを復元し、認証状態を管理
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const store = useAuthStore();

  useEffect(() => {
    store.initialize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value: AuthContextType = {
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    isLoading: store.isLoading,
    error: store.error,
    login: store.login,
    logout: store.logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * useAuth - 認証コンテキストを使用するカスタムフック
 * AuthProvider の外で使用するとエラーをスロー
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
