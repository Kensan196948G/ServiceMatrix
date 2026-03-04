/**
 * 問題管理ページ
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Filter, RefreshCw, HelpCircle, CheckCircle2, XCircle } from "lucide-react";
import apiClient from "@/lib/api";
import Badge, { getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Select from "@/components/ui/Select";

const PAGE_SIZE = 20;

const STATUS_OPTIONS = [
  { value: "", label: "すべてのステータス" },
  { value: "Open", label: "Open" },
  { value: "In_Progress", label: "In Progress" },
  { value: "Known_Error", label: "Known Error" },
  { value: "Resolved", label: "Resolved" },
  { value: "Closed", label: "Closed" },
];

interface ProblemItem {
  problem_id: string;
  problem_number: string;
  title: string;
  description?: string;
  status: string;
  known_error: boolean;
  root_cause?: string;
  workaround?: string;
  created_at: string;
}

export default function ProblemsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: "", description: "" });
  const [formError, setFormError] = useState("");

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["problems", page, filterStatus],
    queryFn: () => {
      const params: Record<string, string | number> = { page, size: PAGE_SIZE };
      if (filterStatus) params.status = filterStatus;
      return apiClient.get("/problems", { params }).then(r => r.data);
    },
  });

  const createMutation = useMutation({
    mutationFn: (body: Record<string, string>) => apiClient.post("/problems", body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["problems"] });
      setShowCreate(false);
      setForm({ title: "", description: "" });
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "作成に失敗しました";
      setFormError(typeof msg === "string" ? msg : JSON.stringify(msg));
    },
  });

  const problems: ProblemItem[] = data?.items ?? data ?? [];
  const total = data?.total ?? problems.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <HelpCircle className="h-5 w-5 text-purple-500" />
            問題管理
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">全 {total} 件の問題</p>
        </div>
        <Button variant="primary" size="md" icon={<Plus className="h-4 w-4" />} onClick={() => setShowCreate(true)}>
          新規問題登録
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        <Filter className="h-4 w-4 text-gray-400" />
        <div className="w-44"><Select options={STATUS_OPTIONS} value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1); }} /></div>
        {filterStatus && <button onClick={() => { setFilterStatus(""); setPage(1); }} className="text-xs text-blue-600 font-medium">リセット</button>}
        <div className="ml-auto"><Button variant="ghost" size="sm" icon={<RefreshCw className="h-3.5 w-3.5" />} onClick={() => refetch()}>更新</Button></div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex h-48 items-center justify-center"><LoadingSpinner size="lg" /></div>
        ) : error ? (
          <div className="flex h-48 items-center justify-center text-sm text-red-600"><XCircle className="mr-2 h-5 w-5" />取得に失敗</div>
        ) : problems.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2 text-gray-400"><CheckCircle2 className="h-8 w-8 text-green-400" /><p className="text-sm">問題はありません</p></div>
        ) : (
          <>
            <div className="grid grid-cols-[140px_1fr_130px_90px_120px] gap-3 border-b border-gray-100 bg-gray-50 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
              <span>番号</span><span>タイトル</span><span>ステータス</span><span>既知エラー</span><span>作成日時</span>
            </div>
            {problems.map((p) => (
              <Link key={p.problem_id} href={`/problems/${p.problem_id}`} className="grid grid-cols-[140px_1fr_130px_90px_120px] gap-3 items-center border-b border-gray-50 px-4 py-3 hover:bg-blue-50/40 transition-colors cursor-pointer last:border-0">
                <span className="font-mono text-xs text-gray-500">{p.problem_number}</span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-800">{p.title}</p>
                  {p.root_cause && <p className="truncate text-xs text-gray-400">根本原因: {p.root_cause}</p>}
                </div>
                <span><Badge variant={getStatusVariant(p.status)}>{p.status.replace(/_/g, " ")}</Badge></span>
                <span>{p.known_error ? <Badge variant="warning">既知</Badge> : <span className="text-xs text-gray-400">-</span>}</span>
                <span className="text-xs text-gray-400">{new Date(p.created_at).toLocaleDateString("ja-JP", { month: "short", day: "numeric" })}</span>
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

      <Modal isOpen={showCreate} onClose={() => { setShowCreate(false); setFormError(""); }} title="新規問題登録" size="md">
        <div className="space-y-4">
          {formError && <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{formError}</div>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">タイトル <span className="text-red-500">*</span></label>
            <input type="text" value={form.title} onChange={e => setForm(f=>({...f,title:e.target.value}))} placeholder="問題の概要" className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">説明</label>
            <textarea value={form.description} onChange={e => setForm(f=>({...f,description:e.target.value}))} rows={3} className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => { setShowCreate(false); setFormError(""); }}>キャンセル</Button>
            <Button variant="primary" loading={createMutation.isPending} onClick={() => {
              if (!form.title.trim()) { setFormError("タイトルは必須です"); return; }
              createMutation.mutate({ title: form.title, description: form.description });
            }}>問題を登録</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
