/**
 * AppShell コンポーネント
 * 認証状態に応じてSidebar+Headerを表示/非表示
 * ログインページではレイアウトなしで表示
 */
"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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
  const { initialize, isAuthenticated } = useAuthStore();
  const [isInitialized, setIsInitialized] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // アプリ起動時に認証状態を復元（完了を明示的に追跡）
  useEffect(() => {
    initialize().finally(() => setIsInitialized(true));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 初期化完了後に未認証ならログインへ
  useEffect(() => {
    if (isInitialized && !isAuthenticated && pathname !== "/login") {
      router.replace("/login");
    }
  }, [isInitialized, isAuthenticated, pathname, router]);

  // ログインページはレイアウトなし
  if (pathname === "/login") {
    return <>{children}</>;
  }

  // 初期化中はローディング表示
  if (!isInitialized) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" message="読み込み中..." />
      </div>
    );
  }

  // 未認証（リダイレクト中）
  if (!isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <LoadingSpinner size="md" message="ログインページへ移動中..." />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header onMenuClick={() => setIsSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
