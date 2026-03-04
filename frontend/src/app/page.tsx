/**
 * ダッシュボードページ - Jira/ServiceNow風 ITSM Dashboard
 */
"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useCallback } from "react";
import Link from "next/link";
import {
  AlertTriangle, GitPullRequest, HelpCircle, ClipboardList,
  ShieldAlert, TrendingUp, Clock, CheckCircle2, XCircle,
  ArrowUpRight, Activity
} from "lucide-react";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from "recharts";
import apiClient from "@/lib/api";
import { useAuthStore } from "@/hooks/useAuth";
import Badge, { getPriorityVariant, getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { IncidentResponse, PaginatedResponse } from "@/types/api";

interface DashboardStats {
  incidents: { total: number; open: number; critical: number; sla_breached: number };
  changes: { total: number; pending: number };
  problems: { total: number; open: number };
  service_requests: { total: number; open: number };
}

const PRIORITY_COLORS = {
  P1: "#ef4444",
  P2: "#f97316",
  P3: "#eab308",
  P4: "#22c55e",
};

const STATUS_COLORS = ["#3b82f6", "#f97316", "#22c55e", "#a855f7", "#6b7280"];

export default function DashboardPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  // WebSocketでリアルタイム更新（正しいエンドポイント: /api/v1/ws/incidents?token=JWT）
  const invalidateIncidents = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["dashboard-incidents"] });
  }, [queryClient]);
  const invalidateChanges = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["dashboard-changes"] });
  }, [queryClient]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const base = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8001/api/v1`;
    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      ws = new WebSocket(`${base}/ws/incidents?token=${token}`);
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === "incident_update" || msg.type === "incident_created") {
            invalidateIncidents();
          } else if (msg.type === "change_update") {
            invalidateChanges();
          }
        } catch { /* ignore parse errors */ }
      };
      ws.onclose = () => {
        retryTimer = setTimeout(connect, 15000);
      };
    };

    connect();
    return () => {
      ws?.close();
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [invalidateIncidents, invalidateChanges]);

  const { data: incidents, isLoading: incLoading } = useQuery({
    queryKey: ["dashboard-incidents"],
    queryFn: () => apiClient.get<PaginatedResponse<IncidentResponse>>("/incidents", {
      params: { page: 1, size: 10 }
    }).then(r => r.data),
    retry: 1,
    staleTime: 15000,
    refetchInterval: 30000,
  });

  const { data: changes } = useQuery({
    queryKey: ["dashboard-changes"],
    queryFn: () => apiClient.get("/changes", { params: { page: 1, size: 100 } }).then(r => r.data),
    retry: 1, staleTime: 15000, refetchInterval: 30000,
  });

  const { data: problems } = useQuery({
    queryKey: ["dashboard-problems"],
    queryFn: () => apiClient.get("/problems", { params: { page: 1, size: 100 } }).then(r => r.data),
    retry: 1, staleTime: 15000, refetchInterval: 30000,
  });

  const { data: serviceRequests } = useQuery({
    queryKey: ["dashboard-sr"],
    queryFn: () => apiClient.get("/service-requests", { params: { page: 1, size: 100 } }).then(r => r.data),
    retry: 1, staleTime: 15000, refetchInterval: 30000,
  });

  const incidentItems: IncidentResponse[] = (incidents as { items?: IncidentResponse[] })?.items ?? (incidents as unknown as IncidentResponse[]) ?? [];
  const changeItems = changes?.items ?? changes ?? [];
  const problemItems = problems?.items ?? problems ?? [];
  const srItems = serviceRequests?.items ?? serviceRequests ?? [];

  // 統計計算
  const stats = {
    incTotal: incidents?.total ?? incidentItems.length,
    incOpen: incidentItems.filter((i: IncidentResponse) => !["Resolved","Closed"].includes(i.status)).length,
    incCritical: incidentItems.filter((i: IncidentResponse) => i.priority === "P1").length,
    incBreached: incidentItems.filter((i: IncidentResponse) => i.sla_breached).length,
    chgTotal: changes?.total ?? changeItems.length,
    chgPending: changeItems.filter((c: { status: string }) => c.status === "Pending").length,
    probTotal: problems?.total ?? problemItems.length,
    probOpen: problemItems.filter((p: { status: string }) => !["Resolved","Closed"].includes(p.status)).length,
    srTotal: serviceRequests?.total ?? srItems.length,
    srOpen: srItems.filter((s: { status: string }) => !["Resolved","Closed","Completed"].includes(s.status)).length,
  };

  // 優先度分布チャート用データ
  const priorityData = ["P1","P2","P3","P4"].map(p => ({
    name: p,
    value: incidentItems.filter((i: IncidentResponse) => i.priority === p).length,
  })).filter(d => d.value > 0);

  // ステータス分布
  const statusCounts: Record<string, number> = {};
  incidentItems.forEach((i: IncidentResponse) => {
    statusCounts[i.status] = (statusCounts[i.status] ?? 0) + 1;
  });
  const statusData = Object.entries(statusCounts).map(([name, value]) => ({ name, value }));

  // 直近7日間のモックトレンドデータ（実際はAPIから取得する）
  const trendData = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    const label = `${d.getMonth()+1}/${d.getDate()}`;
    return {
      date: label,
      incidents: Math.floor(Math.random() * 5) + (i === 6 ? stats.incOpen : 1),
      resolved: Math.floor(Math.random() * 4),
    };
  });

  const kpiCards = [
    {
      label: "インシデント（オープン）",
      value: stats.incOpen,
      total: stats.incTotal,
      icon: AlertTriangle,
      color: "text-red-600",
      bg: "bg-red-50",
      href: "/incidents",
      sub: stats.incBreached > 0 ? `SLA超過 ${stats.incBreached}件` : "SLA正常",
      subColor: stats.incBreached > 0 ? "text-red-500" : "text-green-500",
    },
    {
      label: "変更要求",
      value: stats.chgPending,
      total: stats.chgTotal,
      icon: GitPullRequest,
      color: "text-blue-600",
      bg: "bg-blue-50",
      href: "/changes",
      sub: "承認待ち",
      subColor: "text-blue-500",
    },
    {
      label: "問題管理",
      value: stats.probOpen,
      total: stats.probTotal,
      icon: HelpCircle,
      color: "text-purple-600",
      bg: "bg-purple-50",
      href: "/problems",
      sub: "未解決",
      subColor: "text-purple-500",
    },
    {
      label: "サービスリクエスト",
      value: stats.srOpen,
      total: stats.srTotal,
      icon: ClipboardList,
      color: "text-green-600",
      bg: "bg-green-50",
      href: "/service-requests",
      sub: "対応中",
      subColor: "text-green-500",
    },
  ];

  return (
    <div className="space-y-6">
      {/* ウェルカムバナー */}
      <div className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">
              おはようございます、{user?.full_name ?? user?.username} さん 👋
            </h2>
            <p className="mt-0.5 text-sm text-blue-100">
              ServiceMatrix ITSM Governance Platform · {new Date().toLocaleDateString("ja-JP", { year: "numeric", month: "long", day: "numeric", weekday: "long" })}
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-sm text-blue-100">
            <Activity className="h-4 w-4" />
            <span>システム正常稼働中</span>
          </div>
        </div>
      </div>

      {/* SLA違反アラートバナー */}
      {stats.incBreached > 0 && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <AlertTriangle className="h-5 w-5 shrink-0 text-red-500" />
          <p className="text-sm font-medium text-red-800">
            SLA違反が <strong>{stats.incBreached}件</strong> 発生しています。
            <Link href="/sla" className="ml-2 underline hover:text-red-900">
              SLA監視ダッシュボードで確認 →
            </Link>
          </p>
        </div>
      )}

      {/* KPIカード */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpiCards.map((card) => (
          <Link key={card.href} href={card.href}
            className="group rounded-lg border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300 hover:shadow-md transition-all">
            <div className="flex items-start justify-between">
              <div className={`rounded-lg ${card.bg} p-2.5`}>
                <card.icon className={`h-5 w-5 ${card.color}`} />
              </div>
              <ArrowUpRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
            </div>
            <div className="mt-3">
              <p className="text-2xl font-bold text-gray-900">{card.value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{card.label}</p>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span className={`text-xs font-medium ${card.subColor}`}>{card.sub}</span>
              <span className="text-xs text-gray-400">合計 {card.total}件</span>
            </div>
          </Link>
        ))}
      </div>

      {/* チャートセクション */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* インシデントトレンド */}
        <div className="lg:col-span-2 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-blue-500" />
              インシデント推移（直近7日）
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: "8px", border: "1px solid #e5e7eb" }} />
              <Legend wrapperStyle={{ fontSize: "12px" }} />
              <Line type="monotone" dataKey="incidents" name="発生" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="resolved" name="解決" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 優先度分布 */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-gray-700 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-orange-500" />
            優先度別インシデント
          </h3>
          {priorityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={priorityData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                  {priorityData.map((entry) => (
                    <Cell key={entry.name} fill={PRIORITY_COLORS[entry.name as keyof typeof PRIORITY_COLORS] ?? "#6b7280"} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: "8px" }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[200px] items-center justify-center text-sm text-gray-400">
              <CheckCircle2 className="mr-2 h-5 w-5 text-green-500" />
              インシデントなし
            </div>
          )}
        </div>
      </div>

      {/* ステータス分布 + 最近のインシデント */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* ステータスバー */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Activity className="h-4 w-4 text-purple-500" />
            ステータス分布
          </h3>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={statusData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} width={70} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: "8px", border: "1px solid #e5e7eb" }} />
                <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]}>
                  {statusData.map((_, i) => (
                    <Cell key={i} fill={STATUS_COLORS[i % STATUS_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[180px] items-center justify-center text-sm text-gray-400">データなし</div>
          )}
        </div>

        {/* 最近のインシデント */}
        <div className="lg:col-span-2 rounded-lg border border-gray-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
            <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-500" />
              最近のインシデント
            </h3>
            <Link href="/incidents" className="text-xs text-blue-600 hover:text-blue-700 font-medium">
              すべて表示 →
            </Link>
          </div>
          {incLoading ? (
            <div className="flex h-48 items-center justify-center">
              <LoadingSpinner size="md" message="読み込み中..." />
            </div>
          ) : incidentItems.length === 0 ? (
            <div className="flex h-48 flex-col items-center justify-center gap-2 text-gray-400">
              <CheckCircle2 className="h-8 w-8 text-green-400" />
              <p className="text-sm">インシデントはありません</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-50">
              {incidentItems.slice(0, 6).map((incident: IncidentResponse) => (
                <li key={incident.incident_id} className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50 transition-colors">
                  <div className="flex-shrink-0">
                    {incident.sla_breached
                      ? <XCircle className="h-4 w-4 text-red-500" />
                      : <CheckCircle2 className="h-4 w-4 text-green-400" />
                    }
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-gray-400">{incident.incident_number}</span>
                      <p className="truncate text-sm font-medium text-gray-800">{incident.title}</p>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {new Date(incident.created_at).toLocaleString("ja-JP", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Badge variant={getPriorityVariant(incident.priority)}>{incident.priority}</Badge>
                    <Badge variant={getStatusVariant(incident.status)}>{incident.status}</Badge>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* SLA・変更サマリー */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <ShieldAlert className="h-4 w-4 text-orange-500" />
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">SLA状況</span>
          </div>
          <div className="flex items-end gap-2">
            <span className="text-2xl font-bold text-gray-900">
              {stats.incTotal > 0 ? Math.round((1 - stats.incBreached / Math.max(stats.incTotal, 1)) * 100) : 100}%
            </span>
            <span className="text-xs text-gray-400 mb-1">達成率</span>
          </div>
          <div className="mt-2 h-1.5 rounded-full bg-gray-100">
            <div className="h-1.5 rounded-full bg-green-500" style={{ width: `${stats.incTotal > 0 ? Math.round((1 - stats.incBreached / Math.max(stats.incTotal, 1)) * 100) : 100}%` }} />
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <GitPullRequest className="h-4 w-4 text-blue-500" />
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">変更要求</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.chgTotal}</p>
          <p className="text-xs text-gray-400 mt-1">承認待ち {stats.chgPending}件</p>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <HelpCircle className="h-4 w-4 text-purple-500" />
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">問題管理</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.probTotal}</p>
          <p className="text-xs text-gray-400 mt-1">未解決 {stats.probOpen}件</p>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <ClipboardList className="h-4 w-4 text-green-500" />
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">SR</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.srTotal}</p>
          <p className="text-xs text-gray-400 mt-1">対応中 {stats.srOpen}件</p>
        </div>
      </div>

      {/* SLA達成率チャート（優先度別） */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-gray-700 flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-orange-500" />
          優先度別SLA達成率
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={[
            { priority: "P1", 達成率: 72 },
            { priority: "P2", 達成率: 85 },
            { priority: "P3", 達成率: 91 },
            { priority: "P4", 達成率: 97 },
          ]}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="priority" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} unit="%" />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: "8px", border: "1px solid #e5e7eb" }} formatter={(v: number | string | undefined) => [`${v ?? 0}%`, "SLA達成率"] as [string, string]} />
            <Bar dataKey="達成率" radius={[4, 4, 0, 0]}>
              {[
                { priority: "P1", fill: "#ef4444" },
                { priority: "P2", fill: "#f97316" },
                { priority: "P3", fill: "#eab308" },
                { priority: "P4", fill: "#22c55e" },
              ].map(entry => (
                <Cell key={entry.priority} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
