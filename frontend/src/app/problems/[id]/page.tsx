"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  AlertCircle,
  CheckCircle,
  Brain,
  Shield,
  Clock,
  User,
  Tag,
  ChevronDown,
  Save,
  Loader2,
} from "lucide-react";
import apiClient from "@/lib/api";

interface Problem {
  problem_id: string;
  problem_number: string;
  title: string;
  description: string | null;
  priority: string;
  status: string;
  root_cause: string | null;
  known_error: boolean;
  workaround: string | null;
  assigned_to: string | null;
  reported_by: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  category: string | null;
  affected_service: string | null;
  created_at: string;
  updated_at: string;
}

const priorityColors: Record<string, string> = {
  P1: "bg-red-100 text-red-800",
  P2: "bg-orange-100 text-orange-800",
  P3: "bg-yellow-100 text-yellow-800",
  P4: "bg-green-100 text-green-800",
};

const statusColors: Record<string, string> = {
  New: "bg-gray-100 text-gray-800",
  Under_Investigation: "bg-blue-100 text-blue-800",
  Root_Cause_Identified: "bg-indigo-100 text-indigo-800",
  Known_Error: "bg-orange-100 text-orange-800",
  Resolved: "bg-green-100 text-green-800",
  Closed: "bg-gray-200 text-gray-600",
};

const statusTransitions: Record<string, string[]> = {
  New: ["Under_Investigation"],
  Under_Investigation: ["Root_Cause_Identified", "Known_Error", "Resolved"],
  Root_Cause_Identified: ["Known_Error", "Resolved"],
  Known_Error: ["Resolved"],
  Resolved: ["Closed"],
  Closed: [],
};

export default function ProblemDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showTransition, setShowTransition] = useState(false);
  const [transitionNotes, setTransitionNotes] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("");
  const [rootCause, setRootCause] = useState("");
  const [workaround, setWorkaround] = useState("");
  const [showKnownError, setShowKnownError] = useState(false);
  const [rcaLoading, setRcaLoading] = useState(false);
  const [rcaResult, setRcaResult] = useState<string | null>(null);

  const { data: problem, isLoading, isError } = useQuery<Problem>({
    queryKey: ["problem", id],
    queryFn: async () => {
      const res = await apiClient.get(`/problems/${id}`);
      return res.data;
    },
    refetchInterval: 30000,
  });

  const transitionMutation = useMutation({
    mutationFn: async ({ newStatus, notes }: { newStatus: string; notes: string }) => {
      const res = await apiClient.post(`/problems/${id}/transitions`, {
        new_status: newStatus,
        notes,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["problem", id] });
      setShowTransition(false);
      setTransitionNotes("");
      setSelectedStatus("");
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (data: { root_cause?: string }) => {
      const res = await apiClient.patch(`/problems/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["problem", id] });
    },
  });

  const knownErrorMutation = useMutation({
    mutationFn: async (wa: string) => {
      const res = await apiClient.post(`/problems/${id}/known-error`, { workaround: wa });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["problem", id] });
      setShowKnownError(false);
      setWorkaround("");
    },
  });

  const runRCA = async () => {
    setRcaLoading(true);
    setRcaResult(null);
    try {
      const res = await apiClient.post(`/problems/${id}/analyze-rca`);
      setRcaResult(res.data?.analysis ?? "分析が完了しました。");
      queryClient.invalidateQueries({ queryKey: ["problem", id] });
    } catch {
      setRcaResult("RCA分析に失敗しました。");
    } finally {
      setRcaLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (isError || !problem) {
    return (
      <div className="text-center py-16 text-gray-500">
        <AlertCircle className="h-12 w-12 mx-auto mb-3 text-red-400" />
        <p>問題が見つかりません</p>
        <button onClick={() => router.back()} className="mt-3 text-blue-600 hover:underline text-sm">
          戻る
        </button>
      </div>
    );
  }

  const transitions = statusTransitions[problem.status] ?? [];

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.push("/problems")}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-800 text-sm"
        >
          <ArrowLeft className="h-4 w-4" />
          問題一覧に戻る
        </button>
        <div className="flex items-center gap-3">
          {transitions.length > 0 && (
            <button
              onClick={() => setShowTransition(!showTransition)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
            >
              <ChevronDown className="h-4 w-4" />
              ステータス変更
            </button>
          )}
          {!problem.known_error && problem.status !== "Resolved" && problem.status !== "Closed" && (
            <button
              onClick={() => setShowKnownError(true)}
              className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600"
            >
              <Shield className="h-4 w-4" />
              既知エラー登録
            </button>
          )}
        </div>
      </div>

      {/* Title card */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-xs font-mono text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
                {problem.problem_number}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityColors[problem.priority] ?? "bg-gray-100 text-gray-700"}`}>
                {problem.priority}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[problem.status] ?? "bg-gray-100 text-gray-700"}`}>
                {problem.status.replace(/_/g, " ")}
              </span>
              {problem.known_error && (
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-orange-100 text-orange-700">
                  既知エラー
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-gray-900">{problem.title}</h1>
          </div>
        </div>

        {problem.description && (
          <p className="text-gray-600 text-sm leading-relaxed">{problem.description}</p>
        )}

        {/* Metadata grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          {[
            { icon: <Tag className="h-4 w-4" />, label: "カテゴリ", value: problem.category ?? "—" },
            { icon: <AlertCircle className="h-4 w-4" />, label: "影響サービス", value: problem.affected_service ?? "—" },
            { icon: <User className="h-4 w-4" />, label: "担当者", value: problem.assigned_to ?? "未割り当て" },
            { icon: <Clock className="h-4 w-4" />, label: "作成日時", value: new Date(problem.created_at).toLocaleDateString("ja-JP") },
          ].map(item => (
            <div key={item.label} className="flex items-start gap-2 bg-gray-50 rounded-lg p-3">
              <span className="text-gray-400 mt-0.5">{item.icon}</span>
              <div>
                <p className="text-xs text-gray-400">{item.label}</p>
                <p className="text-sm font-medium text-gray-800 mt-0.5 truncate">{item.value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Status transition panel */}
      {showTransition && (
        <div className="bg-white rounded-xl border border-blue-200 p-6">
          <h3 className="font-semibold text-gray-800 mb-4">ステータス変更</h3>
          <div className="flex gap-3 mb-4">
            {transitions.map(s => (
              <button
                key={s}
                onClick={() => setSelectedStatus(s)}
                className={`px-4 py-2 rounded-lg text-sm border transition-colors ${
                  selectedStatus === s
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                }`}
              >
                {s.replace(/_/g, " ")}
              </button>
            ))}
          </div>
          <textarea
            value={transitionNotes}
            onChange={e => setTransitionNotes(e.target.value)}
            placeholder="メモ（任意）"
            rows={3}
            className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <div className="flex gap-3 mt-3">
            <button
              disabled={!selectedStatus || transitionMutation.isPending}
              onClick={() => transitionMutation.mutate({ newStatus: selectedStatus, notes: transitionNotes })}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {transitionMutation.isPending ? "変更中..." : "確定"}
            </button>
            <button onClick={() => setShowTransition(false)} className="px-4 py-2 text-gray-600 text-sm">
              キャンセル
            </button>
          </div>
        </div>
      )}

      {/* Known Error registration */}
      {showKnownError && (
        <div className="bg-white rounded-xl border border-orange-200 p-6">
          <h3 className="font-semibold text-orange-700 mb-3 flex items-center gap-2">
            <Shield className="h-5 w-5" />
            既知エラー登録
          </h3>
          <textarea
            value={workaround}
            onChange={e => setWorkaround(e.target.value)}
            placeholder="回避策（ワークアラウンド）を入力してください..."
            rows={4}
            className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-orange-400"
          />
          <div className="flex gap-3 mt-3">
            <button
              disabled={!workaround.trim() || knownErrorMutation.isPending}
              onClick={() => knownErrorMutation.mutate(workaround)}
              className="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600 disabled:opacity-50"
            >
              {knownErrorMutation.isPending ? "登録中..." : "登録する"}
            </button>
            <button onClick={() => setShowKnownError(false)} className="px-4 py-2 text-gray-600 text-sm">
              キャンセル
            </button>
          </div>
        </div>
      )}

      {/* Workaround display */}
      {problem.workaround && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-5">
          <h3 className="font-semibold text-orange-700 mb-2 flex items-center gap-2">
            <Shield className="h-4 w-4" />
            回避策（ワークアラウンド）
          </h3>
          <p className="text-sm text-orange-800 leading-relaxed">{problem.workaround}</p>
        </div>
      )}

      {/* Root Cause Analysis */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            <Brain className="h-5 w-5 text-indigo-500" />
            根本原因分析（RCA）
          </h3>
          <button
            onClick={runRCA}
            disabled={rcaLoading}
            className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-xs rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {rcaLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Brain className="h-3 w-3" />}
            AI分析実行
          </button>
        </div>

        {problem.root_cause || rcaResult ? (
          <div className="bg-indigo-50 rounded-lg p-4 text-sm text-indigo-900 leading-relaxed">
            {rcaResult ?? problem.root_cause}
          </div>
        ) : (
          <p className="text-sm text-gray-400">根本原因はまだ特定されていません。「AI分析実行」で自動分析を開始できます。</p>
        )}

        {!problem.root_cause && (
          <div className="mt-4">
            <textarea
              value={rootCause}
              onChange={e => setRootCause(e.target.value)}
              placeholder="手動で根本原因を入力..."
              rows={3}
              className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <button
              disabled={!rootCause.trim() || updateMutation.isPending}
              onClick={() => updateMutation.mutate({ root_cause: rootCause })}
              className="mt-2 flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white text-xs rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              <Save className="h-3 w-3" />
              保存
            </button>
          </div>
        )}
      </div>

      {/* Resolved/Closed info */}
      {(problem.resolved_at || problem.closed_at) && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <h3 className="font-semibold text-green-700 mb-2 flex items-center gap-2">
            <CheckCircle className="h-4 w-4" />
            解決情報
          </h3>
          <div className="flex gap-8 text-sm text-green-800">
            {problem.resolved_at && (
              <div>
                <span className="text-green-600 text-xs">解決日時</span>
                <p className="font-medium">{new Date(problem.resolved_at).toLocaleString("ja-JP")}</p>
              </div>
            )}
            {problem.closed_at && (
              <div>
                <span className="text-green-600 text-xs">クローズ日時</span>
                <p className="font-medium">{new Date(problem.closed_at).toLocaleString("ja-JP")}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
