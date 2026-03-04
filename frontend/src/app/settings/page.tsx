/**
 * システム設定ページ
 */
"use client";

import { Settings, Users, Bell, Shield, Database, Palette } from "lucide-react";
import Link from "next/link";

const settingsCategories = [
  {
    icon: Users,
    label: "ユーザー管理",
    description: "ユーザーアカウント・ロール・権限の管理",
    href: "/settings/users",
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  {
    icon: Bell,
    label: "通知設定",
    description: "メール・Webhook・アラート通知の設定",
    href: "/settings/notifications",
    color: "text-purple-600",
    bg: "bg-purple-50",
  },
  {
    icon: Shield,
    label: "セキュリティ設定",
    description: "認証・セッション・アクセス制御の設定",
    href: "/settings/security",
    color: "text-red-600",
    bg: "bg-red-50",
  },
  {
    icon: Database,
    label: "データ管理",
    description: "バックアップ・メンテナンス・データ保持ポリシー",
    href: "/settings/data",
    color: "text-green-600",
    bg: "bg-green-50",
  },
  {
    icon: Palette,
    label: "外観設定",
    description: "テーマ・言語・タイムゾーンの設定",
    href: "/settings/appearance",
    color: "text-orange-600",
    bg: "bg-orange-50",
  },
  {
    icon: Settings,
    label: "システム全般",
    description: "APIキー・Webhook・統合設定",
    href: "/settings/general",
    color: "text-gray-600",
    bg: "bg-gray-100",
  },
];

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Settings className="h-5 w-5 text-gray-500" />
          システム設定
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">ServiceMatrix の設定を管理します</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {settingsCategories.map((cat) => (
          <Link
            key={cat.href}
            href={cat.href}
            className="group rounded-lg border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300 hover:shadow-md transition-all"
          >
            <div className={`inline-flex rounded-lg ${cat.bg} p-2.5 mb-3`}>
              <cat.icon className={`h-5 w-5 ${cat.color}`} />
            </div>
            <h3 className="text-sm font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">{cat.label}</h3>
            <p className="text-xs text-gray-500 mt-1">{cat.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
