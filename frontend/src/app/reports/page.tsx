/**
 * レポート/分析ページ - 月次KPI・MTTR・SLA・解決時間分布
 */
"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart2,
  Clock,
  ShieldCheck,
  AlertTriangle,
  GitPullRequest,
  Download,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import apiClient from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Button from "@/components/ui/Button";

// Recharts は SSR 無効で動的インポート
const BarChart = dynamic(() => import("recharts").then((m) => m.BarChart), { ssr: false });
const Bar = dynamic(() => import("recharts").then((m) => m.Bar), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import("recharts").then((m) => m.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(
  () => import("recharts").then((m) => m.ResponsiveContainer),
  { ssr: false }
);

interface StatsResponse {
  period: { year: number; month: number };
  incidents: {
    total: number;
    resolved: number;
    open: number;
    avg_resolution_hours: number;
  };
  mttr_hours: number;
  mtbf_hours: number;
  sla_compliance_rate: number;
  changes: { total: number; completed: number; failed: number };
  top_affected_services: { service: string; count: number }[];
}

interface DistributionResponse {
  buckets: { range: string; count: number }[];
  period: { year: number; month: number };
}

function KpiCard({
  icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  color: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-gray-500">{label}</span>
        <div className={`rounded-full p-2 ${color}`}>{icon}</div>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function ReportsPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const statsQuery = useQuery<StatsResponse>({
    queryKey: ["reports-stats", year, month],
    queryFn: () =>
      apiClient
        .get("/reports/stats", { params: { year, month } })
        .then((r) => r.data),
    retry: 1,
  });

  const distQuery = useQuery<DistributionResponse>({
    queryKey: ["reports-dist", year, month],
    queryFn: () =>
      apiClient
        .get("/reports/incident-resolution-distribution", { params: { year, month } })
        .then((r) => r.data),
    retry: 1,
  });

  const stats = statsQuery.data;
  const dist = distQuery.data;
  const isLoading = statsQuery.isLoading || distQuery.isLoading;

  const handleDownloadJSON = useCallback(() => {
    if (!stats) return;
    const blob = new Blob([JSON.stringify({ stats, distribution: dist?.buckets }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report_${year}_${String(month).padStart(2, "0")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [stats, dist, year, month]);

  const handleDownloadCSV = useCallback(() => {
    if (!stats) return;
    const rows = [
      ["指標", "値"],
      ["期間", `${year}年${month}月`],
      ["インシデント総数", String(stats.incidents.total)],
      ["解決済み", String(stats.incidents.resolved)],
      ["未解決", String(stats.incidents.open)],
      ["MTTR (時間)", String(stats.mttr_hours)],
      ["MTBF (時間)", String(stats.mtbf_hours)],
      ["SLA達成率", `${(stats.sla_compliance_rate * 100).toFixed(1)}%`],
      ["変更総数", String(stats.changes.total)],
      ["変更完了", String(stats.changes.completed)],
      ["変更失敗", String(stats.changes.failed)],
    ];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report_${year}_${String(month).padStart(2, "0")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [stats, year, month]);

  const yearOptions = Array.from({ length: 3 }, (_, i) => now.getFullYear() - i);
  const monthOptions = Array.from({ length: 12 }, (_, i) => i + 1);

  return (
    <div className="space-y-6">
      {/* ページヘッダー */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart2 className="h-5 w-5 text-blue-500" />
            レポート / 分析
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">月次KPI・MTTR・SLA達成率の分析</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* 期間セレクタ */}
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          >
            {yearOptions.map((y) => (
              <option key={y} value={y}>
                {y}年
              </option>
            ))}
          </select>
          <select
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          >
            {monthOptions.map((m) => (
              <option key={m} value={m}>
                {m}月
              </option>
            ))}
          </select>
          <Button
            variant="ghost"
            size="sm"
            icon={<RefreshCw className="h-3.5 w-3.5" />}
            onClick={() => {
              statsQuery.refetch();
              distQuery.refetch();
            }}
          >
            更新
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon={<Download className="h-3.5 w-3.5" />}
            onClick={handleDownloadCSV}
            disabled={!stats}
          >
            CSV
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon={<Download className="h-3.5 w-3.5" />}
            onClick={handleDownloadJSON}
            disabled={!stats}
          >
            JSON
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <LoadingSpinner size="lg" message="レポートを読み込み中..." />
        </div>
      ) : statsQuery.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center text-sm text-red-600">
          レポートデータの取得に失敗しました
        </div>
      ) : stats ? (
        <>
          {/* KPIカード */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard
              icon={<Clock className="h-4 w-4 text-blue-600" />}
              label="MTTR"
              value={`${stats.mttr_hours}h`}
              sub="平均解決時間"
              color="bg-blue-50"
            />
            <KpiCard
              icon={<TrendingUp className="h-4 w-4 text-purple-600" />}
              label="MTBF"
              value={`${stats.mtbf_hours}h`}
              sub="平均障害間隔（推定）"
              color="bg-purple-50"
            />
            <KpiCard
              icon={<ShieldCheck className="h-4 w-4 text-green-600" />}
              label="SLA達成率"
              value={`${(stats.sla_compliance_rate * 100).toFixed(1)}%`}
              sub={`全${stats.incidents.total}件中`}
              color="bg-green-50"
            />
            <KpiCard
              icon={<AlertTriangle className="h-4 w-4 text-red-500" />}
              label="インシデント総数"
              value={String(stats.incidents.total)}
              sub={`解決済: ${stats.incidents.resolved} / 未解決: ${stats.incidents.open}`}
              color="bg-red-50"
            />
          </div>

          {/* 変更管理KPI */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <GitPullRequest className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-500">変更管理</span>
              </div>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">総数</span>
                  <span className="font-semibold">{stats.changes.total}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">完了</span>
                  <span className="font-semibold text-green-600">{stats.changes.completed}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">失敗</span>
                  <span className="font-semibold text-red-600">{stats.changes.failed}</span>
                </div>
              </div>
            </div>

            {/* 影響サービス上位 */}
            <div className="col-span-1 sm:col-span-2 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
              <p className="text-sm font-medium text-gray-500 mb-3">影響サービス TOP5</p>
              {stats.top_affected_services.length === 0 ? (
                <p className="text-xs text-gray-400">データなし</p>
              ) : (
                <div className="space-y-2">
                  {stats.top_affected_services.map((item, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-xs text-gray-400 w-4">{i + 1}</span>
                      <div className="flex-1">
                        <div className="flex justify-between mb-0.5">
                          <span className="text-xs font-medium text-gray-700 truncate">
                            {item.service}
                          </span>
                          <span className="text-xs text-gray-500 ml-2">{item.count}件</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-gray-100">
                          <div
                            className="h-1.5 rounded-full bg-blue-500"
                            style={{
                              width: `${(item.count / (stats.top_affected_services[0]?.count || 1)) * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 解決時間分布バーチャート */}
          {dist && (
            <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-700 mb-4">
                インシデント解決時間分布
              </h2>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dist.buckets} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="range"
                      tick={{ fontSize: 12, fill: "#6b7280" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 12, fill: "#6b7280" }}
                      axisLine={false}
                      tickLine={false}
                      allowDecimals={false}
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: "8px",
                        border: "1px solid #e5e7eb",
                        fontSize: "12px",
                      }}
                      formatter={(value) => [`${value ?? 0}件`, "インシデント数"] as [string, string]}
                    />
                    <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
