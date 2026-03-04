/**
 * トークン管理ユーティリティ
 * JWT保存・取得・有効期限検証
 * api.ts と auth.ts の両方から参照されるため独立モジュールとして分離
 */

const TOKEN_KEY = "servicematrix_token";
const REFRESH_TOKEN_KEY = "servicematrix_refresh_token";

export const authStorage = {
  getToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken: (token: string): void => {
    localStorage.setItem(TOKEN_KEY, token);
  },
  setRefreshToken: (token: string): void => {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  },
  removeToken: (): void => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
  isTokenExpired: (token: string): boolean => {
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return Date.now() >= payload.exp * 1000;
    } catch {
      return true;
    }
  },
};
