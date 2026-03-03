/**
 * ダッシュボードページ
 * インシデント・変更・問題・サービスリクエストの統計を表示
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  GitPullRequest,
  Search,
  ClipboardList,
  type LucideIcon,
} from "lucide-react";
import apiClient from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type {
  IncidentResponse,
  ChangeResponse,
  ProblemResponse,
  ServiceRequestResponse,
} from "@/types/api";

/** 統計カードの型 */
interface StatCard {
  title: string;
  value: number;
  icon: LucideIcon;
  color: string;
  bgColor: string;
  href: string;
}

export default function DashboardPage() {
  // 各リソースの件数を並列取得
  const incidents = useQuery({
    queryKey: ["incidents"],
    queryFn: () =>
      apiClient.get<IncidentResponse[]>("/incidents").then((r) => r.data),
  });

  const changes = useQuery({
    queryKey: ["changes"],
    queryFn: () =>
      apiClient.get<ChangeResponse[]>("/changes").then((r) => r.data),
  });

  const problems = useQuery({
    queryKey: ["problems"],
    queryFn: () =>
      apiClient.get<ProblemResponse[]>("/problems").then((r) => r.data),
  });

  const serviceRequests = useQuery({
    queryKey: ["service-requests"],
    queryFn: () =>
      apiClient
        .get<ServiceRequestResponse[]>("/service-requests")
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

  const stats: StatCard[] = [
    {
      title: "インシデント",
      value: Array.isArray(incidents.data) ? incidents.data.length : 0,
      icon: AlertTriangle,
      color: "text-red-600",
      bgColor: "bg-red-50",
      href: "/incidents",
    },
    {
      title: "変更管理",
      value: Array.isArray(changes.data) ? changes.data.length : 0,
      icon: GitPullRequest,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
      href: "/changes",
    },
    {
      title: "問題管理",
      value: Array.isArray(problems.data) ? problems.data.length : 0,
      icon: Search,
      color: "text-yellow-600",
      bgColor: "bg-yellow-50",
      href: "/problems",
    },
    {
      title: "サービスリクエスト",
      value: Array.isArray(serviceRequests.data)
        ? serviceRequests.data.length
        : 0,
      icon: ClipboardList,
      color: "text-green-600",
      bgColor: "bg-green-50",
      href: "/service-requests",
    },
  ];

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">ダッシュボード</h1>

      {/* 統計カード */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
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
                  {stat.value}
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
      {Array.isArray(incidents.data) && incidents.data.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            最近のインシデント
          </h2>
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="divide-y divide-gray-100">
              {incidents.data.slice(0, 5).map((inc) => (
                <div
                  key={inc.incident_id}
                  className="flex items-center justify-between px-6 py-4"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {inc.incident_number}: {inc.title}
                    </p>
                    <p className="text-xs text-gray-500">
                      優先度: {inc.priority} | ステータス: {inc.status}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      inc.sla_breached
                        ? "bg-red-100 text-red-800"
                        : "bg-green-100 text-green-800"
                    }`}
                  >
                    {inc.sla_breached ? "SLA超過" : "SLA遵守"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
