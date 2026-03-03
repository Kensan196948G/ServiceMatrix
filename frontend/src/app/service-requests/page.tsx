/**
 * サービスリクエスト一覧ページ
 * バックエンドAPIからサービスリクエストを取得してテーブル表示
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import Table from "@/components/ui/Table";
import Badge, { getPriorityVariant, getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { ServiceRequestResponse } from "@/types/api";

export default function ServiceRequestsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["service-requests"],
    queryFn: () =>
      apiClient
        .get<ServiceRequestResponse[]>("/service-requests")
        .then((r) => r.data),
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

      <Table<ServiceRequestResponse>
        columns={[
          { header: "番号", accessor: "request_number", className: "w-40" },
          { header: "タイトル", accessor: "title" },
          {
            header: "優先度",
            accessor: (row) => (
              <Badge variant={getPriorityVariant(row.priority)}>
                {row.priority}
              </Badge>
            ),
            className: "w-24",
          },
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
              row.approved_at ? (
                <Badge variant="success">承認済み</Badge>
              ) : (
                <Badge variant="neutral">未承認</Badge>
              ),
            className: "w-24",
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
