"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  User,
  FileText,
  ChevronDown,
  Loader2,
  ThumbsUp,
  ThumbsDown,
  Play,
  Flag,
} from "lucide-react";
import apiClient from "@/lib/api";

interface ServiceRequest {
  request_id: string;
  request_number: string;
  title: string;
  description: string | null;
  status: string;
  request_type: string | null;
  requested_by: string | null;
  assigned_to: string | null;
  approved_by: string | null;
  due_date: string | null;
  fulfilled_at: string | null;
  created_at: string;
  updated_at: string;
}

const statusColors: Record<string, string> = {
  New: "bg-gray-100 text-gray-800",
  Pending_Approval: "bg-yellow-100 text-yellow-800",
  Approved: "bg-blue-100 text-blue-800",
  In_Progress: "bg-indigo-100 text-indigo-800",
  In_Fulfillment: "bg-purple-100 text-purple-800",
  Fulfilled: "bg-green-100 text-green-800",
  Failed: "bg-red-100 text-red-800",
  Rejected: "bg-red-100 text-red-700",
  Cancelled: "bg-gray-200 text-gray-600",
  Closed: "bg-gray-200 text-gray-600",
};

const statusLabels: Record<string, string> = {
  New: "新規",
  Pending_Approval: "承認待ち",
  Approved: "承認済み",
  In_Progress: "対応中",
  In_Fulfillment: "フルフィルメント中",
  Fulfilled: "完了",
  Failed: "失敗",
  Rejected: "却下",
  Cancelled: "キャンセル",
  Closed: "クローズ",
};

const VALID_TRANSITIONS: Record<string, string[]> = {
  New: ["Pending_Approval", "In_Progress"],
  Pending_Approval: ["Approved", "Rejected"],
  Approved: ["In_Progress", "In_Fulfillment"],
  In_Progress: ["Fulfilled", "Cancelled"],
  In_Fulfillment: ["Fulfilled", "Failed"],
  Fulfilled: ["Closed"],
  Failed: ["Closed"],
  Rejected: ["Cancelled", "Closed"],
  Cancelled: [],
  Closed: [],
};

export default function ServiceRequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showTransition, setShowTransition] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState("");
  const [comment, setComment] = useState("");
  const [approvalComment, setApprovalComment] = useState("");
  const [actorName, setActorName] = useState("管理者");

  const { data: sr, isLoading, isError } = useQuery<ServiceRequest>({
    queryKey: ["service-request", id],
    queryFn: async () => {
      const res = await apiClient.get(`/service-requests/${id}`);
      return res.data;
    },
    refetchInterval: 30000,
  });

  const transitionMutation = useMutation({
    mutationFn: async ({ target, cmt }: { target: string; cmt: string }) => {
      const res = await apiClient.post(`/service-requests/${id}/transitions`, {
        target_status: target,
        comment: cmt,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["service-request", id] });
      setShowTransition(false);
      setSelectedStatus("");
      setComment("");
    },
  });

  const approveMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/service-requests/${id}/approve`, {
        actor: actorName,
        comment: approvalComment,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["service-request", id] });
      setApprovalComment("");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/service-requests/${id}/reject`, {
        actor: actorName,
        comment: approvalComment,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["service-request", id] });
      setApprovalComment("");
    },
  });

  const startMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/service-requests/${id}/start`);
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["service-request", id] }),
  });

  const completeMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/service-requests/${id}/complete`, { success: true });
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["service-request", id] }),
  });

  const submitMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/service-requests/${id}/submit`);
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["service-request", id] }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (isError || !sr) {
    return (
      <div className="text-center py-16 text-gray-500">
        <AlertCircle className="h-12 w-12 mx-auto mb-3 text-red-400" />
        <p>サービスリクエストが見つかりません</p>
        <button onClick={() => router.back()} className="mt-3 text-blue-600 hover:underline text-sm">
          戻る
        </button>
      </div>
    );
  }

  const transitions = VALID_TRANSITIONS[sr.status] ?? [];
  const isPendingApproval = sr.status === "Pending_Approval";
  const isNew = sr.status === "New";
  const isApproved = sr.status === "Approved";
  const isInProgress = sr.status === "In_Progress" || sr.status === "In_Fulfillment";

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.push("/service-requests")}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-800 text-sm"
        >
          <ArrowLeft className="h-4 w-4" />
          サービスリクエスト一覧に戻る
        </button>
        <div className="flex items-center gap-2">
          {isNew && (
            <button
              onClick={() => submitMutation.mutate()}
              disabled={submitMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              <FileText className="h-4 w-4" />
              {submitMutation.isPending ? "提出中..." : "承認申請"}
            </button>
          )}
          {isApproved && (
            <button
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              {startMutation.isPending ? "開始中..." : "対応開始"}
            </button>
          )}
          {isInProgress && (
            <button
              onClick={() => completeMutation.mutate()}
              disabled={completeMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
            >
              <Flag className="h-4 w-4" />
              {completeMutation.isPending ? "完了処理中..." : "完了"}
            </button>
          )}
          {transitions.length > 0 && (
            <button
              onClick={() => setShowTransition(!showTransition)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200"
            >
              <ChevronDown className="h-4 w-4" />
              ステータス変更
            </button>
          )}
        </div>
      </div>

      {/* Title card */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-xs font-mono text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
                {sr.request_number}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  statusColors[sr.status] ?? "bg-gray-100 text-gray-700"
                }`}
              >
                {statusLabels[sr.status] ?? sr.status}
              </span>
              {sr.request_type && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-200">
                  {sr.request_type}
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-gray-900">{sr.title}</h1>
          </div>
        </div>

        {sr.description && (
          <p className="text-gray-600 text-sm leading-relaxed mt-2">{sr.description}</p>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          {[
            { icon: <User className="h-4 w-4" />, label: "申請者", value: sr.requested_by ?? "—" },
            { icon: <User className="h-4 w-4" />, label: "担当者", value: sr.assigned_to ?? "未割り当て" },
            { icon: <CheckCircle className="h-4 w-4" />, label: "承認者", value: sr.approved_by ?? "未承認" },
            {
              icon: <Clock className="h-4 w-4" />,
              label: "期限",
              value: sr.due_date ? new Date(sr.due_date).toLocaleDateString("ja-JP") : "—",
            },
          ].map(item => (
            <div key={item.label} className="flex items-start gap-2 bg-gray-50 rounded-lg p-3">
              <span className="text-gray-400 mt-0.5">{item.icon}</span>
              <div>
                <p className="text-xs text-gray-400">{item.label}</p>
                <p className="text-sm font-medium text-gray-800 mt-0.5 truncate">{item.value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Approval panel */}
      {isPendingApproval && (
        <div className="bg-white rounded-xl border border-yellow-200 p-6">
          <h3 className="font-semibold text-yellow-700 mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5" />
            承認アクション
          </h3>
          <div className="mb-4">
            <label className="block text-xs text-gray-500 mb-1">承認者名</label>
            <input
              type="text"
              value={actorName}
              onChange={e => setActorName(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
            />
          </div>
          <div className="mb-4">
            <label className="block text-xs text-gray-500 mb-1">コメント</label>
            <textarea
              value={approvalComment}
              onChange={e => setApprovalComment(e.target.value)}
              rows={3}
              placeholder="承認/却下の理由を入力..."
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-yellow-400"
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending}
              className="flex items-center gap-2 px-5 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
            >
              <ThumbsUp className="h-4 w-4" />
              {approveMutation.isPending ? "承認中..." : "承認"}
            </button>
            <button
              onClick={() => rejectMutation.mutate()}
              disabled={rejectMutation.isPending}
              className="flex items-center gap-2 px-5 py-2 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600 disabled:opacity-50"
            >
              <ThumbsDown className="h-4 w-4" />
              {rejectMutation.isPending ? "却下中..." : "却下"}
            </button>
          </div>
        </div>
      )}

      {/* Manual status transition */}
      {showTransition && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-800 mb-4">ステータス変更</h3>
          <div className="flex flex-wrap gap-2 mb-4">
            {transitions.map(s => (
              <button
                key={s}
                onClick={() => setSelectedStatus(s)}
                className={`px-4 py-2 rounded-lg text-sm border transition-colors ${
                  selectedStatus === s
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                }`}
              >
                {statusLabels[s] ?? s}
              </button>
            ))}
          </div>
          <textarea
            value={comment}
            onChange={e => setComment(e.target.value)}
            placeholder="コメント（任意）"
            rows={2}
            className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <div className="flex gap-3 mt-3">
            <button
              disabled={!selectedStatus || transitionMutation.isPending}
              onClick={() => transitionMutation.mutate({ target: selectedStatus, cmt: comment })}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {transitionMutation.isPending ? "変更中..." : "確定"}
            </button>
            <button onClick={() => setShowTransition(false)} className="px-4 py-2 text-gray-600 text-sm">
              キャンセル
            </button>
          </div>
        </div>
      )}

      {/* Completion info */}
      {sr.fulfilled_at && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <h3 className="font-semibold text-green-700 mb-2 flex items-center gap-2">
            <CheckCircle className="h-4 w-4" />
            完了情報
          </h3>
          <p className="text-sm text-green-800">
            完了日時: {new Date(sr.fulfilled_at).toLocaleString("ja-JP")}
          </p>
        </div>
      )}

      {sr.status === "Rejected" && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5">
          <h3 className="font-semibold text-red-700 mb-1 flex items-center gap-2">
            <XCircle className="h-4 w-4" />
            却下済み
          </h3>
          <p className="text-sm text-red-700">承認者: {sr.approved_by ?? "—"}</p>
        </div>
      )}
    </div>
  );
}
