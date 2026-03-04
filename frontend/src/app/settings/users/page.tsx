/**
 * ユーザー管理ページ
 */
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Users, Plus, Shield, Mail, Clock, X } from "lucide-react";
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

const ROLES = [
  { value: "SystemAdmin", label: "システム管理者" },
  { value: "ServiceManager", label: "サービスマネージャー" },
  { value: "ChangeManager", label: "変更マネージャー" },
  { value: "IncidentManager", label: "インシデントマネージャー" },
  { value: "Operator", label: "オペレーター" },
  { value: "Viewer", label: "閲覧者" },
];

const ROLE_LABELS: Record<string, string> = Object.fromEntries(ROLES.map(r => [r.value, r.label]));

const ROLE_COLORS: Record<string, string> = {
  SystemAdmin: "bg-red-100 text-red-800",
  ServiceManager: "bg-pink-100 text-pink-800",
  Admin: "bg-orange-100 text-orange-800",
  ChangeManager: "bg-blue-100 text-blue-800",
  IncidentManager: "bg-purple-100 text-purple-800",
  Operator: "bg-green-100 text-green-800",
  Viewer: "bg-gray-100 text-gray-700",
};

const EMPTY_FORM = { username: "", email: "", full_name: "", password: "", role: "Viewer", is_active: true };

export default function UsersPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [createError, setCreateError] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => apiClient.get("/auth/users").then(r => r.data).catch(() => []),
  });

  const users: UserItem[] = Array.isArray(data) ? data : data?.items ?? [];

  const createMutation = useMutation({
    mutationFn: (d: typeof form) => apiClient.post("/auth/users", d).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setShowCreate(false);
      setForm({ ...EMPTY_FORM });
      setCreateError("");
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setCreateError(msg ?? "ユーザー作成に失敗しました");
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError("");
    if (!form.username.trim()) { setCreateError("ユーザー名は必須です"); return; }
    if (!form.email.trim()) { setCreateError("メールアドレスは必須です"); return; }
    if (form.password.length < 8) { setCreateError("パスワードは8文字以上で入力してください"); return; }
    createMutation.mutate(form);
  };

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
        {ROLES.map(({ value, label }) => (
          <span key={value} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_COLORS[value]}`}>
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
            <p className="text-sm">ユーザーがいません</p>
            <button onClick={() => setShowCreate(true)} className="text-xs text-blue-600 hover:underline">ユーザーを追加する</button>
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
                    <p className="text-sm font-medium text-gray-800">{user.full_name || user.username}</p>
                    <p className="text-xs text-gray-400">@{user.username}</p>
                  </div>
                </div>
                <span className="flex items-center gap-1 text-sm text-gray-600 truncate">
                  <Mail className="h-3.5 w-3.5 text-gray-300 flex-shrink-0" />{user.email}
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
                  {user.created_at ? new Date(user.created_at).toLocaleDateString("ja-JP", { month: "short", day: "numeric" }) : "—"}
                </span>
              </div>
            ))}
          </>
        )}
      </div>

      {/* ユーザー追加モーダル */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-xl bg-white shadow-xl mx-4">
            <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
              <h2 className="text-base font-semibold text-gray-900">ユーザー追加</h2>
              <button onClick={() => { setShowCreate(false); setCreateError(""); }} className="rounded p-1 text-gray-400 hover:bg-gray-100">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-5 space-y-4">
              {createError && (
                <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{createError}</div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">ユーザー名 <span className="text-red-500">*</span></label>
                  <input
                    type="text"
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                    placeholder="例: john_doe"
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">表示名</label>
                  <input
                    type="text"
                    value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                    placeholder="例: 山田 太郎"
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">メールアドレス <span className="text-red-500">*</span></label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="例: user@example.com"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">初期パスワード <span className="text-red-500">*</span></label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="8文字以上"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">ロール</label>
                  <select
                    value={form.role}
                    onChange={(e) => setForm({ ...form, role: e.target.value })}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状態</label>
                  <select
                    value={form.is_active ? "true" : "false"}
                    onChange={(e) => setForm({ ...form, is_active: e.target.value === "true" })}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="true">有効</option>
                    <option value="false">無効</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => { setShowCreate(false); setCreateError(""); }} className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50">
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
                >
                  {createMutation.isPending ? "作成中..." : "ユーザー追加"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
