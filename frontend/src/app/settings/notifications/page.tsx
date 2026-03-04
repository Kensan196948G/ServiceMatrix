/**
 * 通知設定ページ
 */
"use client";

import { Bell, Mail, Webhook, AlertTriangle, Clock } from "lucide-react";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

export default function NotificationsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Bell className="h-5 w-5 text-purple-500" />
          通知設定
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">アラート・メール・Webhook通知を設定します</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              SLAアラート
            </CardTitle>
          </CardHeader>
          <div className="space-y-3">
            {[
              { label: "SLA違反直前（30分前）", enabled: true },
              { label: "SLA違反発生時", enabled: true },
              { label: "P1インシデント発生時", enabled: true },
              { label: "未対応インシデント（1時間超）", enabled: false },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <span className="text-sm text-gray-700">{item.label}</span>
                <div className={`relative h-5 w-9 rounded-full transition-colors ${item.enabled ? "bg-blue-600" : "bg-gray-200"}`}>
                  <div className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${item.enabled ? "translate-x-4" : "translate-x-0.5"}`} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-blue-500" />
              メール通知
            </CardTitle>
          </CardHeader>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">送信先メールアドレス</label>
              <input type="email" placeholder="admin@example.com" className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">SMTPサーバー</label>
              <input type="text" placeholder="smtp.example.com:587" className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
            </div>
            <p className="text-xs text-gray-400">※ メール送信機能は次バージョンで実装予定</p>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Webhook className="h-4 w-4 text-green-500" />
              Webhook設定
            </CardTitle>
          </CardHeader>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Webhook URL</label>
              <input type="url" placeholder="https://hooks.slack.com/..." className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">イベントタイプ</label>
              <div className="space-y-1">
                {["incident.created", "incident.escalated", "sla.breached", "change.approved"].map(evt => (
                  <label key={evt} className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" className="rounded border-gray-300 text-blue-600" defaultChecked={evt.includes("sla")} />
                    <span className="font-mono text-xs">{evt}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-orange-500" />
              エスカレーション設定
            </CardTitle>
          </CardHeader>
          <div className="space-y-3">
            {[
              { label: "P1 エスカレーション時間", value: "15分" },
              { label: "P2 エスカレーション時間", value: "60分" },
              { label: "P3 エスカレーション時間", value: "4時間" },
              { label: "P4 エスカレーション時間", value: "24時間" },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between py-1.5">
                <span className="text-sm text-gray-700">{item.label}</span>
                <span className="text-sm font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded">{item.value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
