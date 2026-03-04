/**
 * 統合設定ページ - Jira/ServiceNow統合フレームワーク
 */
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plug,
  Plus,
  Trash2,
  CheckCircle,
  XCircle,
  RefreshCw,
  Settings,
  Activity,
} from "lucide-react";
import apiClient from "@/lib/api";

interface IntegrationConfig {
  config_id: string;
  integration_type: string;
  name: string;
  base_url: string | null;
  username: string | null;
  is_active: boolean;
  sync_interval_minutes: number;
  last_synced_at: string | null;
  created_at: string | null;
}

interface CreatePayload {
  integration_type: string;
  name: string;
  base_url: string;
  api_key: string;
  username: string;
  webhook_secret: string;
  is_active: boolean;
  sync_interval_minutes: number;
}

const TYPE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  jira: { label: "Jira", color: "text-blue-700", bg: "bg-blue-50" },
  servicenow: { label: "ServiceNow", color: "text-purple-700", bg: "bg-purple-50" },
  custom: { label: "カスタム", color: "text-gray-700", bg: "bg-gray-100" },
};

const EMPTY_FORM: CreatePayload = {
  integration_type: "jira",
  name: "",
  base_url: "",
  api_key: "",
  username: "",
  webhook_secret: "",
  is_active: true,
  sync_interval_minutes: 30,
};

export default function IntegrationsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreatePayload>(EMPTY_FORM);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});

  const { data: integrations = [], isLoading } = useQuery<IntegrationConfig[]>({
    queryKey: ["integrations"],
    queryFn: async () => {
      const res = await apiClient.get("/integrations");
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreatePayload) => apiClient.post("/integrations", payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["integrations"] });
      setShowForm(false);
      setForm(EMPTY_FORM);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/integrations/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations"] }),
  });

  const handleTest = async (id: string) => {
    try {
      const res = await apiClient.post(`/integrations/${id}/test`);
      setTestResults((prev) => ({ ...prev, [id]: { success: true, message: res.data.message } }));
    } catch {
      setTestResults((prev) => ({ ...prev, [id]: { success: false, message: "接続テストに失敗しました" } }));
    }
  };

  const handleToggle = async (cfg: IntegrationConfig) => {
    await apiClient.patch(`/integrations/${cfg.config_id}`, { is_active: !cfg.is_active });
    qc.invalidateQueries({ queryKey: ["integrations"] });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Plug className="h-5 w-5 text-gray-600" />
          <h1 className="text-xl font-semibold text-gray-800">外部統合</h1>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          統合を追加
        </button>
      </div>

      {/* Integrations List */}
      {isLoading ? (
        <div className="py-8 text-center text-sm text-gray-400">読み込み中...</div>
      ) : integrations.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 py-12 text-center">
          <Plug className="mx-auto mb-3 h-8 w-8 text-gray-300" />
          <p className="text-sm text-gray-500">統合設定がありません</p>
          <p className="mt-1 text-xs text-gray-400">「統合を追加」ボタンから Jira または ServiceNow を設定できます</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {integrations.map((cfg) => {
            const meta = TYPE_LABELS[cfg.integration_type] ?? TYPE_LABELS.custom;
            const testResult = testResults[cfg.config_id];
            return (
              <div key={cfg.config_id} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${meta.bg} ${meta.color}`}>
                      {meta.label}
                    </span>
                    <span className="font-medium text-gray-800">{cfg.name}</span>
                  </div>
                  <button
                    onClick={() => deleteMutation.mutate(cfg.config_id)}
                    className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                {cfg.base_url && (
                  <p className="mt-2 truncate text-xs text-gray-400">{cfg.base_url}</p>
                )}

                <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Activity className="h-3 w-3" />
                    {cfg.sync_interval_minutes}分毎に同期
                  </span>
                  {cfg.last_synced_at && (
                    <span>最終: {new Date(cfg.last_synced_at).toLocaleString("ja-JP")}</span>
                  )}
                </div>

                {testResult && (
                  <div className={`mt-2 flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs ${testResult.success ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
                    {testResult.success ? (
                      <CheckCircle className="h-3.5 w-3.5 flex-shrink-0" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 flex-shrink-0" />
                    )}
                    {testResult.message}
                  </div>
                )}

                <div className="mt-4 flex items-center gap-2">
                  <button
                    onClick={() => handleTest(cfg.config_id)}
                    className="flex items-center gap-1.5 rounded-md border border-gray-200 px-2.5 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
                  >
                    <RefreshCw className="h-3 w-3" />
                    接続テスト
                  </button>
                  <button
                    onClick={() => handleToggle(cfg)}
                    className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium ${
                      cfg.is_active
                        ? "bg-green-50 text-green-700 hover:bg-green-100"
                        : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                    }`}
                  >
                    {cfg.is_active ? "有効" : "無効"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4">
          <div className="w-full max-w-lg rounded-xl bg-white shadow-2xl ring-1 ring-gray-200">
            <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4 text-gray-500" />
                <h2 className="font-semibold text-gray-800">統合を追加</h2>
              </div>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>

            <div className="space-y-4 px-5 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">統合タイプ</label>
                  <select
                    value={form.integration_type}
                    onChange={(e) => setForm((f) => ({ ...f, integration_type: e.target.value }))}
                    className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
                  >
                    <option value="jira">Jira</option>
                    <option value="servicenow">ServiceNow</option>
                    <option value="custom">カスタム</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">表示名 *</label>
                  <input
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder="本番Jira環境"
                    className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">ベースURL</label>
                <input
                  value={form.base_url}
                  onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))}
                  placeholder="https://your-instance.atlassian.net"
                  className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">ユーザー名</label>
                  <input
                    value={form.username}
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                    className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">APIキー</label>
                  <input
                    type="password"
                    value={form.api_key}
                    onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
                    className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">Webhookシークレット</label>
                  <input
                    type="password"
                    value={form.webhook_secret}
                    onChange={(e) => setForm((f) => ({ ...f, webhook_secret: e.target.value }))}
                    className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">同期間隔（分）</label>
                  <input
                    type="number"
                    value={form.sync_interval_minutes}
                    onChange={(e) => setForm((f) => ({ ...f, sync_interval_minutes: Number(e.target.value) }))}
                    min={5}
                    className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t border-gray-100 px-5 py-4">
              <button
                onClick={() => setShowForm(false)}
                className="rounded-md border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                キャンセル
              </button>
              <button
                onClick={() => createMutation.mutate(form)}
                disabled={!form.name || createMutation.isPending}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {createMutation.isPending ? "追加中..." : "追加"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
