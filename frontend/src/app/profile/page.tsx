"use client";

import { useState } from "react";
import { User, Mail, Shield, Camera, Save, Key } from "lucide-react";
import { useAuthStore } from "@/hooks/useAuth";

const roleLabel: Record<string, string> = {
  SystemAdmin: "システム管理者",
  Admin: "管理者",
  ChangeManager: "変更マネージャー",
  IncidentManager: "インシデントマネージャー",
  Operator: "オペレーター",
  Viewer: "閲覧者",
};

export default function ProfilePage() {
  const { user } = useAuthStore();

  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saved, setSaved] = useState(false);
  const [pwError, setPwError] = useState("");

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: API連携
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault();
    setPwError("");
    if (newPassword !== confirmPassword) {
      setPwError("新しいパスワードが一致しません");
      return;
    }
    if (newPassword.length < 8) {
      setPwError("パスワードは8文字以上で入力してください");
      return;
    }
    // TODO: API連携
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const initials = (user?.full_name ?? user?.username ?? "U")
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">プロフィール</h1>
      <p className="text-gray-500 mb-6">アカウント情報とパスワードを管理します</p>

      {saved && (
        <div className="mb-4 rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700 flex items-center gap-2">
          <Save className="w-4 h-4" /> 変更を保存しました
        </div>
      )}

      <div className="space-y-6">
        {/* アバター */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-5">
            <div className="relative">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-blue-600 text-2xl font-bold text-white select-none">
                {initials}
              </div>
              <button className="absolute bottom-0 right-0 flex h-6 w-6 items-center justify-center rounded-full bg-white border border-gray-300 shadow hover:bg-gray-50">
                <Camera className="w-3.5 h-3.5 text-gray-600" />
              </button>
            </div>
            <div>
              <p className="text-lg font-semibold text-gray-900">{user?.full_name ?? user?.username}</p>
              <p className="text-sm text-gray-500">{user?.email}</p>
              <span className="mt-1 inline-block rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                {roleLabel[user?.role ?? ""] ?? user?.role}
              </span>
            </div>
          </div>
        </div>

        {/* 基本情報編集 */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <User className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">基本情報</h2>
          </div>
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">ユーザー名</label>
                <input
                  type="text"
                  value={user?.username ?? ""}
                  readOnly
                  className="w-full rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500 cursor-not-allowed"
                />
                <p className="text-xs text-gray-400 mt-1">ユーザー名は変更できません</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">ロール</label>
                <input
                  type="text"
                  value={roleLabel[user?.role ?? ""] ?? user?.role ?? ""}
                  readOnly
                  className="w-full rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500 cursor-not-allowed"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">表示名</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="フルネームを入力"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <span className="flex items-center gap-1"><Mail className="w-4 h-4" /> メールアドレス</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
              >
                プロフィールを保存
              </button>
            </div>
          </form>
        </div>

        {/* パスワード変更 */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Key className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">パスワード変更</h2>
          </div>
          <form onSubmit={handleChangePassword} className="space-y-4">
            {pwError && (
              <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
                {pwError}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">現在のパスワード</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">新しいパスワード</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="8文字以上"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">新しいパスワード（確認）</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                className="px-5 py-2 bg-gray-800 text-white rounded-lg text-sm font-medium hover:bg-gray-900 transition"
              >
                パスワードを変更
              </button>
            </div>
          </form>
        </div>

        {/* アカウント情報 */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">アカウント情報</h2>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between py-2 px-3 bg-gray-50 rounded">
              <span className="text-sm text-gray-600">ユーザーID</span>
              <span className="text-xs font-mono text-gray-500">{user?.user_id}</span>
            </div>
            <div className="flex justify-between py-2 px-3 bg-gray-50 rounded">
              <span className="text-sm text-gray-600">アカウント状態</span>
              <span className={`text-sm font-medium ${user?.is_active ? "text-green-600" : "text-red-600"}`}>
                {user?.is_active ? "有効" : "無効"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
