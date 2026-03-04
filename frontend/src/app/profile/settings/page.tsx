"use client";

import { useState } from "react";
import { Bell, Monitor, Globe, Moon, Sun } from "lucide-react";

export default function ProfileSettingsPage() {
  const [emailNotify, setEmailNotify] = useState(true);
  const [browserNotify, setBrowserNotify] = useState(true);
  const [p1Notify, setP1Notify] = useState(true);
  const [p2Notify, setP2Notify] = useState(true);
  const [p3Notify, setP3Notify] = useState(false);
  const [theme, setTheme] = useState("light");
  const [language, setLanguage] = useState("ja");
  const [timezone, setTimezone] = useState("Asia/Tokyo");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // TODO: API連携またはlocalStorage保存
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const Toggle = ({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) => (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${value ? "bg-blue-600" : "bg-gray-300"}`}
    >
      <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${value ? "translate-x-4.5" : "translate-x-0.5"}`} style={{ transform: value ? "translateX(18px)" : "translateX(2px)" }} />
    </button>
  );

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">個人設定</h1>
      <p className="text-gray-500 mb-6">通知・表示・言語などの個人設定を管理します</p>

      {saved && (
        <div className="mb-4 rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
          設定を保存しました
        </div>
      )}

      <div className="space-y-6">
        {/* 通知設定 */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Bell className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">通知設定</h2>
          </div>
          <div className="space-y-3">
            {[
              { label: "メール通知", desc: "インシデント・変更・SLA違反をメールで受け取る", value: emailNotify, onChange: setEmailNotify },
              { label: "ブラウザ通知", desc: "ブラウザのプッシュ通知を有効にする", value: browserNotify, onChange: setBrowserNotify },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">{item.label}</p>
                  <p className="text-xs text-gray-500">{item.desc}</p>
                </div>
                <Toggle value={item.value} onChange={item.onChange} />
              </div>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100">
            <p className="text-sm font-medium text-gray-700 mb-3">優先度別通知</p>
            <div className="space-y-2">
              {[
                { label: "P1（緊急）", color: "text-red-600 bg-red-50", value: p1Notify, onChange: setP1Notify },
                { label: "P2（高）", color: "text-orange-600 bg-orange-50", value: p2Notify, onChange: setP2Notify },
                { label: "P3（中）", color: "text-yellow-600 bg-yellow-50", value: p3Notify, onChange: setP3Notify },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between py-1.5">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${item.color}`}>{item.label}</span>
                  <Toggle value={item.value} onChange={item.onChange} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 表示設定 */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Monitor className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">表示設定</h2>
          </div>
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">テーマ</p>
              <div className="flex gap-3">
                {[
                  { id: "light", label: "ライト", icon: Sun },
                  { id: "dark", label: "ダーク", icon: Moon },
                  { id: "system", label: "システム", icon: Monitor },
                ].map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setTheme(id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm transition ${theme === id ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 text-gray-600 hover:border-gray-300"}`}
                  >
                    <Icon className="w-4 h-4" /> {label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 言語・タイムゾーン */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">言語・タイムゾーン</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">表示言語</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="ja">日本語</option>
                <option value="en">English</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">タイムゾーン</label>
              <select
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Asia/Tokyo">Asia/Tokyo (JST +9:00)</option>
                <option value="UTC">UTC (+0:00)</option>
                <option value="America/New_York">America/New_York (EST)</option>
                <option value="Europe/London">Europe/London (GMT)</option>
              </select>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={handleSave}
            className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
          >
            設定を保存
          </button>
        </div>
      </div>
    </div>
  );
}
