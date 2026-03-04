/**
 * インシデント管理ページ - Jira風リスト表示
 * フィルタ・ソート・ページネーション・新規作成モーダル
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Filter, RefreshCw, AlertTriangle, Clock, CheckCircle2, XCircle, CheckSquare, Square } from "lucide-react";
import apiClient from "@/lib/api";
import Badge, { getPriorityVariant, getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Select from "@/components/ui/Select";
import type { IncidentResponse, PaginatedResponse } from "@/types/api";

const PAGE_SIZE = 20;

const PRIORITY_LABELS: Record<string, string> = {
  P1: "P1 - 緊急",
  P2: "P2 - 高",
  P3: "P3 - 中",
  P4: "P4 - 低",
};

const STATUS_OPTIONS = [
  { value: "", label: "すべてのステータス" },
  { value: "New", label: "New" },
  { value: "Acknowledged", label: "Acknowledged" },
  { value: "In_Progress", label: "In Progress" },
  { value: "Resolved", label: "Resolved" },
  { value: "Closed", label: "Closed" },
];

const PRIORITY_OPTIONS = [
  { value: "", label: "すべての優先度" },
  { value: "P1", label: "P1 - 緊急" },
  { value: "P2", label: "P2 - 高" },
  { value: "P3", label: "P3 - 中" },
  { value: "P4", label: "P4 - 低" },
];

interface CreateIncidentForm {
  title: string;
  description: string;
  priority: string;
  category: string;
  affected_service: string;
}

export default function IncidentsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterPriority, setFilterPriority] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateIncidentForm>({
    title: "", description: "", priority: "P3", category: "", affected_service: "",
  });
  const [formError, setFormError] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkStatus, setBulkStatus] = useState("");
  const [bulkAssignee, setBulkAssignee] = useState("");

  const queryKey = ["incidents", page, filterStatus, filterPriority];
  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: () => {
      const params: Record<string, string | number> = { page, size: PAGE_SIZE };
      if (filterStatus) params.status = filterStatus;
      if (filterPriority) params.priority = filterPriority;
      return apiClient.get<PaginatedResponse<IncidentResponse>>("/incidents", { params }).then(r => r.data);
    },
    retry: 1,
  });

  const createMutation = useMutation({
    mutationFn: (body: Record<string, string>) => apiClient.post("/incidents", body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      setShowCreate(false);
      setForm({ title: "", description: "", priority: "P3", category: "", affected_service: "" });
      setFormError("");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "作成に失敗しました";
      setFormError(typeof msg === "string" ? msg : JSON.stringify(msg));
    },
  });

  const incidents: IncidentResponse[] = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const allSelected = incidents.length > 0 && incidents.every(i => selectedIds.has(i.incident_id));
  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(incidents.map(i => i.incident_id)));
    }
  };
  const toggleOne = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const bulkTransitionMutation = useMutation({
    mutationFn: async (newStatus: string) => {
      await Promise.all(
        Array.from(selectedIds).map(id =>
          apiClient.post(`/incidents/${id}/transitions`, { new_status: newStatus })
        )
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      setSelectedIds(new Set());
      setBulkStatus("");
    },
  });

  const bulkAssignMutation = useMutation({
    mutationFn: async (assignee: string) => {
      await apiClient.patch("/incidents/bulk/assign", {
        incident_ids: Array.from(selectedIds),
        assigned_to: assignee || null,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      setSelectedIds(new Set());
      setBulkAssignee("");
    },
  });

  const handleCreate = () => {
    if (!form.title.trim()) { setFormError("タイトルは必須です"); return; }
    createMutation.mutate({
      title: form.title,
      description: form.description,
      priority: form.priority,
      ...(form.category && { category: form.category }),
      ...(form.affected_service && { affected_service: form.affected_service }),
    });
  };

  const priorityBadgeStyle: Record<string, string> = {
    P1: "bg-red-100 text-red-800 border border-red-200",
    P2: "bg-orange-100 text-orange-800 border border-orange-200",
    P3: "bg-yellow-100 text-yellow-800 border border-yellow-200",
    P4: "bg-gray-100 text-gray-700 border border-gray-200",
  };

  return (
    <div className="space-y-4">
      {/* ページヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            インシデント管理
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">全 {total} 件のインシデント</p>
        </div>
        <Button
          variant="primary"
          size="md"
          icon={<Plus className="h-4 w-4" />}
          onClick={() => setShowCreate(true)}
        >
          新規インシデント
        </Button>
      </div>

      {/* フィルタバー */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        <Filter className="h-4 w-4 text-gray-400 flex-shrink-0" />
        <div className="w-44">
          <Select
            options={STATUS_OPTIONS}
            value={filterStatus}
            onChange={e => { setFilterStatus(e.target.value); setPage(1); }}
          />
        </div>
        <div className="w-44">
          <Select
            options={PRIORITY_OPTIONS}
            value={filterPriority}
            onChange={e => { setFilterPriority(e.target.value); setPage(1); }}
          />
        </div>
        {(filterStatus || filterPriority) && (
          <button
            onClick={() => { setFilterStatus(""); setFilterPriority(""); setPage(1); }}
            className="text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            フィルタをリセット
          </button>
        )}
        <div className="ml-auto">
          <Button variant="ghost" size="sm" icon={<RefreshCw className="h-3.5 w-3.5" />} onClick={() => refetch()}>
            更新
          </Button>
        </div>
      </div>

      {/* インシデントリスト */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex h-48 items-center justify-center">
            <LoadingSpinner size="lg" message="インシデントを読み込み中..." />
          </div>
        ) : error ? (
          <div className="flex h-48 items-center justify-center">
            <div className="text-center text-sm text-red-600">
              <XCircle className="mx-auto mb-2 h-8 w-8 text-red-400" />
              インシデントの取得に失敗しました
            </div>
          </div>
        ) : incidents.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2 text-gray-400">
            <CheckCircle2 className="h-8 w-8 text-green-400" />
            <p className="text-sm">インシデントはありません</p>
          </div>
        ) : (
          <>
            {/* 一括操作バー */}
            {selectedIds.size > 0 && (
              <div className="flex flex-wrap items-center gap-3 bg-blue-50 border-b border-blue-200 px-4 py-2.5">
                <span className="text-sm font-medium text-blue-700">{selectedIds.size}件選択中</span>
                {/* 一括ステータス変更 */}
                <select
                  value={bulkStatus}
                  onChange={e => setBulkStatus(e.target.value)}
                  className="rounded border border-blue-300 px-2 py-1 text-xs text-blue-800 bg-white"
                >
                  <option value="">ステータスを変更...</option>
                  <option value="Acknowledged">Acknowledged</option>
                  <option value="In_Progress">In Progress</option>
                  <option value="Resolved">Resolved</option>
                  <option value="Closed">Closed</option>
                </select>
                <button
                  disabled={!bulkStatus || bulkTransitionMutation.isPending}
                  onClick={() => bulkTransitionMutation.mutate(bulkStatus)}
                  className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {bulkTransitionMutation.isPending ? "処理中..." : "一括変更"}
                </button>
                {/* 一括担当者割り当て */}
                <span className="text-blue-300">|</span>
                <input
                  type="text"
                  value={bulkAssignee}
                  onChange={e => setBulkAssignee(e.target.value)}
                  placeholder="担当者UUID..."
                  className="rounded border border-blue-300 px-2 py-1 text-xs bg-white w-56"
                />
                <button
                  disabled={!bulkAssignee || bulkAssignMutation.isPending}
                  onClick={() => bulkAssignMutation.mutate(bulkAssignee)}
                  className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {bulkAssignMutation.isPending ? "処理中..." : "一括割り当て"}
                </button>
                <button
                  onClick={() => setSelectedIds(new Set())}
                  className="px-3 py-1 text-blue-600 text-xs hover:underline ml-auto"
                >
                  選択解除
                </button>
              </div>
            )}

            {/* テーブルヘッダー */}
            <div className="grid grid-cols-[32px_140px_1fr_90px_130px_90px_110px_80px] gap-3 border-b border-gray-100 bg-gray-50 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
              <span>
                <button onClick={toggleAll} className="text-gray-400 hover:text-gray-700">
                  {allSelected ? <CheckSquare className="h-4 w-4 text-blue-600" /> : <Square className="h-4 w-4" />}
                </button>
              </span>
              <span>番号</span>
              <span>タイトル</span>
              <span>優先度</span>
              <span>ステータス</span>
              <span>SLA</span>
              <span>作成日時</span>
              <span></span>
            </div>

            {/* テーブル行 */}
            {incidents.map((incident) => (
              <div
                key={incident.incident_id}
                className={`grid grid-cols-[32px_140px_1fr_90px_130px_90px_110px_80px] gap-3 items-center border-b border-gray-50 px-4 py-3 hover:bg-blue-50/40 transition-colors last:border-0 ${selectedIds.has(incident.incident_id) ? "bg-blue-50/60" : ""}`}
              >
                <span>
                  <button
                    onClick={e => { e.preventDefault(); toggleOne(incident.incident_id); }}
                    className="text-gray-400 hover:text-blue-600"
                  >
                    {selectedIds.has(incident.incident_id)
                      ? <CheckSquare className="h-4 w-4 text-blue-600" />
                      : <Square className="h-4 w-4" />}
                  </button>
                </span>
                <span className="font-mono text-xs text-gray-500">{incident.incident_number}</span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-800">{incident.title}</p>
                  {incident.affected_service && (
                    <p className="truncate text-xs text-gray-400">{incident.affected_service}</p>
                  )}
                </div>
                <span>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${priorityBadgeStyle[incident.priority] ?? "bg-gray-100 text-gray-600"}`}>
                    {incident.priority}
                  </span>
                </span>
                <span>
                  <Badge variant={getStatusVariant(incident.status)}>
                    {incident.status.replace(/_/g, " ")}
                  </Badge>
                </span>
                <span>
                  {incident.sla_breached ? (
                    <span className="flex items-center gap-1 text-xs text-red-600 font-medium">
                      <XCircle className="h-3.5 w-3.5" /> 超過
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-green-600">
                      <Clock className="h-3.5 w-3.5" /> 遵守
                    </span>
                  )}
                </span>
                <span className="text-xs text-gray-400">
                  {new Date(incident.created_at).toLocaleDateString("ja-JP", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                </span>
                <span>
                  <Link
                    href={`/incidents/${incident.incident_id}`}
                    className="text-xs text-blue-600 hover:text-blue-800 hover:underline font-medium"
                  >
                    詳細を見る
                  </Link>
                </span>
              </div>
            ))}
          </>
        )}
      </div>

      {/* ページネーション */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {(page - 1) * PAGE_SIZE + 1}〜{Math.min(page * PAGE_SIZE, total)} 件 / 全 {total} 件
          </p>
          <div className="flex items-center gap-1">
            <Button variant="secondary" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>前へ</Button>
            <span className="px-3 text-sm text-gray-600">{page} / {totalPages}</span>
            <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>次へ</Button>
          </div>
        </div>
      )}

      {/* 新規作成モーダル */}
      <Modal isOpen={showCreate} onClose={() => { setShowCreate(false); setFormError(""); }} title="新規インシデント作成" size="lg">
        <div className="space-y-4">
          {formError && (
            <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{formError}</div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">タイトル <span className="text-red-500">*</span></label>
            <input
              type="text"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="インシデントの概要を入力"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">説明</label>
            <textarea
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="詳細な説明を入力"
              rows={3}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">優先度</label>
              <select
                value={form.priority}
                onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {Object.entries(PRIORITY_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">カテゴリ</label>
              <input
                type="text"
                value={form.category}
                onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                placeholder="例: Network, Server, Application"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">影響サービス</label>
            <input
              type="text"
              value={form.affected_service}
              onChange={e => setForm(f => ({ ...f, affected_service: e.target.value }))}
              placeholder="例: 受発注システム, メールサービス"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => { setShowCreate(false); setFormError(""); }}>キャンセル</Button>
            <Button variant="primary" loading={createMutation.isPending} onClick={handleCreate}>
              インシデントを作成
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
