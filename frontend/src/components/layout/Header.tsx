/**
 * ヘッダーコンポーネント
 * ユーザー情報表示・ログアウトボタン・通知ベルを提供
 */
"use client";

import { Bell, LogOut, User } from "lucide-react";
import { useCallback, useState } from "react";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/hooks/useAuth";
import { useWebSocket } from "@/hooks/useWebSocket";

/** パスからページタイトルを取得 */
function getPageTitle(pathname: string): string {
  const titles: Record<string, string> = {
    "/": "ダッシュボード",
    "/incidents": "インシデント管理",
    "/changes": "変更管理",
    "/problems": "問題管理",
    "/service-requests": "サービスリクエスト",
    "/sla": "SLA監視",
    "/ai": "AI分析",
    "/cmdb": "CMDB管理",
    "/audit-logs": "監査ログ",
  };
  return titles[pathname] ?? "ServiceMatrix";
}

export default function Header() {
  const { user, logout } = useAuthStore();
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);

  useWebSocket({
    channel: "all",
    onMessage: useCallback(() => setUnread((n) => n + 1), []),
  });

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      {/* ページタイトル */}
      <h1 className="text-lg font-semibold text-gray-800">{getPageTitle(pathname)}</h1>

      {/* ユーザー情報・通知・ログアウト */}
      <div className="flex items-center gap-4">
        {/* 通知ベル */}
        <button
          onClick={() => setUnread(0)}
          className="relative rounded-lg p-1.5 text-gray-500 hover:bg-gray-100"
          aria-label="通知"
        >
          <Bell className="h-5 w-5" />
          {unread > 0 && (
            <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </button>
        {user && (
          <div className="flex items-center gap-2 text-sm text-gray-700">
            <User className="h-4 w-4 text-gray-400" />
            <span>{user.full_name || user.username}</span>
            <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
              {user.role}
            </span>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
        >
          <LogOut className="h-4 w-4" />
          ログアウト
        </button>
      </div>
    </header>
  );
}
