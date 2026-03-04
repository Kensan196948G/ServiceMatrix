/**
 * サービスリクエストページ
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Filter, RefreshCw, ClipboardList, CheckCircle2, XCircle } from "lucide-react";
import apiClient from "@/lib/api";
import Badge, { getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Select from "@/components/ui/Select";

const PAGE_SIZE = 20;

const STATUS_OPTIONS = [
  { value: "", label: "すべてのステータス" },
  { value: "New", label: "New" },
  { value: "In_Progress", label: "In Progress" },
  { value: "Pending_Approval", label: "Pending Approval" },
  { value: "Completed", label: "Completed" },
  { value: "Cancelled", label: "Cancelled" },
];

interface SRItem {
  request_id: string;
  request_number: string;
  title: string;
  description?: string;
  status: string;
  priority?: string;
  created_at: string;
}

export default function ServiceRequestsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", priority: "P3" });
  const [formError, setFormError] = useState("");

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["service-requests", page, filterStatus],
    queryFn: () => {
      const params: Record<string, string | number> = { page, size: PAGE_SIZE };
      if (filterStatus) params.status = filterStatus;
      return apiClient.get("/service-requests", { params }).then(r => r.data);
    },
  });

  const createMutation = useMutation({
    mutationFn: (body: Record<string, string>) => apiClient.post("/service-requests", body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["service-requests"] });
      setShowCreate(false);
      setForm({ title: "", description: "", priority: "P3" });
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "作成に失敗しました";
      setFormError(typeof msg === "string" ? msg : JSON.stringify(msg));
    },
  });

  const requests: SRItem[] = data?.items ?? data ?? [];
  const total = data?.total ?? requests.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-green-500" />
            サービスリクエスト
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">全 {total} 件のリクエスト</p>
        </div>
        <Button variant="primary" size="md" icon={<Plus className="h-4 w-4" />} onClick={() => setShowCreate(true)}>
          新規リクエスト
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        <Filter className="h-4 w-4 text-gray-400" />
        <div className="w-48"><Select options={STATUS_OPTIONS} value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1); }} /></div>
        {filterStatus && <button onClick={() => { setFilterStatus(""); setPage(1); }} className="text-xs text-blue-600 font-medium">リセット</button>}
        <div className="ml-auto"><Button variant="ghost" size="sm" icon={<RefreshCw className="h-3.5 w-3.5" />} onClick={() => refetch()}>更新</Button></div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex h-48 items-center justify-center"><LoadingSpinner size="lg" /></div>
        ) : error ? (
          <div className="flex h-48 items-center justify-center text-sm text-red-600"><XCircle className="mr-2 h-5 w-5" />取得に失敗</div>
        ) : requests.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2 text-gray-400"><CheckCircle2 className="h-8 w-8 text-green-400" /><p className="text-sm">リクエストはありません</p></div>
        ) : (
          <>
            <div className="grid grid-cols-[140px_1fr_90px_150px_120px] gap-3 border-b border-gray-100 bg-gray-50 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
              <span>番号</span><span>タイトル</span><span>優先度</span><span>ステータス</span><span>作成日時</span>
            </div>
            {requests.map((req) => (
              <Link key={req.request_id} href={`/service-requests/${req.request_id}`} className="grid grid-cols-[140px_1fr_90px_150px_120px] gap-3 items-center border-b border-gray-50 px-4 py-3 hover:bg-blue-50/40 transition-colors cursor-pointer last:border-0">
                <span className="font-mono text-xs text-gray-500">{req.request_number}</span>
                <p className="truncate text-sm font-medium text-gray-800">{req.title}</p>
                <span className="text-xs text-gray-500">{req.priority ?? "P3"}</span>
                <span><Badge variant={getStatusVariant(req.status)}>{req.status.replace(/_/g, " ")}</Badge></span>
                <span className="text-xs text-gray-400">{new Date(req.created_at).toLocaleDateString("ja-JP", { month: "short", day: "numeric" })}</span>
              </Link>
            ))}
          </>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">全 {total} 件</p>
          <div className="flex gap-1">
            <Button variant="secondary" size="sm" disabled={page===1} onClick={() => setPage(p=>p-1)}>前へ</Button>
            <span className="px-3 text-sm text-gray-600">{page}/{totalPages}</span>
            <Button variant="secondary" size="sm" disabled={page>=totalPages} onClick={() => setPage(p=>p+1)}>次へ</Button>
          </div>
        </div>
      )}

      <Modal isOpen={showCreate} onClose={() => { setShowCreate(false); setFormError(""); }} title="新規サービスリクエスト" size="md">
        <div className="space-y-4">
          {formError && <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{formError}</div>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">タイトル <span className="text-red-500">*</span></label>
            <input type="text" value={form.title} onChange={e => setForm(f=>({...f,title:e.target.value}))} placeholder="リクエストの概要" className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">説明</label>
            <textarea value={form.description} onChange={e => setForm(f=>({...f,description:e.target.value}))} rows={3} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">優先度</label>
            <select value={form.priority} onChange={e => setForm(f=>({...f,priority:e.target.value}))} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
              <option value="P1">P1 - 緊急</option>
              <option value="P2">P2 - 高</option>
              <option value="P3">P3 - 中</option>
              <option value="P4">P4 - 低</option>
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => { setShowCreate(false); setFormError(""); }}>キャンセル</Button>
            <Button variant="primary" loading={createMutation.isPending} onClick={() => {
              if (!form.title.trim()) { setFormError("タイトルは必須です"); return; }
              createMutation.mutate({ title: form.title, description: form.description, priority: form.priority });
            }}>リクエストを作成</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
