/**
 * メンテナンスウィンドウ管理ページ
 */
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Wrench, Plus, Clock, CheckCircle2, XCircle, AlertTriangle, X } from "lucide-react";
import apiClient from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

interface MaintenanceWindow {
  window_id: string;
  name: string;
  description?: string;
  start_time: string;
  end_time: string;
  is_recurring: boolean;
  recurrence_rule?: string;
  is_active: boolean;
  created_by?: string;
  created_at: string;
}

interface CreateForm {
  name: string;
  description: string;
  start_time: string;
  end_time: string;
  is_recurring: boolean;
  recurrence_rule: string;
}

const EMPTY_FORM: CreateForm = {
  name: "",
  description: "",
  start_time: "",
  end_time: "",
  is_recurring: false,
  recurrence_rule: "",
};

function formatDT(dt: string) {
  return new Date(dt).toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function isCurrentlyActive(w: MaintenanceWindow) {
  const now = Date.now();
  return (
    w.is_active &&
    new Date(w.start_time).getTime() <= now &&
    new Date(w.end_time).getTime() >= now
  );
}

export default function MaintenancePage() {
  const queryClient = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<CreateForm>(EMPTY_FORM);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: windows = [], isLoading } = useQuery<MaintenanceWindow[]>({
    queryKey: ["maintenance-windows"],
    queryFn: () => apiClient.get("/maintenance-windows").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<CreateForm>) =>
      apiClient.post("/maintenance-windows", data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["maintenance-windows"] });
      setShowModal(false);
      setForm(EMPTY_FORM);
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "作成に失敗しました";
      setErrorMsg(typeof msg === "string" ? msg : JSON.stringify(msg));
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient.patch(`/maintenance-windows/${id}`, { is_active: false }).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["maintenance-windows"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient.delete(`/maintenance-windows/${id}`).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["maintenance-windows"] }),
  });

  const activeNow = windows.filter(isCurrentlyActive);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    const payload: Record<string, unknown> = {
      name: form.name,
      start_time: form.start_time,
      end_time: form.end_time,
      is_recurring: form.is_recurring,
    };
    if (form.description) payload.description = form.description;
    if (form.recurrence_rule) payload.recurrence_rule = form.recurrence_rule;
    createMutation.mutate(payload);
  };

  return (
    <div className="p-6 space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wrench className="h-6 w-6 text-orange-500" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">メンテナンスウィンドウ管理</h1>
            <p className="text-sm text-gray-500 mt-0.5">変更禁止期間・定期メンテナンスの設定</p>
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 transition"
        >
          <Plus className="h-4 w-4" />
          新規作成
        </button>
      </div>

      {/* アクティブバナー */}
      {activeNow.length > 0 && (
        <div className="rounded-lg bg-red-50 border border-red-300 p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-semibold text-red-800">🔴 現在メンテナンス中です</p>
            <ul className="mt-1 space-y-0.5">
              {activeNow.map((w) => (
                <li key={w.window_id} className="text-sm text-red-700">
                  {w.name} — {formatDT(w.start_time)} 〜 {formatDT(w.end_time)}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* 一覧テーブル */}
      {isLoading ? (
        <LoadingSpinner />
      ) : windows.length === 0 ? (
        <div className="rounded-lg bg-gray-50 border border-gray-200 p-12 text-center text-gray-400">
          <Wrench className="h-12 w-12 mx-auto mb-3 opacity-40" />
          <p className="text-sm">メンテナンスウィンドウがありません</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">名前</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">開始</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">終了</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">繰り返し</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">状態</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {windows.map((w) => {
                const active = isCurrentlyActive(w);
                return (
                  <tr key={w.window_id} className={active ? "bg-red-50" : ""}>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{w.name}</p>
                      {w.description && (
                        <p className="text-xs text-gray-500 mt-0.5 truncate max-w-xs">
                          {w.description}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5 text-gray-400" />
                        {formatDT(w.start_time)}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5 text-gray-400" />
                        {formatDT(w.end_time)}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {w.is_recurring ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                          繰り返し
                          {w.recurrence_rule && (
                            <span className="opacity-70">({w.recurrence_rule})</span>
                          )}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">なし</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {active ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                          <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
                          実施中
                        </span>
                      ) : w.is_active ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">
                          <CheckCircle2 className="h-3 w-3" />
                          有効
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs">
                          <XCircle className="h-3 w-3" />
                          無効
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {w.is_active && (
                          <button
                            onClick={() => deactivateMutation.mutate(w.window_id)}
                            className="text-xs text-gray-500 hover:text-orange-600 transition"
                          >
                            無効化
                          </button>
                        )}
                        <button
                          onClick={() => deleteMutation.mutate(w.window_id)}
                          className="text-xs text-red-400 hover:text-red-600 transition"
                        >
                          削除
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* 新規作成モーダル */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <Wrench className="h-4 w-4 text-orange-500" />
                メンテナンスウィンドウ新規作成
              </h2>
              <button onClick={() => setShowModal(false)}>
                <X className="h-5 w-5 text-gray-400 hover:text-gray-600" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  名前 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
                  placeholder="例: 月次定期メンテナンス"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">説明</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  rows={2}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
                  placeholder="メンテナンスの内容・影響範囲"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    開始日時 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={form.start_time}
                    onChange={(e) => setForm((f) => ({ ...f, start_time: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    終了日時 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={form.end_time}
                    onChange={(e) => setForm((f) => ({ ...f, end_time: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
                  />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="is_recurring"
                  checked={form.is_recurring}
                  onChange={(e) => setForm((f) => ({ ...f, is_recurring: e.target.checked }))}
                  className="h-4 w-4 rounded border-gray-300 text-orange-500"
                />
                <label htmlFor="is_recurring" className="text-sm text-gray-700">
                  定期繰り返し
                </label>
              </div>

              {form.is_recurring && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    繰り返しルール（RRULE形式）
                  </label>
                  <input
                    type="text"
                    value={form.recurrence_rule}
                    onChange={(e) => setForm((f) => ({ ...f, recurrence_rule: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
                    placeholder="例: FREQ=MONTHLY;BYDAY=1SU"
                  />
                </div>
              )}

              {errorMsg && (
                <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{errorMsg}</p>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setForm(EMPTY_FORM);
                    setErrorMsg(null);
                  }}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition"
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex items-center gap-2 px-5 py-2 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50 transition"
                >
                  {createMutation.isPending ? "作成中..." : "作成"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
