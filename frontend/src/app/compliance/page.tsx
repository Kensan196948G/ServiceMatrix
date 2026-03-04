/**
 * コンプライアンスページ - SOC2/ISO27001 チェックリスト・スコアレポート
 */
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, Printer, RefreshCw, CheckCircle2, XCircle, HelpCircle } from "lucide-react";
import apiClient from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

type CheckStatus = "PASS" | "FAIL" | "MANUAL";

interface ComplianceCheck {
  id: string;
  category: string;
  title: string;
  description: string;
  status: CheckStatus;
  evidence: string | null;
}

interface CheckSummary {
  total: number;
  pass: number;
  fail: number;
  manual: number;
  score: number;
}

interface ChecksResponse {
  checks: ComplianceCheck[];
  summary: CheckSummary;
}

type TabKey = "soc2" | "iso27001";

const STATUS_STYLES: Record<CheckStatus, { label: string; className: string; Icon: React.FC<{ className?: string }> }> = {
  PASS: { label: "PASS", className: "bg-green-100 text-green-700", Icon: ({ className }) => <CheckCircle2 className={className} /> },
  FAIL: { label: "FAIL", className: "bg-red-100 text-red-700", Icon: ({ className }) => <XCircle className={className} /> },
  MANUAL: { label: "手動確認", className: "bg-yellow-100 text-yellow-700", Icon: ({ className }) => <HelpCircle className={className} /> },
};

function ScoreMeter({ score, label }: { score: number; label: string }) {
  const color = score >= 80 ? "text-green-600" : score >= 60 ? "text-yellow-500" : "text-red-500";
  return (
    <div className="flex flex-col items-center">
      <div className={`text-5xl font-bold ${color}`}>{score}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}

function ChecksTable({ checks }: { checks: ComplianceCheck[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-semibold text-gray-600 w-40">カテゴリ</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">チェック項目</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600 w-32">ステータス</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">エビデンス</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {checks.map((check) => {
            const s = STATUS_STYLES[check.status];
            return (
              <tr key={check.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">{check.category}</td>
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-800">{check.title}</div>
                  <div className="text-xs text-gray-400 mt-0.5">{check.description}</div>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${s.className}`}>
                    <s.Icon className="h-3.5 w-3.5" />
                    {s.label}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">{check.evidence ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function CompliancePage() {
  const [activeTab, setActiveTab] = useState<TabKey>("soc2");

  const soc2Query = useQuery<ChecksResponse>({
    queryKey: ["compliance-soc2"],
    queryFn: () => apiClient.get("/compliance/checks/soc2").then((r) => r.data),
  });

  const isoQuery = useQuery<ChecksResponse>({
    queryKey: ["compliance-iso27001"],
    queryFn: () => apiClient.get("/compliance/checks/iso27001").then((r) => r.data),
  });

  const activeQuery = activeTab === "soc2" ? soc2Query : isoQuery;
  const isLoading = soc2Query.isLoading || isoQuery.isLoading;

  const soc2Score = soc2Query.data?.summary.score ?? 0;
  const isoScore = isoQuery.data?.summary.score ?? 0;
  const overallScore = soc2Query.data && isoQuery.data
    ? Math.round((soc2Score + isoScore) / 2)
    : 0;

  const handlePrint = () => window.print();

  const handleRefresh = () => {
    soc2Query.refetch();
    isoQuery.refetch();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-7 w-7 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">コンプライアンス</h1>
            <p className="text-sm text-gray-500">SOC2 Type II / ISO27001:2022 準拠チェックリスト</p>
          </div>
        </div>
        <div className="flex gap-2 print:hidden">
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            更新
          </button>
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Printer className="h-4 w-4" />
            レポートをPDF印刷
          </button>
        </div>
      </div>

      {/* スコアカード */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm text-center">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">総合スコア</div>
          {isLoading ? <LoadingSpinner size="sm" /> : <ScoreMeter score={overallScore} label="/ 100点" />}
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm text-center">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">SOC2 スコア</div>
          {soc2Query.isLoading ? <LoadingSpinner size="sm" /> : <ScoreMeter score={soc2Score} label="/ 100点" />}
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm text-center">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">ISO27001 スコア</div>
          {isoQuery.isLoading ? <LoadingSpinner size="sm" /> : <ScoreMeter score={isoScore} label="/ 100点" />}
        </div>
      </div>

      {/* タブ + チェックリスト */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        {/* タブ */}
        <div className="border-b border-gray-200 px-4 print:hidden">
          <div className="flex gap-4">
            {(["soc2", "iso27001"] as TabKey[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`border-b-2 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? "border-blue-600 text-blue-700"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {tab === "soc2" ? "SOC2 Type II" : "ISO27001:2022"}
                {activeTab === tab && (
                  <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                    {activeQuery.data?.summary.pass ?? 0}/{activeQuery.data?.summary.total ?? 0} PASS
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* サマリーバー */}
        {activeQuery.data && (
          <div className="flex gap-6 px-6 py-3 bg-gray-50 border-b border-gray-100 text-sm">
            <span className="text-gray-500">合計: <strong>{activeQuery.data.summary.total}</strong></span>
            <span className="text-green-600">✓ PASS: <strong>{activeQuery.data.summary.pass}</strong></span>
            <span className="text-red-600">✗ FAIL: <strong>{activeQuery.data.summary.fail}</strong></span>
            <span className="text-yellow-600">? 手動確認: <strong>{activeQuery.data.summary.manual}</strong></span>
          </div>
        )}

        {/* テーブル */}
        <div className="p-0">
          {activeQuery.isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" message="チェックリストを読み込み中..." />
            </div>
          ) : activeQuery.isError ? (
            <div className="py-12 text-center text-red-500">データの取得に失敗しました</div>
          ) : activeQuery.data ? (
            <ChecksTable checks={activeQuery.data.checks} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
