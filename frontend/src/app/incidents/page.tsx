/**
 * インシデント一覧ページ
 * バックエンドAPIからインシデントを取得してテーブル表示（ページネーション対応）
 */
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import apiClient from "@/lib/api";
import Table from "@/components/ui/Table";
import Badge, { getPriorityVariant, getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { IncidentResponse, PaginatedResponse } from "@/types/api";

const PAGE_SIZE = 20;

export default function IncidentsPage() {
  const [skip, setSkip] = useState(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["incidents", skip],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<IncidentResponse> | IncidentResponse[]>(
          "/incidents",
          { params: { skip, limit: PAGE_SIZE } }
        )
        .then((r) => r.data),
  });

  if (isLoading) {
    return <LoadingSpinner size="lg" message="インシデントを読み込み中..." />;
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
        インシデントの取得に失敗しました。
      </div>
    );
  }

  // PaginatedResponse と配列レスポンス両方に対応
  const isPaginated = data && !Array.isArray(data) && "items" in data;
  const incidents: IncidentResponse[] = isPaginated
    ? (data as PaginatedResponse<IncidentResponse>).items
    : Array.isArray(data)
      ? (data as IncidentResponse[])
      : [];
  const total = isPaginated
    ? (data as PaginatedResponse<IncidentResponse>).total
    : incidents.length;

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(skip / PAGE_SIZE) + 1;
  const hasPrev = skip > 0;
  const hasNext = skip + PAGE_SIZE < total;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">インシデント管理</h1>
        <span className="text-sm text-gray-500">{total} 件</span>
      </div>

      <Table<IncidentResponse>
        columns={[
          { header: "番号", accessor: "incident_number", className: "w-40" },
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
            header: "SLA",
            accessor: (row) => (
              <Badge variant={row.sla_breached ? "danger" : "success"}>
                {row.sla_breached ? "超過" : "遵守"}
              </Badge>
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
        data={incidents}
        emptyMessage="インシデントはありません"
      />

      {/* ページネーションコントロール */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {skip + 1}〜{Math.min(skip + PAGE_SIZE, total)} 件 / 全 {total} 件
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
              disabled={!hasPrev}
              className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
              前へ
            </button>
            <span className="text-sm text-gray-600">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setSkip(skip + PAGE_SIZE)}
              disabled={!hasNext}
              className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              次へ
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
