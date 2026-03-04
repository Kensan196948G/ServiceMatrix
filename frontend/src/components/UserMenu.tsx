/**
 * UserMenu - ユーザーメニューコンポーネント
 * ユーザー名・ロール表示とログアウトボタン
 */
"use client";

import { LogOut, User } from "lucide-react";
import { useAuthStore } from "@/hooks/useAuth";

export default function UserMenu() {
  const { user, logout } = useAuthStore();

  return (
    <div className="flex items-center gap-4">
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
  );
}
