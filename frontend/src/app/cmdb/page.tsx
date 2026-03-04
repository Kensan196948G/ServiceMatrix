/**
 * CMDBページ（CI管理）
 * Configuration Item の一覧・検索・フィルター・詳細モーダルを提供
 */
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, X, Search } from "lucide-react";
import apiClient from "@/lib/api";
import Table from "@/components/ui/Table";
import Badge from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { CI, PaginatedResponse } from "@/types/api";

const PAGE_SIZE = 20;

const CI_TYPES = ["Server", "Network", "Application", "Database", "Virtual", "Container"] as const;
const CI_STATUSES = ["Active", "Inactive", "Maintenance", "Retired"] as const;

function getCiTypeVariant(type: string): "info" | "warning" | "success" | "default" {
  switch (type) {
    case "Server": return "info";
    case "Network": return "warning";
    case "Application": return "success";
    case "Database": return "info";
    default: return "default";
  }
}

function getCiStatusVariant(status: string): "success" | "danger" | "warning" | "default" {
  switch (status) {
    case "Active": return "success";
    case "Inactive": return "danger";
    case "Maintenance": return "warning";
    case "Retired": return "default";
    default: return "default";
  }
}

export default function CMDBPage() {
  const [skip, setSkip] = useState(0);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [selectedCI, setSelectedCI] = useState<CI | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["cmdb-cis", skip, search, filterType, filterStatus],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<CI> | CI[]>("/cmdb/cis", {
          params: {
            skip,
            limit: PAGE_SIZE,
            ...(search && { name: search }),
            ...(filterType && { ci_type: filterType }),
            ...(filterStatus && { status: filterStatus }),
          },
        })
        .then((r) => r.data),
  });

  if (isLoading) {
    return <LoadingSpinner size="lg" message="CIを読み込み中..." />;
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
        CI一覧の取得に失敗しました。
      </div>
    );
  }

  const isPaginated = data && !Array.isArray(data) && "items" in data;
  const cis: CI[] = isPaginated
    ? (data as PaginatedResponse<CI>).items
    : Array.isArray(data)
      ? (data as CI[])
      : [];
  const total = isPaginated ? (data as PaginatedResponse<CI>).total : cis.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(skip / PAGE_SIZE) + 1;

  const handleSearch = (val: string) => {
    setSearch(val);
    setSkip(0);
  };

  const handleFilterType = (val: string) => {
    setFilterType(val);
    setSkip(0);
  };

  const handleFilterStatus = (val: string) => {
    setFilterStatus(val);
    setSkip(0);
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">CMDB管理</h1>
        <span className="text-sm text-gray-500">{total} 件</span>
      </div>

      {/* フィルター・検索バー */}
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="CI名で検索..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => handleFilterType(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">全タイプ</option>
          {CI_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => handleFilterStatus(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">全ステータス</option>
          {CI_STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <Table<CI>
        columns={[
          { header: "CI名", accessor: "name" },
          {
            header: "タイプ",
            accessor: (row) => (
              <Badge variant={getCiTypeVariant(row.ci_type)}>{row.ci_type}</Badge>
            ),
            className: "w-36",
          },
          {
            header: "ステータス",
            accessor: (row) => (
              <Badge variant={getCiStatusVariant(row.status)}>{row.status}</Badge>
            ),
            className: "w-32",
          },
          {
            header: "担当チーム",
            accessor: (row) => row.team_id ?? "—",
            className: "w-40",
          },
          {
            header: "最終更新",
            accessor: (row) =>
              new Date(row.updated_at).toLocaleDateString("ja-JP"),
            className: "w-32",
          },
        ]}
        data={cis}
        onRowClick={(row) => setSelectedCI(row)}
        emptyMessage="CIはありません"
      />

      {/* ページネーション */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {skip + 1}〜{Math.min(skip + PAGE_SIZE, total)} 件 / 全 {total} 件
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
              disabled={skip === 0}
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
              disabled={skip + PAGE_SIZE >= total}
              className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              次へ
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* CI詳細モーダル */}
      {selectedCI && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setSelectedCI(null)}
        >
          <div
            className="relative w-full max-w-lg rounded-xl bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setSelectedCI(null)}
              className="absolute right-4 top-4 rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
            <h2 className="mb-4 text-lg font-bold text-gray-900">
              {selectedCI.name}
            </h2>
            <dl className="space-y-3 text-sm">
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">CI ID</dt>
                <dd className="font-mono text-gray-800">{selectedCI.ci_id}</dd>
              </div>
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">タイプ</dt>
                <dd>
                  <Badge variant={getCiTypeVariant(selectedCI.ci_type)}>
                    {selectedCI.ci_type}
                  </Badge>
                </dd>
              </div>
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">ステータス</dt>
                <dd>
                  <Badge variant={getCiStatusVariant(selectedCI.status)}>
                    {selectedCI.status}
                  </Badge>
                </dd>
              </div>
              {selectedCI.description && (
                <div className="flex gap-4">
                  <dt className="w-32 text-gray-500">説明</dt>
                  <dd className="text-gray-800">{selectedCI.description}</dd>
                </div>
              )}
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">担当チーム</dt>
                <dd className="text-gray-800">{selectedCI.team_id ?? "—"}</dd>
              </div>
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">関連インシデント数</dt>
                <dd className="font-semibold text-gray-800">
                  {selectedCI.incident_count ?? 0}
                </dd>
              </div>
              {selectedCI.depends_on && selectedCI.depends_on.length > 0 && (
                <div className="flex gap-4">
                  <dt className="w-32 text-gray-500">依存関係</dt>
                  <dd className="flex flex-wrap gap-1">
                    {selectedCI.depends_on.map((dep) => (
                      <span
                        key={dep}
                        className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-600"
                      >
                        {dep}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">作成日時</dt>
                <dd className="text-gray-800">
                  {new Date(selectedCI.created_at).toLocaleString("ja-JP")}
                </dd>
              </div>
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">最終更新</dt>
                <dd className="text-gray-800">
                  {new Date(selectedCI.updated_at).toLocaleString("ja-JP")}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      )}
    </div>
  );
}
