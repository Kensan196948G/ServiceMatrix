/**
 * 監査ログページ
 * 監査ログ一覧・フィルター・ハッシュチェーン整合性バッジを提供
 */
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, ShieldCheck, ShieldX, Download } from "lucide-react";
import apiClient from "@/lib/api";
import Table from "@/components/ui/Table";
import Badge from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { AuditLog, AuditVerifyResult, PaginatedResponse } from "@/types/api";

const PAGE_SIZE = 20;

const ACTIONS = ["CREATE", "UPDATE", "DELETE", "READ"] as const;
const ENTITY_TYPES = [
  "incident",
  "change",
  "problem",
  "service_request",
  "ci",
  "user",
] as const;

type TimeRange = "today" | "7d" | "30d" | "all";

function getTimeRangeDates(range: TimeRange): { from?: string; to?: string } {
  if (range === "all") return {};
  const now = new Date();
  const to = now.toISOString();
  let from: Date;
  if (range === "today") {
    from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  } else if (range === "7d") {
    from = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  } else {
    from = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
  }
  return { from: from.toISOString(), to };
}

function getActionVariant(action: string): "success" | "warning" | "danger" | "info" {
  switch (action) {
    case "CREATE": return "success";
    case "UPDATE": return "warning";
    case "DELETE": return "danger";
    case "READ": return "info";
    default: return "info";
  }
}

export default function AuditLogsPage() {
  const [skip, setSkip] = useState(0);
  const [filterAction, setFilterAction] = useState("");
  const [filterEntityType, setFilterEntityType] = useState("");
  const [timeRange, setTimeRange] = useState<TimeRange>("all");

  const timeParams = getTimeRangeDates(timeRange);

  const { data, isLoading, error } = useQuery({
    queryKey: ["audit-logs", skip, filterAction, filterEntityType, timeRange],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<AuditLog> | AuditLog[]>("/audit/logs", {
          params: {
            skip,
            limit: PAGE_SIZE,
            ...(filterAction && { action: filterAction }),
            ...(filterEntityType && { entity_type: filterEntityType }),
            ...(timeParams.from && { from: timeParams.from }),
            ...(timeParams.to && { to: timeParams.to }),
          },
        })
        .then((r) => r.data),
  });

  const { data: verifyData } = useQuery<AuditVerifyResult>({
    queryKey: ["audit-verify"],
    queryFn: () =>
      apiClient.get<AuditVerifyResult>("/audit/verify").then((r) => r.data),
    retry: false,
  });

  if (isLoading) {
    return <LoadingSpinner size="lg" message="監査ログを読み込み中..." />;
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
        監査ログの取得に失敗しました。
      </div>
    );
  }

  const isPaginated = data && !Array.isArray(data) && "items" in data;
  const logs: AuditLog[] = isPaginated
    ? (data as PaginatedResponse<AuditLog>).items
    : Array.isArray(data)
      ? (data as AuditLog[])
      : [];
  const total = isPaginated ? (data as PaginatedResponse<AuditLog>).total : logs.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(skip / PAGE_SIZE) + 1;

  const handleFilterChange = (setter: (v: string) => void) => (val: string) => {
    setter(val);
    setSkip(0);
  };

  const exportCSV = () => {
    if (!logs.length) return;
    const headers = ["操作タイプ", "エンティティ種別", "エンティティID", "操作者", "日時", "ハッシュ"];
    const rows = logs.map(l => [
      l.action,
      l.entity_type,
      l.entity_id,
      l.user_id ?? "",
      new Date(l.created_at).toLocaleString("ja-JP"),
      l.hash,
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportJSON = () => {
    if (!logs.length) return;
    const blob = new Blob([JSON.stringify(logs, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">監査ログ</h1>
        <div className="flex items-center gap-3">
          {/* ハッシュチェーン整合性バッジ */}
          {verifyData && (
            <div
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium ${
                verifyData.valid
                  ? "bg-green-50 text-green-700"
                  : "bg-red-50 text-red-700"
              }`}
            >
              {verifyData.valid ? (
                <ShieldCheck className="h-4 w-4" />
              ) : (
                <ShieldX className="h-4 w-4" />
              )}
              {verifyData.valid
                ? `整合性OK (${verifyData.total_records}件)`
                : `整合性エラー (${verifyData.violations}件違反)`}
            </div>
          )}
          <div className="flex items-center gap-1">
            <button
              onClick={exportCSV}
              disabled={!logs.length}
              className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              title="CSVエクスポート"
            >
              <Download className="h-4 w-4" />
              CSV
            </button>
            <button
              onClick={exportJSON}
              disabled={!logs.length}
              className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              title="JSONエクスポート"
            >
              <Download className="h-4 w-4" />
              JSON
            </button>
          </div>
          <span className="text-sm text-gray-500">{total} 件</span>
        </div>
      </div>

      {/* フィルターバー */}
      <div className="mb-4 flex flex-wrap gap-3">
        <select
          value={filterAction}
          onChange={(e) => handleFilterChange(setFilterAction)(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">全操作タイプ</option>
          {ACTIONS.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <select
          value={filterEntityType}
          onChange={(e) => handleFilterChange(setFilterEntityType)(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">全エンティティ</option>
          {ENTITY_TYPES.map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
        <div className="flex rounded-lg border border-gray-300 overflow-hidden text-sm">
          {(["today", "7d", "30d", "all"] as TimeRange[]).map((r) => (
            <button
              key={r}
              onClick={() => { setTimeRange(r); setSkip(0); }}
              className={`px-3 py-2 transition-colors ${
                timeRange === r
                  ? "bg-primary-600 text-white"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              {r === "today" ? "今日" : r === "7d" ? "7日" : r === "30d" ? "30日" : "全期間"}
            </button>
          ))}
        </div>
      </div>

      <Table<AuditLog>
        columns={[
          {
            header: "操作タイプ",
            accessor: (row) => (
              <Badge variant={getActionVariant(row.action)}>{row.action}</Badge>
            ),
            className: "w-28",
          },
          {
            header: "エンティティ種別",
            accessor: "entity_type",
            className: "w-40",
          },
          {
            header: "エンティティID",
            accessor: (row) => (
              <span className="font-mono text-xs text-gray-600">
                {row.entity_id.slice(0, 8)}…
              </span>
            ),
            className: "w-32",
          },
          {
            header: "変更者",
            accessor: (row) => row.user_id ?? "—",
            className: "w-40",
          },
          {
            header: "タイムスタンプ",
            accessor: (row) =>
              new Date(row.created_at).toLocaleString("ja-JP"),
            className: "w-44",
          },
          {
            header: "ハッシュ",
            accessor: (row) => (
              <span className="font-mono text-xs text-gray-500" title={row.hash}>
                {row.hash.slice(0, 12)}…
              </span>
            ),
            className: "w-36",
          },
        ]}
        data={logs}
        emptyMessage="監査ログはありません"
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
    </div>
  );
}
