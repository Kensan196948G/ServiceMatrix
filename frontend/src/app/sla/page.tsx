/**
 * SLA監視ダッシュボードページ
 * インシデントのSLA違反状況・進捗を可視化する
 */
"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Clock, RefreshCw, BellRing, X } from "lucide-react";
import apiClient from "@/lib/api";
import Badge, { getPriorityVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { IncidentResponse, PaginatedResponse } from "@/types/api";

interface SLAAlert {
  id: string;
  message: string;
  incident_number?: string;
  priority?: string;
  type: "breach" | "warning";
  at: number;
}

// SLA目標時間（分）
const SLA_TARGETS: Record<string, number> = {
  P1: 60,
  P2: 240,
  P3: 480,
  P4: 1440,
};

/** SLA進捗バー */
function SLAProgressBar({
  dueAt,
  createdAt,
  priority,
}: {
  dueAt: string;
  createdAt: string;
  priority: string;
}) {
  const now = Date.now();
  const created = new Date(createdAt).getTime();
  const due = new Date(dueAt).getTime();
  const total = due - created;
  const elapsed = now - created;
  const remainingPct = Math.max(0, Math.min(100, ((due - now) / total) * 100));
  const isBreached = now > due;

  const barColor = isBreached
    ? "bg-red-500"
    : remainingPct < 10
      ? "bg-red-400"
      : remainingPct < 30
        ? "bg-orange-400"
        : "bg-green-500";

  const remainingMs = due - now;
  const remainingHours = Math.floor(Math.abs(remainingMs) / 3600000);
  const remainingMins = Math.floor((Math.abs(remainingMs) % 3600000) / 60000);
  const label = isBreached
    ? `${remainingHours}h ${remainingMins}m 超過`
    : `残り ${remainingHours}h ${remainingMins}m`;

  return (
    <div className="w-full">
      <div className="mb-1 flex justify-between text-xs text-gray-500">
        <span>SLA目標: {SLA_TARGETS[priority] ?? "-"}分</span>
        <span className={isBreached ? "font-medium text-red-600" : ""}>{label}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className={`h-2 rounded-full transition-all ${barColor}`}
          style={{ width: `${isBreached ? 100 : remainingPct}%` }}
        />
      </div>
    </div>
  );
}

/** SLAステータスバッジ */
function SLAStatusBadge({ breached, dueAt }: { breached: boolean; dueAt: string | null }) {
  if (breached) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
        <AlertCircle className="h-3 w-3" />
        SLA違反
      </span>
    );
  }
  if (dueAt) {
    const remaining = new Date(dueAt).getTime() - Date.now();
    const pct = remaining / (new Date(dueAt).getTime() - Date.now() + 1);
    if (remaining < 0) {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
          <AlertCircle className="h-3 w-3" />
          期限超過
        </span>
      );
    }
    // 残り30%未満
    const targetMinutes = 60; // フォールバック
    if (remaining < 30 * 60 * 1000) {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800">
          <Clock className="h-3 w-3" />
          警告
        </span>
      );
    }
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
      正常
    </span>
  );
}

type Priority = "ALL" | "P1" | "P2" | "P3" | "P4";
type SLAFilter = "ALL" | "breached" | "warning" | "ok";

/** SLAアラートトースト */
function SLAAlertToast({
  alerts,
  onDismiss,
}: {
  alerts: SLAAlert[];
  onDismiss: (id: string) => void;
}) {
  if (alerts.length === 0) return null;
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
      {alerts.map((a) => (
        <div
          key={a.id}
          className={`flex items-start gap-3 rounded-lg px-4 py-3 shadow-lg border ${
            a.type === "breach"
              ? "bg-red-50 border-red-300 text-red-800"
              : "bg-orange-50 border-orange-300 text-orange-800"
          }`}
        >
          <BellRing className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="flex-1 text-sm">
            <p className="font-medium">
              {a.type === "breach" ? "⚠️ SLA違反" : "🔔 SLA警告"}
            </p>
            <p>{a.message}</p>
            {a.incident_number && (
              <p className="text-xs opacity-75">{a.incident_number}</p>
            )}
          </div>
          <button onClick={() => onDismiss(a.id)}>
            <X className="h-4 w-4 opacity-60 hover:opacity-100" />
          </button>
        </div>
      ))}
    </div>
  );
}

interface SLAAlertItem {
  incident_id: string;
  title: string;
  sla_remaining_percent: number;
  priority: string;
}

function SLAAlertBanner({ alerts }: { alerts: SLAAlertItem[] }) {
  if (alerts.length === 0) return null;
  return (
    <div className="mb-4 flex items-center gap-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-red-800">
      <AlertCircle className="h-5 w-5 shrink-0 text-red-600" />
      <span className="font-semibold">
        SLAアラート: {alerts.length}件のインシデントが期限切れ間近
      </span>
    </div>
  );
}

export default function SLADashboardPage() {
  const [priorityFilter, setPriorityFilter] = useState<Priority>("ALL");
  const [slaFilter, setSlaFilter] = useState<SLAFilter>("ALL");
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [slaAlerts, setSlaAlerts] = useState<SLAAlert[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();

  // WebSocket: sla_alerts チャンネル購読
  const connectWS = useCallback(() => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.hostname;
    const ws = new WebSocket(
      `${proto}://${host}:8001/api/v1/ws/sla_alerts?token=${token}`
    );
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        const alert: SLAAlert = {
          id: `${Date.now()}-${Math.random()}`,
          message: data.message || data.title || "SLAアラート",
          incident_number: data.incident_number,
          priority: data.priority,
          type: data.event_type === "sla_breach" ? "breach" : "warning",
          at: Date.now(),
        };
        setSlaAlerts((prev) => [alert, ...prev].slice(0, 5));
        queryClient.invalidateQueries({ queryKey: ["sla-incidents"] });
      } catch {}
    };
    ws.onclose = () => {
      setTimeout(connectWS, 5000);
    };
    wsRef.current = ws;
  }, [queryClient]);

  useEffect(() => {
    connectWS();
    return () => wsRef.current?.close();
  }, [connectWS]);

  // 30秒後に自動消去
  useEffect(() => {
    if (slaAlerts.length === 0) return;
    const timer = setTimeout(() => {
      const cutoff = Date.now() - 30_000;
      setSlaAlerts((prev) => prev.filter((a) => a.at > cutoff));
    }, 30_000);
    return () => clearTimeout(timer);
  }, [slaAlerts]);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["sla-incidents"],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<IncidentResponse> | IncidentResponse[]>(
          "/incidents",
          { params: { limit: 200 } }
        )
        .then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: slaAlertItems = [] } = useQuery<SLAAlertItem[]>({
    queryKey: ["sla-alerts"],
    queryFn: () => apiClient.get<SLAAlertItem[]>("/sla/alerts").then((r) => r.data),
    refetchInterval: 60_000,
  });

  useEffect(() => {
    setLastUpdated(new Date());
  }, [data]);

  if (isLoading) {
    return <LoadingSpinner size="lg" message="SLAデータを読み込み中..." />;
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
        SLAデータの取得に失敗しました。
      </div>
    );
  }

  const isPaginated = data && !Array.isArray(data) && "items" in data;
  const allIncidents: IncidentResponse[] = isPaginated
    ? (data as PaginatedResponse<IncidentResponse>).items
    : Array.isArray(data)
      ? (data as IncidentResponse[])
      : [];

  // SLAに関係するもの（解決期限あり or 違反済み）
  const slaIncidents = allIncidents.filter(
    (i) => i.sla_resolution_due_at !== null || i.sla_breached
  );

  // フィルタリング
  const filtered = slaIncidents.filter((i) => {
    if (priorityFilter !== "ALL" && i.priority !== priorityFilter) return false;
    if (slaFilter === "breached" && !i.sla_breached) return false;
    if (slaFilter === "warning") {
      if (i.sla_breached) return false;
      if (!i.sla_resolution_due_at) return false;
      const remaining = new Date(i.sla_resolution_due_at).getTime() - Date.now();
      if (remaining < 0 || remaining >= 30 * 60 * 1000) return false;
    }
    if (slaFilter === "ok") {
      if (i.sla_breached) return false;
      if (i.sla_resolution_due_at) {
        const remaining = new Date(i.sla_resolution_due_at).getTime() - Date.now();
        if (remaining < 30 * 60 * 1000) return false;
      }
    }
    return true;
  });

  // サマリー
  const breachedCount = slaIncidents.filter((i) => i.sla_breached).length;
  const warningCount = slaIncidents.filter((i) => {
    if (i.sla_breached || !i.sla_resolution_due_at) return false;
    const rem = new Date(i.sla_resolution_due_at).getTime() - Date.now();
    return rem >= 0 && rem < 30 * 60 * 1000;
  }).length;

  return (
    <div>
      {/* SLAアラートバナー（/sla/alerts APIから取得） */}
      <SLAAlertBanner alerts={slaAlertItems} />

      {/* SLAリアルタイムアラートトースト */}
      <SLAAlertToast
        alerts={slaAlerts}
        onDismiss={(id) => setSlaAlerts((prev) => prev.filter((a) => a.id !== id))}
      />

      {/* ヘッダー */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SLA監視ダッシュボード</h1>
          <p className="mt-1 text-sm text-gray-500">
            最終更新: {lastUpdated.toLocaleTimeString("ja-JP")} （30秒ごと自動更新）
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <RefreshCw className="h-4 w-4" />
          今すぐ更新
        </button>
      </div>

      {/* サマリーカード */}
      <div className="mb-6 grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-600">SLA違反</p>
          <p className="mt-1 text-3xl font-bold text-red-700">{breachedCount}</p>
        </div>
        <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
          <p className="text-sm text-orange-600">警告（30分未満）</p>
          <p className="mt-1 text-3xl font-bold text-orange-700">{warningCount}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-sm text-gray-600">SLA対象合計</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{slaIncidents.length}</p>
        </div>
      </div>

      {/* フィルター */}
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">優先度:</span>
          {(["ALL", "P1", "P2", "P3", "P4"] as Priority[]).map((p) => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                priorityFilter === p
                  ? "bg-primary-600 text-white"
                  : "border border-gray-300 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">SLA状態:</span>
          {([
            { value: "ALL", label: "すべて" },
            { value: "breached", label: "違反" },
            { value: "warning", label: "警告" },
            { value: "ok", label: "正常" },
          ] as { value: SLAFilter; label: string }[]).map((f) => (
            <button
              key={f.value}
              onClick={() => setSlaFilter(f.value)}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                slaFilter === f.value
                  ? "bg-primary-600 text-white"
                  : "border border-gray-300 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* インシデント一覧 */}
      {filtered.length === 0 ? (
        <div className="rounded-lg bg-gray-50 p-8 text-center text-sm text-gray-500">
          該当するSLA対象インシデントはありません
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((incident) => (
            <div
              key={incident.incident_id}
              className={`rounded-lg border p-4 ${
                incident.sla_breached
                  ? "border-red-200 bg-red-50"
                  : "border-gray-200 bg-white"
              }`}
            >
              <div className="mb-3 flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-gray-500">
                      {incident.incident_number}
                    </span>
                    <Badge variant={getPriorityVariant(incident.priority)}>
                      {incident.priority}
                    </Badge>
                    <SLAStatusBadge
                      breached={incident.sla_breached}
                      dueAt={incident.sla_resolution_due_at}
                    />
                  </div>
                  <p className="mt-1 font-medium text-gray-900">{incident.title}</p>
                  {incident.affected_service && (
                    <p className="text-xs text-gray-500">
                      影響サービス: {incident.affected_service}
                    </p>
                  )}
                </div>
                <div className="text-right text-xs text-gray-400">
                  <div>作成: {new Date(incident.created_at).toLocaleString("ja-JP")}</div>
                  {incident.sla_resolution_due_at && (
                    <div>
                      解決期限:{" "}
                      <span
                        className={
                          incident.sla_breached ? "font-medium text-red-600" : ""
                        }
                      >
                        {new Date(incident.sla_resolution_due_at).toLocaleString("ja-JP")}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* SLA進捗バー */}
              {incident.sla_resolution_due_at && (
                <SLAProgressBar
                  dueAt={incident.sla_resolution_due_at}
                  createdAt={incident.created_at}
                  priority={incident.priority}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
