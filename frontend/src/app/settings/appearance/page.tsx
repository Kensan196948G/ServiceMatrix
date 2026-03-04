"use client";

import { useState } from "react";
import { Palette, Sun, Moon, Type, Layout, Check } from "lucide-react";

const themes = [
  { id: "light", label: "ライト", preview: "bg-white border-gray-200" },
  { id: "dark", label: "ダーク", preview: "bg-gray-900 border-gray-700" },
  { id: "system", label: "システム", preview: "bg-gradient-to-r from-white to-gray-900 border-gray-400" },
];

const accentColors = [
  { id: "blue", label: "ブルー", color: "bg-blue-600" },
  { id: "indigo", label: "インディゴ", color: "bg-indigo-600" },
  { id: "violet", label: "バイオレット", color: "bg-violet-600" },
  { id: "green", label: "グリーン", color: "bg-green-600" },
  { id: "orange", label: "オレンジ", color: "bg-orange-500" },
];

const fontSizes = ["小（12px）", "標準（14px）", "大（16px）"];
const densities = ["コンパクト", "標準", "ゆったり"];

export default function AppearancePage() {
  const [selectedTheme, setSelectedTheme] = useState("light");
  const [selectedAccent, setSelectedAccent] = useState("blue");
  const [fontSize, setFontSize] = useState("標準（14px）");
  const [density, setDensity] = useState("標準");

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">外観設定</h1>
      <p className="text-gray-500 mb-6">テーマ・カラー・フォント・レイアウト密度を設定します</p>

      <div className="space-y-6">
        {/* テーマ */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Palette className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">テーマ</h2>
          </div>
          <div className="flex gap-4">
            {themes.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedTheme(t.id)}
                className={`flex-1 rounded-lg border-2 p-3 text-center transition ${
                  selectedTheme === t.id ? "border-blue-500" : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className={`h-10 rounded mb-2 border ${t.preview}`} />
                <span className="text-sm font-medium text-gray-700">{t.label}</span>
                {selectedTheme === t.id && (
                  <div className="flex justify-center mt-1">
                    <Check className="w-4 h-4 text-blue-500" />
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* アクセントカラー */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Sun className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">アクセントカラー</h2>
          </div>
          <div className="flex gap-3">
            {accentColors.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedAccent(c.id)}
                className="flex flex-col items-center gap-1"
              >
                <div className={`w-8 h-8 rounded-full ${c.color} ${selectedAccent === c.id ? "ring-2 ring-offset-2 ring-gray-400" : ""}`} />
                <span className="text-xs text-gray-600">{c.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* フォントサイズ */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Type className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">フォントサイズ</h2>
          </div>
          <div className="flex gap-3">
            {fontSizes.map((f) => (
              <button
                key={f}
                onClick={() => setFontSize(f)}
                className={`px-4 py-2 rounded border text-sm transition ${
                  fontSize === f ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* レイアウト密度 */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Layout className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-900">レイアウト密度</h2>
          </div>
          <div className="flex gap-3">
            {densities.map((d) => (
              <button
                key={d}
                onClick={() => setDensity(d)}
                className={`px-4 py-2 rounded border text-sm transition ${
                  density === d ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-end">
          <button className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition">
            設定を保存
          </button>
        </div>
      </div>
    </div>
  );
}
