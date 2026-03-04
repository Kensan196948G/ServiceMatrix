/**
 * Axios APIクライアント
 * JWT自動付与（有効期限検証付き）・401時リダイレクト・インターセプター設定
 */
import axios from "axios";
import { authStorage } from "./token";

/** APIベースURL（環境変数またはデフォルト） */
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Axiosインスタンス */
const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

/**
 * リクエストインターセプター
 * JWTトークンが有効な場合のみ Authorization ヘッダーに付与
 */
apiClient.interceptors.request.use(
  (config) => {
    const token = authStorage.getToken();
    if (token && !authStorage.isTokenExpired(token)) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * レスポンスインターセプター
 * 401エラー時にトークンをクリアしてログインページへリダイレクト
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      typeof window !== "undefined" &&
      !window.location.pathname.includes("/login")
    ) {
      authStorage.removeToken();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default apiClient;
