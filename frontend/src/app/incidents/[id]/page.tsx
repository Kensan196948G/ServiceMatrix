"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Clock, AlertTriangle, CheckCircle, XCircle,
  RefreshCw, User, Tag, Calendar, MessageSquare, Send, Brain, Loader2, Sparkles
} from "lucide-react";
import apiClient from "@/lib/api";
import type { IncidentResponse } from "@/types/api";

const PRIORITY_COLORS: Record<string, string> = {
  P1: "bg-red-100 text-red-800 border-red-200",
  P2: "bg-orange-100 text-orange-800 border-orange-200",
  P3: "bg-yellow-100 text-yellow-800 border-yellow-200",
  P4: "bg-green-100 text-green-800 border-green-200",
};

const STATUS_COLORS: Record<string, string> = {
  Open: "bg-blue-100 text-blue-800",
  In_Progress: "bg-purple-100 text-purple-800",
  Pending: "bg-yellow-100 text-yellow-800",
  Resolved: "bg-green-100 text-green-800",
  Closed: "bg-gray-100 text-gray-600",
  Cancelled: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<string, string> = {
  Open: "オープン",
  In_Progress: "対応中",
  Pending: "保留中",
  Resolved: "解決済み",
  Closed: "クローズ",
  Cancelled: "キャンセル",
};

// ステータス遷移定義
const TRANSITIONS: Record<string, { label: string; newStatus: string; variant: string }[]> = {
  Open: [{ label: "対応開始", newStatus: "In_Progress", variant: "blue" }],
  In_Progress: [
    { label: "解決済みにする", newStatus: "Resolved", variant: "green" },
    { label: "保留にする", newStatus: "Pending", variant: "yellow" },
  ],
  Pending: [{ label: "対応再開", newStatus: "In_Progress", variant: "blue" }],
  Resolved: [
    { label: "クローズ", newStatus: "Closed", variant: "gray" },
    { label: "再オープン", newStatus: "Open", variant: "orange" },
  ],
};

function SlaTimer({ label, dueAt, breached }: { label: string; dueAt: string | null; breached: boolean }) {
  const [remaining, setRemaining] = useState("");

  useEffect(() => {
    if (!dueAt) return;
    const update = () => {
      const diff = new Date(dueAt).getTime() - Date.now();
      if (diff <= 0) {
        setRemaining("超過");
        return;
      }
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      setRemaining(`${h}時間 ${m}分`);
    };
    update();
    const id = setInterval(update, 60000);
    return () => clearInterval(id);
  }, [dueAt]);

  if (!dueAt) return null;

  const isOverdue = new Date(dueAt).getTime() < Date.now();
  const color = breached || isOverdue ? "text-red-600 bg-red-50 border-red-200" : "text-green-700 bg-green-50 border-green-200";

  return (
    <div className={`rounded-lg border px-4 py-3 ${color}`}>
      <p className="text-xs font-medium opacity-70">{label}</p>
      <p className="text-lg font-bold mt-0.5">{remaining || "計算中..."}</p>
      <p className="text-xs opacity-60 mt-0.5">{new Date(dueAt).toLocaleString("ja-JP")}</p>
    </div>
  );
}

// サンプルタイムライン生成
function buildTimeline(inc: IncidentResponse) {
  const events = [
    { time: inc.created_at, label: "インシデント作成", desc: `優先度 ${inc.priority} で登録`, icon: "create" },
  ];
  if (inc.acknowledged_at) {
    events.push({ time: inc.acknowledged_at, label: "対応開始", desc: "担当者が対応を開始しました", icon: "progress" });
  }
  if (inc.resolved_at) {
    events.push({ time: inc.resolved_at, label: "解決済み", desc: inc.resolution_notes ?? "解決されました", icon: "resolved" });
  }
  if (inc.closed_at) {
    events.push({ time: inc.closed_at, label: "クローズ", desc: "インシデントをクローズしました", icon: "closed" });
  }
  return events.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
}

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const [comments, setComments] = useState<{ text: string; time: string }[]>([]);
  const [aiTriageResult, setAiTriageResult] = useState<{
    priority: string; category: string; confidence: number; reasoning: string;
  } | null>(null);
  const [aiTriageLoading, setAiTriageLoading] = useState(false);

  const { data: incident, isLoading, error } = useQuery<IncidentResponse>({
    queryKey: ["incident", id],
    queryFn: () => apiClient.get(`/incidents/${id}`).then(r => r.data),
    enabled: !!id,
  });

  const transitionMutation = useMutation({
    mutationFn: (newStatus: string) =>
      apiClient.post(`/incidents/${id}/transitions`, { new_status: newStatus }).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incident", id] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
  });

  const handleComment = () => {
    if (!comment.trim()) return;
    setComments(prev => [...prev, { text: comment, time: new Date().toLocaleString("ja-JP") }]);
    setComment("");
  };

  const runAiTriage = async () => {
    if (!id) return;
    setAiTriageLoading(true);
    setAiTriageResult(null);
    try {
      const res = await apiClient.post(`/incidents/${id}/ai-triage`);
      setAiTriageResult({
        priority: res.data.priority,
        category: res.data.category,
        confidence: res.data.confidence,
        reasoning: res.data.reasoning,
      });
      queryClient.invalidateQueries({ queryKey: ["incident", id] });
    } catch {
      setAiTriageResult({ priority: "—", category: "—", confidence: 0, reasoning: "AI分析に失敗しました。" });
    } finally {
      setAiTriageLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="p-6 text-center text-red-600">
        インシデントが見つかりませんでした
        <button onClick={() => router.push("/incidents")} className="block mx-auto mt-3 text-sm text-blue-600 hover:underline">
          一覧へ戻る
        </button>
      </div>
    );
  }

  const transitions = TRANSITIONS[incident.status] ?? [];
  const timeline = buildTimeline(incident);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      {/* ヘッダー */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <button
            onClick={() => router.push("/incidents")}
            className="mt-1 flex-shrink-0 p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-gray-400">{incident.incident_number}</span>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold border ${PRIORITY_COLORS[incident.priority]}`}>
                {incident.priority}
              </span>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[incident.status] ?? "bg-gray-100 text-gray-600"}`}>
                {STATUS_LABELS[incident.status] ?? incident.status}
              </span>
              {incident.sla_breached && (
                <span className="rounded-full bg-red-500 px-2.5 py-0.5 text-xs font-bold text-white">SLA違反</span>
              )}
            </div>
            <h1 className="text-xl font-bold text-gray-900">{incident.title}</h1>
          </div>
        </div>

        {/* 遷移ボタン */}
        <div className="flex-shrink-0 flex gap-2">
          {transitions.map((t) => (
            <button
              key={t.newStatus}
              onClick={() => transitionMutation.mutate(t.newStatus)}
              disabled={transitionMutation.isPending}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50 ${
                t.variant === "blue" ? "bg-blue-600 text-white hover:bg-blue-700" :
                t.variant === "green" ? "bg-green-600 text-white hover:bg-green-700" :
                t.variant === "yellow" ? "bg-yellow-500 text-white hover:bg-yellow-600" :
                t.variant === "orange" ? "bg-orange-500 text-white hover:bg-orange-600" :
                "bg-gray-500 text-white hover:bg-gray-600"
              }`}
            >
              {transitionMutation.isPending ? "処理中..." : t.label}
            </button>
          ))}
        </div>
      </div>

      {/* SLAタイマー */}
      <div className="grid grid-cols-2 gap-4">
        <SlaTimer label="応答期限" dueAt={incident.sla_response_due_at} breached={incident.sla_breached} />
        <SlaTimer label="解決期限" dueAt={incident.sla_resolution_due_at} breached={incident.sla_breached} />
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* 詳細情報 */}
        <div className="col-span-2 space-y-4">
          {/* 説明 */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 mb-3">詳細説明</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">
              {incident.description ?? "説明なし"}
            </p>
            {incident.resolution_notes && (
              <div className="mt-4 rounded-lg bg-green-50 border border-green-200 p-3">
                <p className="text-xs font-semibold text-green-700 mb-1">✅ 解決メモ</p>
                <p className="text-sm text-green-800">{incident.resolution_notes}</p>
              </div>
            )}
          </div>

          {/* AIトリアージ */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <Brain className="w-4 h-4 text-purple-500" />
                AI トリアージ
              </h2>
              <button
                onClick={runAiTriage}
                disabled={aiTriageLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 text-white text-xs rounded-lg hover:bg-purple-700 disabled:opacity-50 transition"
              >
                {aiTriageLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                AI分析実行
              </button>
            </div>
            {(aiTriageResult || incident.ai_triage_notes) ? (
              <div className="space-y-3">
                {aiTriageResult && (
                  <div className="grid grid-cols-3 gap-3 mb-3">
                    <div className="bg-purple-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-purple-500 font-medium">推奨優先度</p>
                      <p className="text-lg font-bold text-purple-800">{aiTriageResult.priority}</p>
                    </div>
                    <div className="bg-blue-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-blue-500 font-medium">カテゴリ</p>
                      <p className="text-sm font-bold text-blue-800">{aiTriageResult.category}</p>
                    </div>
                    <div className="bg-green-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-green-500 font-medium">信頼度</p>
                      <p className="text-lg font-bold text-green-800">{Math.round(aiTriageResult.confidence * 100)}%</p>
                    </div>
                  </div>
                )}
                {aiTriageResult?.reasoning && (
                  <div className="rounded-lg bg-purple-50 border border-purple-200 p-3">
                    <p className="text-xs font-semibold text-purple-700 mb-1">推論</p>
                    <p className="text-sm text-purple-800">{aiTriageResult.reasoning}</p>
                  </div>
                )}
                {incident.ai_triage_notes && !aiTriageResult && (
                  <div className="rounded-lg bg-purple-50 border border-purple-200 p-3">
                    <p className="text-xs font-semibold text-purple-700 mb-1">🤖 AI トリアージノート</p>
                    <p className="text-sm text-purple-800 whitespace-pre-line">{incident.ai_triage_notes}</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-400">AIトリアージ未実行。「AI分析実行」ボタンで自動分析を開始できます。</p>
            )}
          </div>

          {/* タイムライン */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 mb-4">タイムライン</h2>
            <ol className="relative border-l border-gray-200 ml-3 space-y-4">
              {timeline.map((ev, i) => (
                <li key={i} className="ml-6">
                  <span className="absolute -left-3 flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 ring-4 ring-white">
                    {ev.icon === "resolved" ? <CheckCircle className="w-3.5 h-3.5 text-green-600" /> :
                     ev.icon === "closed" ? <XCircle className="w-3.5 h-3.5 text-gray-500" /> :
                     ev.icon === "progress" ? <AlertTriangle className="w-3.5 h-3.5 text-orange-500" /> :
                     <Clock className="w-3.5 h-3.5 text-blue-500" />}
                  </span>
                  <p className="text-sm font-semibold text-gray-900">{ev.label}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{ev.desc}</p>
                  <time className="text-[11px] text-gray-400">
                    {new Date(ev.time).toLocaleString("ja-JP")}
                  </time>
                </li>
              ))}
            </ol>
          </div>

          {/* コメント */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <MessageSquare className="w-4 h-4" /> コメント
            </h2>
            <div className="space-y-3 mb-4">
              {comments.length === 0 ? (
                <p className="text-sm text-gray-400">コメントはまだありません</p>
              ) : (
                comments.map((c, i) => (
                  <div key={i} className="rounded-lg bg-gray-50 px-4 py-3">
                    <p className="text-sm text-gray-800">{c.text}</p>
                    <p className="text-xs text-gray-400 mt-1">{c.time}</p>
                  </div>
                ))
              )}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleComment()}
                placeholder="コメントを入力..."
                className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleComment}
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 transition"
              >
                <Send className="w-3.5 h-3.5" /> 送信
              </button>
            </div>
          </div>
        </div>

        {/* サイドバー情報 */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">インシデント情報</h3>
            <dl className="space-y-2.5 text-sm">
              {[
                { icon: Tag, label: "カテゴリ", value: incident.category ?? "—" },
                { icon: User, label: "報告者", value: incident.reported_by ?? "—" },
                { icon: User, label: "担当者", value: incident.assigned_to ?? "未割当" },
                { icon: Tag, label: "影響サービス", value: incident.affected_service ?? "—" },
                { icon: Calendar, label: "作成日時", value: new Date(incident.created_at).toLocaleString("ja-JP") },
                { icon: Calendar, label: "最終更新", value: new Date(incident.updated_at).toLocaleString("ja-JP") },
              ].map(({ icon: Icon, label, value }) => (
                <div key={label} className="flex items-start gap-2">
                  <Icon className="w-3.5 h-3.5 mt-0.5 text-gray-400 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-gray-400">{label}</p>
                    <p className="text-gray-800 font-medium">{value}</p>
                  </div>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
