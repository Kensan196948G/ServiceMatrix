/**
 * 変更管理ページ - Jira風リスト表示
 */
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Plus, Filter, RefreshCw, GitPullRequest, Shield, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import apiClient from "@/lib/api";
import Badge, { getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Select from "@/components/ui/Select";
import type { ChangeResponse, PaginatedResponse } from "@/types/api";

const PAGE_SIZE = 20;

const STATUS_OPTIONS = [
  { value: "", label: "すべてのステータス" },
  { value: "Pending", label: "Pending" },
  { value: "Approved", label: "Approved" },
  { value: "In_Progress", label: "In Progress" },
  { value: "Completed", label: "Completed" },
  { value: "Rejected", label: "Rejected" },
];

const TYPE_OPTIONS = [
  { value: "", label: "すべてのタイプ" },
  { value: "Standard", label: "Standard" },
  { value: "Normal", label: "Normal" },
  { value: "Emergency", label: "Emergency" },
  { value: "Major", label: "Major" },
];

function getRiskStyle(score: number) {
  if (score >= 70) return "bg-red-100 text-red-800 border border-red-200";
  if (score >= 40) return "bg-orange-100 text-orange-800 border border-orange-200";
  return "bg-green-100 text-green-700 border border-green-200";
}

function getRiskLabel(score: number) {
  if (score >= 70) return "高リスク";
  if (score >= 40) return "中リスク";
  return "低リスク";
}

export default function ChangesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", change_type: "Normal", implementation_plan: "", rollback_plan: "" });
  const [formError, setFormError] = useState("");

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["changes", page, filterStatus, filterType],
    queryFn: () => {
      const params: Record<string, string | number> = { page, size: PAGE_SIZE };
      if (filterStatus) params.status = filterStatus;
      if (filterType) params.change_type = filterType;
      return apiClient.get<PaginatedResponse<ChangeResponse> | ChangeResponse[]>("/changes", { params }).then(r => r.data);
    },
  });

  const createMutation = useMutation({
    mutationFn: (body: Record<string, string>) => apiClient.post("/changes", body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["changes"] });
      setShowCreate(false);
      setForm({ title: "", description: "", change_type: "Normal", implementation_plan: "", rollback_plan: "" });
      setFormError("");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "作成に失敗しました";
      setFormError(typeof msg === "string" ? msg : JSON.stringify(msg));
    },
  });

  const isPaginated = data && !Array.isArray(data) && "items" in data;
  const changes: ChangeResponse[] = isPaginated ? (data as PaginatedResponse<ChangeResponse>).items : (Array.isArray(data) ? data : []);
  const total = isPaginated ? (data as PaginatedResponse<ChangeResponse>).total : changes.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <GitPullRequest className="h-5 w-5 text-blue-500" />
            変更管理
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">全 {total} 件の変更要求</p>
        </div>
        <Button variant="primary" size="md" icon={<Plus className="h-4 w-4" />} onClick={() => setShowCreate(true)}>
          新規変更要求
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        <Filter className="h-4 w-4 text-gray-400" />
        <div className="w-44"><Select options={STATUS_OPTIONS} value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1); }} /></div>
        <div className="w-44"><Select options={TYPE_OPTIONS} value={filterType} onChange={e => { setFilterType(e.target.value); setPage(1); }} /></div>
        {(filterStatus || filterType) && (
          <button onClick={() => { setFilterStatus(""); setFilterType(""); setPage(1); }} className="text-xs text-blue-600 hover:text-blue-700 font-medium">リセット</button>
        )}
        <div className="ml-auto">
          <Button variant="ghost" size="sm" icon={<RefreshCw className="h-3.5 w-3.5" />} onClick={() => refetch()}>更新</Button>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex h-48 items-center justify-center"><LoadingSpinner size="lg" /></div>
        ) : error ? (
          <div className="flex h-48 items-center justify-center text-sm text-red-600"><XCircle className="mr-2 h-5 w-5 text-red-400" />取得に失敗しました</div>
        ) : changes.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2 text-gray-400"><CheckCircle2 className="h-8 w-8 text-green-400" /><p className="text-sm">変更要求はありません</p></div>
        ) : (
          <>
            <div className="grid grid-cols-[140px_1fr_110px_130px_90px_110px] gap-3 border-b border-gray-100 bg-gray-50 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
              <span>番号</span><span>タイトル</span><span>タイプ</span><span>ステータス</span><span>リスク</span><span>予定日</span>
            </div>
            {changes.map((c) => (
              <Link key={c.change_id} href={`/changes/${c.change_id}`} className="grid grid-cols-[140px_1fr_110px_130px_90px_110px] gap-3 items-center border-b border-gray-50 px-4 py-3 hover:bg-blue-50/40 transition-colors cursor-pointer last:border-0">
                <span className="font-mono text-xs text-gray-500">{c.change_number}</span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-800">{c.title}</p>
                  <p className="text-xs text-gray-400 truncate">{c.description?.slice(0, 50)}</p>
                </div>
                <span>
                  <Badge variant="info">{c.change_type}</Badge>
                </span>
                <span><Badge variant={getStatusVariant(c.status)}>{c.status.replace(/_/g, " ")}</Badge></span>
                <span>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${getRiskStyle(c.risk_score)}`}>
                    {c.risk_score}点
                  </span>
                </span>
                <span className="text-xs text-gray-400">
                  {c.scheduled_start_at ? new Date(c.scheduled_start_at).toLocaleDateString("ja-JP", { month: "short", day: "numeric" }) : "-"}
                </span>
              </Link>
            ))}
          </>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">{(page-1)*PAGE_SIZE+1}〜{Math.min(page*PAGE_SIZE,total)} 件 / 全 {total} 件</p>
          <div className="flex gap-1">
            <Button variant="secondary" size="sm" disabled={page===1} onClick={() => setPage(p=>p-1)}>前へ</Button>
            <span className="px-3 text-sm text-gray-600">{page}/{totalPages}</span>
            <Button variant="secondary" size="sm" disabled={page>=totalPages} onClick={() => setPage(p=>p+1)}>次へ</Button>
          </div>
        </div>
      )}

      <Modal isOpen={showCreate} onClose={() => { setShowCreate(false); setFormError(""); }} title="新規変更要求作成" size="lg">
        <div className="space-y-4">
          {formError && <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{formError}</div>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">タイトル <span className="text-red-500">*</span></label>
            <input type="text" value={form.title} onChange={e => setForm(f=>({...f,title:e.target.value}))} placeholder="変更要求の概要" className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">説明</label>
            <textarea value={form.description} onChange={e => setForm(f=>({...f,description:e.target.value}))} rows={3} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">変更タイプ</label>
              <select value={form.change_type} onChange={e => setForm(f=>({...f,change_type:e.target.value}))} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
                <option value="Standard">Standard</option>
                <option value="Normal">Normal</option>
                <option value="Emergency">Emergency</option>
                <option value="Major">Major</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">実装計画</label>
              <input type="text" value={form.implementation_plan} onChange={e => setForm(f=>({...f,implementation_plan:e.target.value}))} placeholder="実装手順の概要" className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ロールバック計画</label>
            <textarea value={form.rollback_plan} onChange={e => setForm(f=>({...f,rollback_plan:e.target.value}))} rows={2} placeholder="問題発生時のロールバック手順" className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => { setShowCreate(false); setFormError(""); }}>キャンセル</Button>
            <Button variant="primary" loading={createMutation.isPending} onClick={() => {
              if (!form.title.trim()) { setFormError("タイトルは必須です"); return; }
              createMutation.mutate({ title: form.title, description: form.description, change_type: form.change_type, ...(form.implementation_plan && { implementation_plan: form.implementation_plan }), ...(form.rollback_plan && { rollback_plan: form.rollback_plan }) });
            }}>変更要求を作成</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
