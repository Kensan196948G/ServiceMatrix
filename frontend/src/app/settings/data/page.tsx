"use client";

import { HardDrive, Download, Trash2, RefreshCw, ArchiveRestore } from "lucide-react";

const sections = [
  {
    icon: Download,
    title: "バックアップ",
    description: "データベースの定期バックアップを管理します",
    items: [
      { label: "自動バックアップ", value: "有効（毎日 02:00）" },
      { label: "保存期間", value: "30日間" },
      { label: "保存先", value: "ローカル + S3" },
      { label: "最終バックアップ", value: "2026-03-04 02:00" },
    ],
  },
  {
    icon: ArchiveRestore,
    title: "リストア",
    description: "バックアップからデータを復元します",
    items: [
      { label: "利用可能なポイント数", value: "30件" },
      { label: "最終確認済みバックアップ", value: "2026-03-03" },
    ],
  },
  {
    icon: Trash2,
    title: "データ保持ポリシー",
    description: "古いデータの自動削除・アーカイブ設定",
    items: [
      { label: "監査ログ保持期間", value: "1年" },
      { label: "クローズ済みインシデント", value: "2年後にアーカイブ" },
      { label: "通知履歴", value: "90日" },
    ],
  },
  {
    icon: RefreshCw,
    title: "データベースメンテナンス",
    description: "VACUUM・インデックス最適化・統計更新",
    items: [
      { label: "自動VACUUM", value: "有効" },
      { label: "最終最適化", value: "2026-03-01" },
      { label: "DB容量使用量", value: "512 MB / 10 GB" },
    ],
  },
];

export default function DataSettingsPage() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">データ管理</h1>
      <p className="text-gray-500 mb-6">バックアップ・リストア・データ保持ポリシーを管理します</p>

      <div className="space-y-4">
        {sections.map((section) => {
          const Icon = section.icon;
          return (
            <div key={section.title} className="bg-white rounded-lg border border-gray-200 p-5">
              <div className="flex items-start gap-3 mb-4">
                <div className="p-2 bg-orange-50 rounded-lg">
                  <Icon className="w-5 h-5 text-orange-600" />
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
