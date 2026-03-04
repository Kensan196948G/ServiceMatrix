/**
 * サービスリクエスト一覧ページ
 * バックエンドAPIからサービスリクエストを取得してテーブル表示
 * Pending_Approval ステータスのリクエストには承認/却下ボタンを表示
 */
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import Table from "@/components/ui/Table";
import Badge, { getPriorityVariant, getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { ServiceRequestResponse } from "@/types/api";

export default function ServiceRequestsPage() {
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["service-requests"],
    queryFn: () =>
      apiClient
        .get<{ items: ServiceRequestResponse[] }>("/service-requests")
        .then((r) => r.data.items ?? []),
  });

  const approveMutation = useMutation({
    mutationFn: (requestId: string) =>
      apiClient.post(`/service-requests/${requestId}/approve`, { actor: "", comment: "" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["service-requests"] }),
    onError: () => setActionError("承認に失敗しました"),
  });

  const rejectMutation = useMutation({
    mutationFn: (requestId: string) =>
      apiClient.post(`/service-requests/${requestId}/reject`, { actor: "", comment: "" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["service-requests"] }),
    onError: () => setActionError("却下に失敗しました"),
  });

  if (isLoading) {
    return (
      <LoadingSpinner
        size="lg"
        message="サービスリクエストを読み込み中..."
      />
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
        サービスリクエストの取得に失敗しました。
      </div>
    );
  }

  const requests = Array.isArray(data) ? data : [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">
          サービスリクエスト
        </h1>
        <span className="text-sm text-gray-500">{requests.length} 件</span>
      </div>

      {actionError && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {actionError}
        </div>
      )}

      <Table<ServiceRequestResponse>
        columns={[
          { header: "番号", accessor: "request_number", className: "w-40" },
          { header: "タイトル", accessor: "title" },
          {
            header: "ステータス",
            accessor: (row) => (
              <Badge variant={getStatusVariant(row.status)}>{row.status}</Badge>
            ),
            className: "w-36",
          },
          {
            header: "承認",
            accessor: (row) =>
              row.approved_by ? (
                <Badge variant="success">承認済み</Badge>
              ) : (
                <Badge variant="neutral">未承認</Badge>
              ),
            className: "w-24",
          },
          {
            header: "アクション",
            accessor: (row) =>
              row.status === "Pending_Approval" ? (
                <div className="flex gap-2">
                  <button
                    onClick={() => approveMutation.mutate(row.request_id)}
                    disabled={approveMutation.isPending}
                    className="rounded bg-green-600 px-2 py-1 text-xs text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    承認
                  </button>
                  <button
                    onClick={() => rejectMutation.mutate(row.request_id)}
                    disabled={rejectMutation.isPending}
                    className="rounded bg-red-600 px-2 py-1 text-xs text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    却下
                  </button>
                </div>
              ) : null,
            className: "w-32",
          },
          {
            header: "作成日時",
            accessor: (row) =>
              new Date(row.created_at).toLocaleDateString("ja-JP"),
            className: "w-32",
          },
        ]}
        data={requests}
        emptyMessage="サービスリクエストはありません"
      />
    </div>
  );
}
