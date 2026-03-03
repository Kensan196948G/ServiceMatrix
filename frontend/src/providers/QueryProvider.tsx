/**
 * TanStack Query プロバイダー
 * アプリ全体でReact Queryのキャッシュ・データフェッチを提供
 */
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

export default function QueryProvider({ children }: Props) {
  // QueryClientをuseStateで保持（SSR時の再生成防止）
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 5分間キャッシュ有効
            staleTime: 5 * 60 * 1000,
            // エラー時は1回だけリトライ
            retry: 1,
            // ウィンドウフォーカス時の自動リフェッチを無効化
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
