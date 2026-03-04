/**
 * ダッシュボードページ
 * インシデント・変更・問題・サービスリクエストの統計とSLAコンプライアンスを表示
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  GitPullRequest,
  Search,
  ClipboardList,
  ShieldCheck,
  Plus,
  Activity,
  CheckCircle2,
  type LucideIcon,
} from "lucide-react";
import apiClient from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Badge, { getPriorityVariant, getStatusVariant } from "@/components/ui/Badge";
import { useAuthStore } from "@/hooks/useAuth";
import type {
  IncidentResponse,
  ChangeResponse,
  ProblemResponse,
  ServiceRequestResponse,
  PaginatedResponse,
} from "@/types/api";

/** 統計カードの型 */
interface StatCard {
  title: string;
  value: number | string;
  icon: LucideIcon;
  color: string;
  bgColor: string;
  href: string;
  suffix?: string;
}

/** ページネーションまたは配列レスポンスから件数を取得 */
function extractTotal<T>(data: PaginatedResponse<T> | T[] | undefined): number {
  if (!data) return 0;
  if (Array.isArray(data)) return data.length;
  return data.total ?? data.items?.length ?? 0;
}

/** ページネーションまたは配列レスポンスからアイテムを取得 */
function extractItems<T>(data: PaginatedResponse<T> | T[] | undefined): T[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  return data.items ?? [];
}

export default function DashboardPage() {
  // すべてのフックを最初に呼ぶ（Rules of Hooks）
  const { user } = useAuthStore();

  // 各リソースの件数を並列取得（limit=100で全件またはページネーション対応）
  const incidents = useQuery({
    queryKey: ["incidents", "dashboard"],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<IncidentResponse> | IncidentResponse[]>("/incidents", {
          params: { limit: 100, skip: 0 },
        })
        .then((r) => r.data),
    retry: 1,
    staleTime: 30000,
  });

  const changes = useQuery({
    queryKey: ["changes", "dashboard"],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<ChangeResponse> | ChangeResponse[]>("/changes", {
          params: { limit: 1, skip: 0 },
        })
        .then((r) => r.data),
    retry: 1,
    staleTime: 30000,
  });

  const problems = useQuery({
    queryKey: ["problems", "dashboard"],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<ProblemResponse> | ProblemResponse[]>("/problems", {
          params: { limit: 1, skip: 0 },
        })
        .then((r) => r.data),
    retry: 1,
    staleTime: 30000,
  });

  const serviceRequests = useQuery({
    queryKey: ["service-requests", "dashboard"],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<ServiceRequestResponse> | ServiceRequestResponse[]>(
          "/service-requests",
          { params: { limit: 1, skip: 0 } }
        )
        .then((r) => r.data),
    retry: 1,
    staleTime: 30000,
  });

  const hasError =
    incidents.isError || changes.isError || problems.isError || serviceRequests.isError;
  const isActuallyLoading =
    (incidents.isLoading ||
      changes.isLoading ||
      problems.isLoading ||
      serviceRequests.isLoading) &&
    !hasError;

  if (isActuallyLoading) {
    return <LoadingSpinner size="lg" message="ダッシュボードを読み込み中..." />;
  }

  if (hasError) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="rounded-xl border border-red-200 bg-red-50 p-8 max-w-md">
          <div className="mb-4 flex h-12 w-12 mx-auto items-center justify-center rounded-full bg-red-100">
            <AlertTriangle className="h-6 w-6 text-red-600" />
          </div>
          <h3 className="text-lg font-semibold text-red-900">バックエンドに接続できません</h3>
          <p className="mt-2 text-sm text-red-700">
            APIサーバーへの接続に失敗しました。
          </p>
          <p className="mt-1 text-sm text-red-600">
            <strong>ヒント:</strong> まず{" "}
            <a href="/login" className="underline">
              ログイン
            </a>{" "}
            してからアクセスしてください。
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
          >
            再読み込み
          </button>
        </div>
      </div>
    );
  }

  // SLAコンプライアンス計算（インシデントデータから）
  const incidentItems = extractItems(incidents.data);
  const totalIncidents = incidentItems.length;
  const breachedCount = incidentItems.filter((i) => i.sla_breached).length;
  const slaCompliance =
    totalIncidents > 0
      ? Math.round(((totalIncidents - breachedCount) / totalIncidents) * 100)
      : 100;

  const stats: StatCard[] = [
    {
      title: "オープンインシデント",
      value: extractTotal(incidents.data),
      icon: AlertTriangle,
      color: "text-red-600",
      bgColor: "bg-red-50",
      href: "/incidents",
    },
    {
      title: "変更管理",
      value: extractTotal(changes.data),
      icon: GitPullRequest,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
      href: "/changes",
    },
    {
      title: "問題管理",
      value: extractTotal(problems.data),
      icon: Search,
      color: "text-yellow-600",
      bgColor: "bg-yellow-50",
      href: "/problems",
    },
    {
      title: "サービスリクエスト",
      value: extractTotal(serviceRequests.data),
      icon: ClipboardList,
      color: "text-purple-600",
      bgColor: "bg-purple-50",
      href: "/service-requests",
    },
    {
      title: "SLAコンプライアンス",
      value: slaCompliance,
      suffix: "%",
      icon: ShieldCheck,
      color: slaCompliance >= 95 ? "text-green-600" : slaCompliance >= 80 ? "text-yellow-600" : "text-red-600",
      bgColor: slaCompliance >= 95 ? "bg-green-50" : slaCompliance >= 80 ? "bg-yellow-50" : "bg-red-50",
      href: "/incidents",
    },
  ];

  const recentIncidents = incidentItems.slice(0, 5);
  const totalAll =
    extractTotal(incidents.data) +
    extractTotal(changes.data) +
    extractTotal(problems.data) +
    extractTotal(serviceRequests.data);

  return (
    <div className="space-y-6">
      {/* ウェルカムバナー */}
      <div className="rounded-xl border border-blue-100 bg-gradient-to-r from-blue-600 to-indigo-600 p-6 text-white shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">
              おかえりなさい、{user?.full_name || user?.username || "管理者"}さん
            </h1>
            <p className="mt-1 text-sm text-blue-100">
              ServiceMatrix ITSM Governance Platform へようこそ
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-lg bg-white/20 px-3 py-1.5">
            <Activity className="h-4 w-4" />
            <span className="text-sm font-medium">システム稼働中</span>
          </div>
        </div>
      </div>

      {/* KPI統計カード */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {stats.map((stat) => (
          <a
            key={stat.title}
            href={stat.href}
            className="group rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:border-primary-200 hover:shadow-md"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500">{stat.title}</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {stat.value}{stat.suffix ?? ""}
                </p>
              </div>
              <div className={`rounded-xl p-3 ${stat.bgColor} transition-transform group-hover:scale-110`}>
                <stat.icon className={`h-5 w-5 ${stat.color}`} />
              </div>
            </div>
          </a>
        ))}
      </div>

      {/* 空状態またはコンテンツ */}
      {totalAll === 0 ? (
        /* ウェルカム空状態 */
        <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
          <div className="flex flex-col items-center text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-50">
              <CheckCircle2 className="h-8 w-8 text-primary-600" />
            </div>
            <h2 className="mt-4 text-lg font-semibold text-gray-900">
              システムは正常に動作しています
            </h2>
            <p className="mt-2 max-w-sm text-sm text-gray-500">
              現在、オープンなインシデントや変更はありません。
              新しいアイテムを作成してITSM管理を始めましょう。
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <a
                href="/incidents"
                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
              >
                <Plus className="h-4 w-4" />
                インシデント登録
              </a>
              <a
                href="/changes"
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                変更申請
              </a>
              <a
                href="/service-requests"
                className="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-purple-700"
              >
                <Plus className="h-4 w-4" />
                サービスリクエスト
              </a>
            </div>
          </div>
        </div>
      ) : (
        /* 最近のインシデント */
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              最近のインシデント
            </h2>
            <a href="/incidents" className="text-sm font-medium text-primary-600 hover:text-primary-700">
              すべて見る →
            </a>
          </div>
          {recentIncidents.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white py-12 text-center shadow-sm">
              <AlertTriangle className="mx-auto h-8 w-8 text-gray-300" />
              <p className="mt-2 text-sm text-gray-400">インシデントはありません</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">番号</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">タイトル</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">優先度</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">ステータス</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">SLA</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {recentIncidents.map((inc) => (
                    <tr key={inc.incident_id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                        {inc.incident_number}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">{inc.title}</td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm">
                        <Badge variant={getPriorityVariant(inc.priority)}>{inc.priority}</Badge>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm">
                        <Badge variant={getStatusVariant(inc.status)}>{inc.status}</Badge>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm">
                        <Badge variant={inc.sla_breached ? "danger" : "success"}>
                          {inc.sla_breached ? "超過" : "遵守"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
