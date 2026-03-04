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
  type LucideIcon,
} from "lucide-react";
import apiClient from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Badge, { getPriorityVariant, getStatusVariant } from "@/components/ui/Badge";
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
  // 各リソースの件数を並列取得（limit=100で全件またはページネーション対応）
  const incidents = useQuery({
    queryKey: ["incidents", "dashboard"],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<IncidentResponse> | IncidentResponse[]>("/incidents", {
          params: { limit: 100, skip: 0 },
        })
        .then((r) => r.data),
  });

  const changes = useQuery({
    queryKey: ["changes", "dashboard"],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<ChangeResponse> | ChangeResponse[]>("/changes", {
          params: { limit: 1, skip: 0 },
        })
        .then((r) => r.data),
  });

  const problems = useQuery({
    queryKey: ["problems", "dashboard"],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<ProblemResponse> | ProblemResponse[]>("/problems", {
          params: { limit: 1, skip: 0 },
        })
        .then((r) => r.data),
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
  });

  const isLoading =
    incidents.isLoading ||
    changes.isLoading ||
    problems.isLoading ||
    serviceRequests.isLoading;

  if (isLoading) {
    return <LoadingSpinner size="lg" message="ダッシュボードを読み込み中..." />;
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

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">ダッシュボード</h1>

      {/* KPI統計カード */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
        {stats.map((stat) => (
          <a
            key={stat.title}
            href={stat.href}
            className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">
                  {stat.title}
                </p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {stat.value}{stat.suffix ?? ""}
                </p>
              </div>
              <div className={`rounded-lg p-3 ${stat.bgColor}`}>
                <stat.icon className={`h-6 w-6 ${stat.color}`} />
              </div>
            </div>
          </a>
        ))}
      </div>

      {/* 最近のインシデント */}
      {recentIncidents.length > 0 && (
        <div className="mt-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              最近のインシデント
            </h2>
            <a href="/incidents" className="text-sm text-primary-600 hover:text-primary-700">
              すべて見る →
            </a>
          </div>
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
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {inc.title}
                    </td>
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
        </div>
      )}
    </div>
  );
}
