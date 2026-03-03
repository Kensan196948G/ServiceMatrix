/**
 * AppShell コンポーネント
 * 認証状態に応じてSidebar+Headerを表示/非表示
 * ログインページではレイアウトなしで表示
 */
"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import { useAuthStore } from "@/hooks/useAuth";

interface Props {
  children: React.ReactNode;
}

export default function AppShell({ children }: Props) {
  const pathname = usePathname();
  const { initialize } = useAuthStore();

  // アプリ起動時に認証状態を復元
  useEffect(() => {
    initialize();
  }, [initialize]);

  // ログインページはレイアウトなし
  if (pathname === "/login") {
    return <>{children}</>;
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
