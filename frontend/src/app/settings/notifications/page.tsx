/**
 * 通知設定ページ（バックエンドAPI永続化対応）
 */
"use client";

import { useState, useEffect } from "react";
import { Bell, Mail, Webhook, AlertTriangle, Clock, Save, RefreshCw } from "lucide-react";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import apiClient from "@/lib/api";
import { useAuthStore } from "@/hooks/useAuth";

interface NotificationSettings {
  email: boolean;
  sla_breach: boolean;
  incident_created: boolean;
  change_approved: boolean;
  sr_completed: boolean;
  webhook_url: string;
  webhook_type: string;
}

interface ToggleRowProps {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}

function ToggleRow({ label, checked, onChange }: ToggleRowProps) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
      <span className="text-sm text-gray-700">{label}</span>
      <button
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 rounded-full transition-colors ${checked ? "bg-blue-600" : "bg-gray-200"}`}
        aria-checked={checked}
        role="switch"
      >
        <div
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${checked ? "translate-x-4" : "translate-x-0.5"}`}
        />
      </button>
    </div>
  );
}

export default function NotificationsPage() {
  const { isAuthenticated } = useAuthStore();
  const [settings, setSettings] = useState<NotificationSettings>({
    email: true,
    sla_breach: true,
    incident_created: true,
    change_approved: false,
    sr_completed: false,
    webhook_url: "",
    webhook_type: "slack",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [webhookTesting, setWebhookTesting] = useState(false);
  const [webhookTestResult, setWebhookTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    if (!isAuthenticated) return;
    apiClient
      .get<{ settings: NotificationSettings }>("/notifications/settings")
      .then((res) => {
        setSettings(res.data.settings);
      })
      .catch(() => {
        // API未対応の場合はLocalStorageからフォールバック
        const stored = localStorage.getItem("notificationSettings");
        if (stored) {
          try { setSettings(JSON.parse(stored)); } catch { /* ignore */ }
        }
      })
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  const update = (key: keyof NotificationSettings, value: boolean | string) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleTestWebhook = async () => {
    if (!settings.webhook_url) return;
    setWebhookTesting(true);
    setWebhookTestResult(null);
    try {
      const res = await apiClient.post<{ success: boolean; message: string }>(
        "/notifications/settings/test-webhook",
        { webhook_url: settings.webhook_url, webhook_type: settings.webhook_type }
      );
      setWebhookTestResult(res.data);
    } catch {
      setWebhookTestResult({ success: false, message: "リクエスト失敗" });
    } finally {
      setWebhookTesting(false);
    }
  };

  const handleSave = async () => {
    if (!isAuthenticated) return;
    setSaving(true);
    setError(null);
    try {
      await apiClient.patch("/notifications/settings", settings);
      localStorage.setItem("notificationSettings", JSON.stringify(settings));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      // フォールバック: LocalStorageのみ保存
      localStorage.setItem("notificationSettings", JSON.stringify(settings));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      setError(err instanceof Error ? err.message : null);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <RefreshCw className="animate-spin text-gray-400" size={24} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Bell className="h-5 w-5 text-purple-500" />
            通知設定
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">アラート・メール・Webhook通知を設定します</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
          {saved ? "✓ 保存済み" : "設定を保存"}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md text-sm text-yellow-700">
          APIへの保存は失敗しましたが、ローカルに保存しました: {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              SLAアラート
            </CardTitle>
          </CardHeader>
          <div className="space-y-1">
            <ToggleRow
              label="SLA違反発生時"
              checked={settings.sla_breach}
              onChange={(v) => update("sla_breach", v)}
            />
            <ToggleRow
              label="P1インシデント発生時"
              checked={settings.incident_created}
              onChange={(v) => update("incident_created", v)}
            />
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
            <ToggleRow
              label="メール通知を有効化"
              checked={settings.email}
              onChange={(v) => update("email", v)}
            />
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">送信先メールアドレス</label>
              <input
                type="email"
                placeholder="admin@example.com"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <p className="text-xs text-gray-400">※ メール送信機能は次バージョンで実装予定</p>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Webhook className="h-4 w-4 text-green-500" />
              ワークフロー通知
            </CardTitle>
          </CardHeader>
          <div className="space-y-1">
            <ToggleRow
              label="変更承認時"
              checked={settings.change_approved}
              onChange={(v) => update("change_approved", v)}
            />
            <ToggleRow
              label="サービスリクエスト完了時"
              checked={settings.sr_completed}
              onChange={(v) => update("sr_completed", v)}
            />
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Webhook className="h-4 w-4 text-purple-500" />
              Slack / Teams Webhook
            </CardTitle>
          </CardHeader>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Webhook URL</label>
              <input
                type="url"
                value={settings.webhook_url}
                onChange={(e) => update("webhook_url", e.target.value)}
                placeholder="https://hooks.slack.com/services/..."
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Webhookタイプ</label>
              <div className="flex gap-4">
                {(["slack", "teams"] as const).map((type) => (
                  <label key={type} className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="radio"
                      name="webhook_type"
                      value={type}
                      checked={settings.webhook_type === type}
                      onChange={() => update("webhook_type", type)}
                      className="accent-blue-600"
                    />
                    <span className="text-sm text-gray-700">
                      {type === "slack" ? "Slack" : "Microsoft Teams"}
                    </span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleTestWebhook}
                disabled={webhookTesting || !settings.webhook_url}
                className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200 disabled:opacity-50 transition"
              >
                {webhookTesting && <RefreshCw size={12} className="animate-spin" />}
                接続テスト
              </button>
              {webhookTestResult && (
                <span className={`text-sm ${webhookTestResult.success ? "text-green-600" : "text-red-600"}`}>
                  {webhookTestResult.success ? "✅" : "❌"} {webhookTestResult.message}
                </span>
              )}
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
          <div className="space-y-1">
            {[
              { label: "P1 エスカレーション時間", value: "15分" },
              { label: "P2 エスカレーション時間", value: "60分" },
              { label: "P3 エスカレーション時間", value: "4時間" },
              { label: "P4 エスカレーション時間", value: "24時間" },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between py-1.5">
                <span className="text-sm text-gray-700">{item.label}</span>
                <span className="text-sm font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                  {item.value}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

