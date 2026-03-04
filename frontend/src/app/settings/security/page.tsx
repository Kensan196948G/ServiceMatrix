"use client";

import { Lock, Key, Shield, UserX, Clock } from "lucide-react";

const sections = [
  {
    icon: Key,
    title: "パスワードポリシー",
    description: "最小文字数・複雑さ・有効期限を設定します",
    items: [
      { label: "最小文字数", value: "8文字以上" },
      { label: "複雑さ要件", value: "大文字・数字・記号を含む" },
      { label: "パスワード有効期限", value: "90日" },
    ],
  },
  {
    icon: Lock,
    title: "アカウントロックアウト",
    description: "連続ログイン失敗時のロックアウト設定",
    items: [
      { label: "最大試行回数", value: "5回" },
      { label: "ロックアウト時間", value: "30分" },
    ],
  },
  {
    icon: Clock,
    title: "セッション管理",
    description: "セッションタイムアウト・同時ログイン設定",
    items: [
      { label: "セッションタイムアウト", value: "8時間" },
      { label: "同時ログイン", value: "許可（最大3セッション）" },
    ],
  },
  {
    icon: Shield,
    title: "二要素認証（2FA）",
    description: "TOTP / メールOTPによる追加認証",
    items: [
      { label: "2FA強制", value: "管理者のみ必須" },
      { label: "対応方式", value: "TOTP（認証アプリ）" },
    ],
  },
  {
    icon: UserX,
    title: "アクセス制御",
    description: "IPアドレス制限・ロールベースアクセス制御",
    items: [
      { label: "IP制限", value: "無効（全許可）" },
      { label: "RBAC", value: "有効" },
    ],
  },
];

export default function SecuritySettingsPage() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">セキュリティ管理</h1>
      <p className="text-gray-500 mb-6">システムのセキュリティポリシーを管理します</p>

      <div className="space-y-4">
        {sections.map((section) => {
          const Icon = section.icon;
          return (
            <div key={section.title} className="bg-white rounded-lg border border-gray-200 p-5">
              <div className="flex items-start gap-3 mb-4">
                <div className="p-2 bg-red-50 rounded-lg">
                  <Icon className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <h2 className="font-semibold text-gray-900">{section.title}</h2>
                  <p className="text-sm text-gray-500">{section.description}</p>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {section.items.map((item) => (
                  <div key={item.label} className="flex justify-between items-center py-2 px-3 bg-gray-50 rounded">
                    <span className="text-sm text-gray-600">{item.label}</span>
                    <span className="text-sm font-medium text-gray-900">{item.value}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex justify-end">
                <button className="text-sm text-blue-600 hover:text-blue-800 font-medium">設定を変更 →</button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
