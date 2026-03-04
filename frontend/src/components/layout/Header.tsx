/**
 * Header コンポーネント - Jira風ヘッダー
 * 検索バー・通知・ユーザーメニュー
 */
"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Bell, Search, LogOut, User, Settings, ChevronDown } from "lucide-react";
import { useAuthStore } from "@/hooks/useAuth";
import NotificationPanel from "@/components/layout/NotificationPanel";

const pageTitles: Record<string, string> = {
  "/": "ダッシュボード",
  "/incidents/[id]": "インシデント詳細",
  "/incidents": "インシデント管理",
  "/changes": "変更管理",
  "/problems": "問題管理",
  "/service-requests": "サービスリクエスト",
  "/sla": "SLA監視",
  "/ai": "AI分析",
  "/cmdb": "CMDB管理",
  "/audit-logs": "監査ログ",
  "/settings": "システム管理",
  "/settings/users": "ユーザー管理",
  "/settings/notifications": "通知管理",
  "/settings/security": "セキュリティ管理",
  "/settings/data": "データ管理",
  "/settings/appearance": "外観設定",
  "/settings/general": "システム全般",
  "/profile": "プロフィール",
  "/profile/settings": "個人設定",
};

// 動的ルートのタイトル解決
function resolveTitle(pathname: string): string {
  if (pageTitles[pathname]) return pageTitles[pathname];
  if (/^\/incidents\/[^/]+$/.test(pathname)) return "インシデント詳細";
  if (/^\/changes\/[^/]+$/.test(pathname)) return "変更詳細";
  if (/^\/problems\/[^/]+$/.test(pathname)) return "問題詳細";
  if (/^\/cmdb\/[^/]+$/.test(pathname)) return "CI詳細・依存関係グラフ";
  const match = Object.entries(pageTitles).find(([path]) =>
    path !== "/" && pathname.startsWith(path)
  );
  return match?.[1] ?? "ServiceMatrix";
}

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);

  const title = resolveTitle(pathname);

  const roleLabel: Record<string, string> = {
    SystemAdmin: "システム管理者",
    Admin: "管理者",
    ChangeManager: "変更マネージャー",
    IncidentManager: "インシデントマネージャー",
    Operator: "オペレーター",
    Viewer: "閲覧者",
  };

  return (
    <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6 flex-shrink-0">
      {/* ページタイトル */}
      <div className="flex items-center gap-2">
        <h1 className="text-base font-semibold text-gray-800">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        {/* 検索バー */}
        <div className={`flex items-center gap-2 rounded-md border px-3 py-1.5 transition-all ${searchFocused ? "border-blue-400 bg-white shadow-sm w-64" : "border-gray-200 bg-gray-50 w-48"}`}>
          <Search className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
          <input
            type="text"
            placeholder="検索..."
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            className="bg-transparent text-sm text-gray-600 placeholder-gray-400 focus:outline-none w-full"
          />
          <kbd className="hidden text-[10px] text-gray-400 sm:inline">/</kbd>
        </div>

        {/* 通知パネル */}
        <NotificationPanel />

        {/* ユーザーメニュー */}
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-100"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
              {user?.full_name?.[0] ?? user?.username?.[0]?.toUpperCase() ?? "U"}
            </div>
            <span className="hidden sm:block max-w-[100px] truncate">{user?.full_name ?? user?.username}</span>
            <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full z-20 mt-1 w-56 rounded-lg border border-gray-200 bg-white shadow-lg">
                <div className="border-b border-gray-100 px-4 py-3">
                  <p className="text-sm font-medium text-gray-900">{user?.full_name ?? user?.username}</p>
                  <p className="text-xs text-gray-500">{user?.email}</p>
                  <span className="mt-1 inline-block rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700">
                    {roleLabel[user?.role ?? ""] ?? user?.role}
                  </span>
                </div>
                <ul className="p-1">
                  <li>
                    <button
                      onClick={() => { router.push("/profile"); setMenuOpen(false); }}
                      className="flex w-full items-center gap-2 rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <User className="h-4 w-4 text-gray-400" /> プロフィール
                    </button>
                  </li>
                  <li>
                    <button
                      onClick={() => { router.push("/profile/settings"); setMenuOpen(false); }}
                      className="flex w-full items-center gap-2 rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <Settings className="h-4 w-4 text-gray-400" /> 設定
                    </button>
                  </li>
                  <li className="border-t border-gray-100 mt-1 pt-1">
                    <button
                      onClick={() => { logout(); setMenuOpen(false); }}
                      className="flex w-full items-center gap-2 rounded px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                    >
                      <LogOut className="h-4 w-4" /> ログアウト
                    </button>
                  </li>
                </ul>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
