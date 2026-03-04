/**
 * ユーザー管理ページ
 */
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Users, Plus, Shield, Mail, Clock } from "lucide-react";
import apiClient from "@/lib/api";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

interface UserItem {
  user_id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

const ROLE_LABELS: Record<string, string> = {
  SystemAdmin: "システム管理者",
  Admin: "管理者",
  ChangeManager: "変更マネージャー",
  IncidentManager: "インシデントマネージャー",
  Operator: "オペレーター",
  Viewer: "閲覧者",
};

const ROLE_COLORS: Record<string, string> = {
  SystemAdmin: "bg-red-100 text-red-800",
  Admin: "bg-orange-100 text-orange-800",
  ChangeManager: "bg-blue-100 text-blue-800",
  IncidentManager: "bg-purple-100 text-purple-800",
  Operator: "bg-green-100 text-green-800",
  Viewer: "bg-gray-100 text-gray-700",
};

export default function UsersPage() {
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => apiClient.get("/users").then(r => r.data).catch(() => []),
  });

  const users: UserItem[] = data?.items ?? data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="h-5 w-5 text-blue-500" />
            ユーザー管理
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">システムユーザーとロールを管理します</p>
        </div>
        <Button variant="primary" size="md" icon={<Plus className="h-4 w-4" />} onClick={() => setShowCreate(true)}>
          ユーザー追加
        </Button>
      </div>

      {/* ロール凡例 */}
      <div className="flex flex-wrap gap-2 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        <span className="text-xs font-medium text-gray-500 self-center">ロール：</span>
        {Object.entries(ROLE_LABELS).map(([role, label]) => (
          <span key={role} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_COLORS[role]}`}>
            {label}
          </span>
        ))}
      </div>

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex h-48 items-center justify-center"><LoadingSpinner size="lg" /></div>
        ) : users.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2 text-gray-400">
            <Users className="h-8 w-8 text-gray-300" />
            <p className="text-sm">ユーザーが見つかりません</p>
            <p className="text-xs text-gray-400">ユーザー管理APIが利用可能になると表示されます</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-[1fr_200px_180px_100px_120px] gap-3 border-b border-gray-100 bg-gray-50 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
              <span>ユーザー</span><span>メール</span><span>ロール</span><span>状態</span><span>作成日</span>
            </div>
            {users.map((user: UserItem) => (
              <div key={user.user_id} className="grid grid-cols-[1fr_200px_180px_100px_120px] gap-3 items-center border-b border-gray-50 px-4 py-3 hover:bg-gray-50 last:border-0">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                    {user.full_name?.[0] ?? user.username?.[0]?.toUpperCase()}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-800">{user.full_name}</p>
                    <p className="text-xs text-gray-400">@{user.username}</p>
                  </div>
                </div>
                <span className="flex items-center gap-1 text-sm text-gray-600">
                  <Mail className="h-3.5 w-3.5 text-gray-300" />{user.email}
                </span>
                <span>
                  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_COLORS[user.role] ?? "bg-gray-100 text-gray-700"}`}>
                    <Shield className="h-3 w-3" />
                    {ROLE_LABELS[user.role] ?? user.role}
                  </span>
                </span>
                <span>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${user.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {user.is_active ? "有効" : "無効"}
                  </span>
                </span>
                <span className="flex items-center gap-1 text-xs text-gray-400">
                  <Clock className="h-3 w-3" />
                  {new Date(user.created_at).toLocaleDateString("ja-JP", { month: "short", day: "numeric" })}
                </span>
              </div>
            ))}
          </>
        )}
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="rounded-lg bg-white p-6 shadow-2xl w-full max-w-md mx-4">
            <h2 className="text-lg font-semibold mb-4">ユーザー追加</h2>
            <p className="text-sm text-gray-500 mb-4">ユーザー管理APIは現在準備中です。直接DBに追加するか、管理CLIを使用してください。</p>
            <div className="rounded-md bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-700 font-mono">
              python3 scripts/create_user.py --username xxx --role Operator
            </div>
            <div className="flex justify-end mt-4">
              <Button variant="secondary" onClick={() => setShowCreate(false)}>閉じる</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
