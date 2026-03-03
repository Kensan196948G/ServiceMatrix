/**
 * 変更管理一覧ページ
 * バックエンドAPIから変更レコードを取得してテーブル表示
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import Table from "@/components/ui/Table";
import Badge, { getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { ChangeResponse } from "@/types/api";

/** リスクレベルに応じたバッジバリアント */
function getRiskVariant(riskScore: number) {
  if (riskScore >= 70) return "danger" as const;
  if (riskScore >= 40) return "warning" as const;
  return "success" as const;
}

export default function ChangesPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["changes"],
    queryFn: () =>
      apiClient.get<ChangeResponse[]>("/changes").then((r) => r.data),
  });

  if (isLoading) {
    return <LoadingSpinner size="lg" message="変更レコードを読み込み中..." />;
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
        変更レコードの取得に失敗しました。
      </div>
    );
  }

  const changes = Array.isArray(data) ? data : [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">変更管理</h1>
        <span className="text-sm text-gray-500">{changes.length} 件</span>
      </div>

      <Table<ChangeResponse>
        columns={[
          { header: "番号", accessor: "change_number", className: "w-40" },
          { header: "タイトル", accessor: "title" },
          {
            header: "種別",
            accessor: (row) => (
              <Badge variant="info">{row.change_type}</Badge>
            ),
            className: "w-28",
          },
          {
            header: "ステータス",
            accessor: (row) => (
              <Badge variant={getStatusVariant(row.status)}>{row.status}</Badge>
            ),
            className: "w-36",
          },
          {
            header: "リスク",
            accessor: (row) => (
              <Badge variant={getRiskVariant(row.risk_score)}>
                {row.risk_score}点
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
        data={changes}
        emptyMessage="変更レコードはありません"
      />
    </div>
  );
}
