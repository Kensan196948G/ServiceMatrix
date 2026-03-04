/**
 * AI分析ページ
 * インシデントトリアージ・類似インシデント検索・AI決定ログを提供
 */
"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Search, Zap, Brain } from "lucide-react";
import apiClient from "@/lib/api";
import Badge, { getPriorityVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { IncidentResponse } from "@/types/api";

interface TriageResult {
  incident_id: string;
  priority: string;
  triage_notes: string;
  similar_incidents?: Array<{ incident_id: string; score: number; title: string }>;
}

interface SimilarIncident {
  incident_id: string;
  incident_number: string;
  title: string;
  priority: string;
  status: string;
  score?: number;
}

export default function AIPage() {
  const [triageId, setTriageId] = useState("");
  const [searchText, setSearchText] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // トリアージ実行
  const triageMutation = useMutation({
    mutationFn: (incidentId: string) =>
      apiClient
        .post<TriageResult>(`/ai/triage/${incidentId}`)
        .then((r) => r.data),
  });

  // 類似インシデント検索
  const { data: similarData, isLoading: similarLoading, refetch: searchRefetch } =
    useQuery({
      queryKey: ["similar-incidents", searchQuery],
      queryFn: () =>
        apiClient
          .get<SimilarIncident[]>("/ai/similar", {
            params: { q: searchQuery, limit: 10 },
          })
          .then((r) => r.data),
      enabled: searchQuery.length > 0,
    });

  // AI決定ログ（インシデント一覧からai_triage_notesを持つものを取得）
  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ["ai-decision-logs"],
    queryFn: () =>
      apiClient
        .get<IncidentResponse[] | { items: IncidentResponse[] }>("/incidents", {
          params: { limit: 50 },
        })
        .then((r) => {
          const raw = r.data;
          const items = Array.isArray(raw) ? raw : (raw as { items: IncidentResponse[] }).items ?? [];
          return items.filter((i) => i.ai_triage_notes);
        }),
    refetchInterval: 60_000,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchText);
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">AI分析</h1>
        <p className="mt-1 text-sm text-gray-500">
          AIによるインシデントトリアージ・類似インシデント検索・判断ログ確認
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* トリアージパネル */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <div className="mb-4 flex items-center gap-2">
            <Zap className="h-5 w-5 text-purple-500" />
            <h2 className="text-lg font-semibold text-gray-900">AIトリアージ</h2>
          </div>
          <p className="mb-4 text-sm text-gray-500">
            インシデントIDを入力してAIトリアージを実行します
          </p>

          <div className="flex gap-2">
            <input
              type="text"
              value={triageId}
              onChange={(e) => setTriageId(e.target.value)}
              placeholder="インシデントID (例: INC-00001)"
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            <button
              onClick={() => triageId && triageMutation.mutate(triageId)}
              disabled={!triageId || triageMutation.isPending}
              className="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
            >
              {triageMutation.isPending ? (
                <LoadingSpinner size="sm" />
              ) : (
                <Zap className="h-4 w-4" />
              )}
              実行
            </button>
          </div>

          {/* トリアージ結果 */}
          {triageMutation.isError && (
            <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              トリアージに失敗しました。インシデントIDを確認してください。
            </div>
          )}
          {triageMutation.isSuccess && triageMutation.data && (
            <div className="mt-4 rounded-lg bg-purple-50 p-4">
              <div className="mb-2 flex items-center gap-2">
                <span className="text-sm font-medium text-purple-800">トリアージ結果</span>
                <Badge variant={getPriorityVariant(triageMutation.data.priority)}>
                  {triageMutation.data.priority}
                </Badge>
              </div>
              <p className="text-sm text-gray-700">{triageMutation.data.triage_notes}</p>
              {triageMutation.data.similar_incidents &&
                triageMutation.data.similar_incidents.length > 0 && (
                  <div className="mt-3">
                    <p className="mb-1 text-xs font-medium text-gray-500">類似インシデント:</p>
                    <ul className="space-y-1">
                      {triageMutation.data.similar_incidents.map((s) => (
                        <li key={s.incident_id} className="text-xs text-gray-600">
                          • {s.title} (スコア: {(s.score * 100).toFixed(0)}%)
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          )}
        </div>

        {/* 類似インシデント検索パネル */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <div className="mb-4 flex items-center gap-2">
            <Search className="h-5 w-5 text-blue-500" />
            <h2 className="text-lg font-semibold text-gray-900">類似インシデント検索</h2>
          </div>
          <p className="mb-4 text-sm text-gray-500">
            テキストで類似インシデントを検索します
          </p>

          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="例: データベース接続エラー"
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            <button
              type="submit"
              disabled={!searchText || similarLoading}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Search className="h-4 w-4" />
              検索
            </button>
          </form>

          {/* 検索結果 */}
          {similarLoading && searchQuery && (
            <div className="mt-4">
              <LoadingSpinner size="sm" message="検索中..." />
            </div>
          )}
          {similarData && similarData.length === 0 && (
            <div className="mt-4 text-center text-sm text-gray-500">
              類似インシデントが見つかりませんでした
            </div>
          )}
          {similarData && similarData.length > 0 && (
            <ul className="mt-4 space-y-2">
              {similarData.map((s) => (
                <li
                  key={s.incident_id}
                  className="rounded-lg border border-gray-100 bg-gray-50 p-3"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-gray-400">
                      {s.incident_number}
                    </span>
                    <Badge variant={getPriorityVariant(s.priority)}>{s.priority}</Badge>
                    {s.score !== undefined && (
                      <span className="ml-auto text-xs text-gray-400">
                        {(s.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-gray-700">{s.title}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* AI決定ログ */}
      <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
        <div className="mb-4 flex items-center gap-2">
          <Brain className="h-5 w-5 text-green-500" />
          <h2 className="text-lg font-semibold text-gray-900">AI判断ログ（最近の履歴）</h2>
        </div>

        {logsLoading && <LoadingSpinner size="sm" message="ログを読み込み中..." />}
        {!logsLoading && logsData && logsData.length === 0 && (
          <p className="text-sm text-gray-500">AI判断ログがまだありません</p>
        )}
        {logsData && logsData.length > 0 && (
          <div className="space-y-3">
            {logsData.slice(0, 10).map((incident) => (
              <div
                key={incident.incident_id}
                className="rounded-lg border border-gray-100 bg-gray-50 p-4"
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="font-mono text-xs text-gray-400">
                    {incident.incident_number}
                  </span>
                  <Badge variant={getPriorityVariant(incident.priority)}>
                    {incident.priority}
                  </Badge>
                  <span className="ml-auto text-xs text-gray-400">
                    {new Date(incident.updated_at).toLocaleString("ja-JP")}
                  </span>
                </div>
                <p className="mb-1 text-sm font-medium text-gray-700">{incident.title}</p>
                <p className="text-xs text-gray-500">{incident.ai_triage_notes}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
