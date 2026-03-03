/**
 * SLAダッシュボードページ
 * 優先度別SLA達成率・警告一覧・違反一覧・手動チェック機能を提供
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import apiClient from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Badge from "@/components/ui/Badge";
import ProgressGauge from "@/components/ui/ProgressGauge";
import type {
  SLASummaryResponse,
  SLAWarningsResponse,
  SLACheckResponse,
  IncidentResponse,
} from "@/types/api";

/** 優先度の表示順序 */
const PRIORITY_ORDER = ["P1", "P2", "P3", "P4"];

/** 優先度ごとの色設定 */
const PRIORITY_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  P1: { bg: "bg-red-50", border: "border-red-200", text: "text-red-700" },
  P2: { bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-700" },
  P3: { bg: "bg-yellow-50", border: "border-yellow-200", text: "text-yellow-700" },
  P4: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700" },
};

export default function SLADashboardPage() {
  const queryClient = useQueryClient();

  // SLA達成率サマリー
  const summary = useQuery({
    queryKey: ["sla-summary"],
    queryFn: () =>
      apiClient.get<SLASummaryResponse>("/sla/summary").then((r) => r.data),
    refetchInterval: 60_000, // 60秒自動更新
  });

  // SLA警告一覧
  const warnings = useQuery({
    queryKey: ["sla-warnings"],
    queryFn: () =>
      apiClient.get<SLAWarningsResponse>("/sla/warnings").then((r) => r.data),
    refetchInterval: 30_000, // 30秒自動更新
  });

  // SLA違反インシデント一覧
  const breaches = useQuery({
    queryKey: ["sla-breaches"],
    queryFn: () =>
      apiClient.get<IncidentResponse[]>("/sla/breaches").then((r) => r.data),
    refetchInterval: 60_000,
  });

  // 手動SLAチェック
  const manualCheck = useMutation({
    mutationFn: () =>
      apiClient.post<SLACheckResponse>("/sla/check").then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sla-summary"] });
      queryClient.invalidateQueries({ queryKey: ["sla-warnings"] });
      queryClient.invalidateQueries({ queryKey: ["sla-breaches"] });
    },
  });

  const isLoading =
    summary.isLoading || warnings.isLoading || breaches.isLoading;

  if (isLoading) {
    return <LoadingSpinner size="lg" message="SLAダッシュボードを読み込み中..." />;
  }

  // 優先度順にソートしたサマリーエントリ
  const summaryEntries = PRIORITY_ORDER.filter(
    (p) => summary.data && p in summary.data
  ).map((p) => ({
    priority: p,
    ...summary.data![p],
  }));

  // 全体達成率の計算
  const totalIncidents = summaryEntries.reduce((sum, e) => sum + e.total, 0);
  const totalBreached = summaryEntries.reduce((sum, e) => sum + e.breached, 0);
  const overallRate =
    totalIncidents > 0
      ? Math.round(((totalIncidents - totalBreached) / totalIncidents) * 1000) / 10
      : 100;

  const warningList = warnings.data?.warnings ?? [];
  const breachList = Array.isArray(breaches.data) ? breaches.data : [];

  return (
    <div>
      {/* ヘッダー */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">SLAダッシュボード</h1>
        <button
          onClick={() => manualCheck.mutate()}
          disabled={manualCheck.isPending}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${manualCheck.isPending ? "animate-spin" : ""}`}
          />
          SLAチェック実行
        </button>
      </div>

      {/* 手動チェック結果 */}
      {manualCheck.data && (
        <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span className="text-sm font-medium text-green-800">
              SLAチェック完了 - 違反検出: {manualCheck.data.breaches_detected}件 /
              警告検出: {manualCheck.data.warnings_detected}件
            </span>
          </div>
        </div>
      )}

      {/* 全体SLA達成率 + 優先度別ゲージ */}
      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* 全体達成率 */}
        <div className="flex flex-col items-center rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-medium text-gray-500">全体SLA達成率</h3>
          <div className="relative">
            <ProgressGauge value={overallRate} size={140} strokeWidth={12} label="達成率" />
          </div>
          <p className="mt-2 text-xs text-gray-400">
            {totalIncidents}件中 {totalIncidents - totalBreached}件遵守
          </p>
        </div>

        {/* 優先度別カード */}
        {summaryEntries.map((entry) => {
          const colors = PRIORITY_COLORS[entry.priority] ?? PRIORITY_COLORS.P4;
          return (
            <div
              key={entry.priority}
              className={`flex flex-col items-center rounded-xl border ${colors.border} ${colors.bg} p-6 shadow-sm`}
            >
              <h3 className={`mb-4 text-sm font-bold ${colors.text}`}>
                {entry.priority}
              </h3>
              <div className="relative">
                <ProgressGauge
                  value={entry.compliance_rate}
                  size={100}
                  strokeWidth={8}
                  label="達成率"
                />
              </div>
              <div className="mt-2 text-center">
                <p className="text-xs text-gray-500">
                  合計: {entry.total}件
                </p>
                <p className="text-xs text-gray-500">
                  違反: {entry.breached}件
                </p>
              </div>
            </div>
          );
        })}

        {/* データが無い場合 */}
        {summaryEntries.length === 0 && (
          <div className="col-span-4 flex items-center justify-center rounded-xl border border-gray-200 bg-white p-8">
            <p className="text-sm text-gray-400">SLAデータがありません</p>
          </div>
        )}
      </div>

      {/* 警告セクション */}
      <div className="mb-8">
        <div className="mb-4 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <h2 className="text-lg font-semibold text-gray-900">
            SLA警告 ({warningList.length}件)
          </h2>
        </div>

        {warningList.length === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
            <CheckCircle className="mx-auto h-8 w-8 text-green-400" />
            <p className="mt-2 text-sm text-gray-500">
              現在SLA警告はありません
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="divide-y divide-gray-100">
              {warningList.map((w, idx) => (
                <div
                  key={`${w.incident_id}-${w.sla_type}-${idx}`}
                  className="flex items-center justify-between px-6 py-4"
                >
                  <div className="flex items-center gap-3">
                    <Clock
                      className={`h-5 w-5 ${
                        w.warning_level === "warning_90"
                          ? "text-red-500"
                          : "text-amber-500"
                      }`}
                    />
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {w.incident_number}: {w.title}
                      </p>
                      <p className="text-xs text-gray-500">
                        {w.sla_type === "response" ? "応答SLA" : "解決SLA"} |
                        期限: {w.deadline ? new Date(w.deadline).toLocaleString("ja-JP") : "-"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={w.priority === "P1" || w.priority === "P2" ? "danger" : "warning"}
                    >
                      {w.priority}
                    </Badge>
                    <div className="w-24">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">経過</span>
                        <span
                          className={`font-medium ${
                            w.progress_percent >= 90
                              ? "text-red-600"
                              : "text-amber-600"
                          }`}
                        >
                          {w.progress_percent}%
                        </span>
                      </div>
                      <div className="mt-1 h-2 w-full rounded-full bg-gray-200">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            w.progress_percent >= 90
                              ? "bg-red-500"
                              : "bg-amber-500"
                          }`}
                          style={{ width: `${Math.min(w.progress_percent, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* SLA違反インシデント一覧 */}
      <div>
        <div className="mb-4 flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-red-500" />
          <h2 className="text-lg font-semibold text-gray-900">
            SLA違反インシデント ({breachList.length}件)
          </h2>
        </div>

        {breachList.length === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
            <CheckCircle className="mx-auto h-8 w-8 text-green-400" />
            <p className="mt-2 text-sm text-gray-500">
              SLA違反インシデントはありません
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            {/* テーブルヘッダー */}
            <div className="grid grid-cols-12 gap-4 border-b border-gray-200 px-6 py-3 text-xs font-medium uppercase tracking-wider text-gray-500">
              <div className="col-span-2">番号</div>
              <div className="col-span-4">タイトル</div>
              <div className="col-span-1">優先度</div>
              <div className="col-span-2">ステータス</div>
              <div className="col-span-3">応答SLA期限</div>
            </div>

            {/* テーブルボディ */}
            <div className="divide-y divide-gray-100">
              {breachList.map((inc) => (
                <div
                  key={inc.incident_id}
                  className="grid grid-cols-12 gap-4 px-6 py-4 text-sm"
                >
                  <div className="col-span-2 font-medium text-gray-900">
                    {inc.incident_number}
                  </div>
                  <div className="col-span-4 truncate text-gray-700">
                    {inc.title}
                  </div>
                  <div className="col-span-1">
                    <Badge
                      variant={
                        inc.priority === "P1"
                          ? "danger"
                          : inc.priority === "P2"
                            ? "warning"
                            : "info"
                      }
                    >
                      {inc.priority}
                    </Badge>
                  </div>
                  <div className="col-span-2 text-gray-600">{inc.status}</div>
                  <div className="col-span-3 flex items-center gap-1 text-gray-500">
                    <XCircle className="h-4 w-4 text-red-400" />
                    <span className="text-xs">
                      {inc.sla_response_due_at
                        ? new Date(inc.sla_response_due_at).toLocaleString("ja-JP")
                        : "-"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
