/**
 * AppShell コンポーネント
 * 認証状態に応じてSidebar+Headerを表示/非表示
 * ログインページではレイアウトなしで表示
 */
"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import { useAuthStore } from "@/hooks/useAuth";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

interface Props {
  children: React.ReactNode;
}

export default function AppShell({ children }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const { initialize, isAuthenticated, isLoading } = useAuthStore();

  // アプリ起動時に認証状態を復元
  useEffect(() => {
    initialize();
  }, [initialize]);

  // 未認証ならログインページへリダイレクト
  useEffect(() => {
    if (!isLoading && !isAuthenticated && pathname !== "/login") {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, pathname, router]);

  // ログインページはレイアウトなし
  if (pathname === "/login") {
    return <>{children}</>;
  }

  // 認証確認中はローディング表示
  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" message="認証を確認中..." />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
