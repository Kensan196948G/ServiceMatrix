/**
 * 問題管理一覧ページ
 * バックエンドAPIから問題レコードを取得してテーブル表示
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import Table from "@/components/ui/Table";
import Badge, { getPriorityVariant, getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { ProblemResponse } from "@/types/api";

export default function ProblemsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["problems"],
    queryFn: () =>
      apiClient.get<ProblemResponse[]>("/problems").then((r) => r.data),
  });

  if (isLoading) {
    return <LoadingSpinner size="lg" message="問題レコードを読み込み中..." />;
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
        問題レコードの取得に失敗しました。
      </div>
    );
  }

  const problems = Array.isArray(data) ? data : [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">問題管理</h1>
        <span className="text-sm text-gray-500">{problems.length} 件</span>
      </div>

      <Table<ProblemResponse>
        columns={[
          { header: "番号", accessor: "problem_number", className: "w-40" },
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
            header: "既知エラー",
            accessor: (row) =>
              row.known_error ? (
                <Badge variant="warning">KEDB</Badge>
              ) : (
                <span className="text-gray-400">-</span>
              ),
            className: "w-28",
          },
          {
            header: "作成日時",
            accessor: (row) =>
              new Date(row.created_at).toLocaleDateString("ja-JP"),
            className: "w-32",
          },
        ]}
        data={problems}
        emptyMessage="問題レコードはありません"
      />
    </div>
  );
}
