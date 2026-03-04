/**
 * 変更詳細ページ - CAB承認・キャンセル・リスクバー・ステータスタイムライン
 */
"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  GitPullRequest,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Shield,
  User,
  Calendar,
} from "lucide-react";
import apiClient from "@/lib/api";
import Badge, { getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Button from "@/components/ui/Button";
import type { ChangeResponse } from "@/types/api";

// ステータス順序（タイムライン用）
const STATUS_TIMELINE: Record<string, string[]> = {
  Standard: ["Draft", "Submitted", "Approved", "Scheduled", "In_Progress", "Implemented", "Closed"],
  Normal: ["Draft", "Submitted", "Pending_Approval", "Approved", "Scheduled", "In_Progress", "Implemented", "Closed"],
  Emergency: ["Draft", "Submitted", "Approved", "In_Progress", "Implemented", "Closed"],
  Major: ["Draft", "Submitted", "Pending_Approval", "Approved", "Scheduled", "In_Progress", "Implemented", "Closed"],
};

const STATUS_LABELS: Record<string, string> = {
  Draft: "下書き",
  Submitted: "申請済",
  Pending_Approval: "承認待ち",
  Approved: "承認済",
  Scheduled: "スケジュール済",
  In_Progress: "実施中",
  Implemented: "実装完了",
  Failed: "失敗",
  Cancelled: "キャンセル",
  Closed: "クローズ",
};

const TERMINAL_STATUSES = ["Implemented", "Closed", "Cancelled", "Failed"];
const CANCEL_HIDDEN_STATUSES = ["Implemented", "Closed", "Cancelled"];

function getRiskColor(score: number) {
  if (score > 60) return { bar: "bg-red-500", text: "text-red-600", bg: "bg-red-100", label: "高リスク" };
  if (score > 30) return { bar: "bg-yellow-400", text: "text-yellow-600", bg: "bg-yellow-100", label: "中リスク" };
  return { bar: "bg-green-500", text: "text-green-600", bg: "bg-green-100", label: "低リスク" };
}

function RiskBar({ score }: { score: number }) {
  const { bar, text, bg, label } = getRiskColor(score);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${text} ${bg}`}>{label} {score}点</span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
        <div className={`h-full rounded-full transition-all ${bar}`} style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
      <div className="flex justify-between text-[10px] text-gray-400">
        <span>0</span><span>30</span><span>60</span><span>100</span>
      </div>
    </div>
  );
}

function StatusTimeline({ changeType, currentStatus }: { changeType: string; currentStatus: string }) {
  const steps = STATUS_TIMELINE[changeType] ?? STATUS_TIMELINE.Normal;
  const isFailed = currentStatus === "Failed";
  const isCancelled = currentStatus === "Cancelled";

  let currentIdx = steps.indexOf(currentStatus);
  if (isFailed || isCancelled) currentIdx = steps.length; // past the end

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {steps.map((step, i) => {
        const done = i < currentIdx;
        const active = steps[i] === currentStatus;
        return (
          <div key={step} className="flex items-center gap-1">
            <div className={`flex flex-col items-center`}>
              <div className={`h-6 w-6 rounded-full flex items-center justify-center text-[10px] font-bold border-2
                ${active ? "border-blue-500 bg-blue-500 text-white" : done ? "border-green-500 bg-green-500 text-white" : "border-gray-200 bg-white text-gray-400"}`}>
                {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : <span>{i + 1}</span>}
              </div>
              <span className={`text-[10px] mt-0.5 whitespace-nowrap ${active ? "text-blue-600 font-semibold" : done ? "text-green-600" : "text-gray-400"}`}>
                {STATUS_LABELS[step] ?? step}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={`h-0.5 w-6 mb-3 ${i < currentIdx ? "bg-green-400" : "bg-gray-200"}`} />
            )}
          </div>
        );
      })}
      {(isFailed || isCancelled) && (
        <div className="flex items-center gap-1 ml-1">
          <div className="h-0.5 w-6 mb-3 bg-red-300" />
          <div className="flex flex-col items-center">
            <div className="h-6 w-6 rounded-full flex items-center justify-center border-2 border-red-500 bg-red-500 text-white">
              <XCircle className="h-3.5 w-3.5" />
            </div>
            <span className="text-[10px] mt-0.5 text-red-600 font-semibold">{STATUS_LABELS[currentStatus]}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ChangeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const changeId = params.id as string;
  const [approveError, setApproveError] = useState("");
  const [cancelError, setCancelError] = useState("");

  const { data: change, isLoading, error } = useQuery({
    queryKey: ["change", changeId],
    queryFn: () => apiClient.get<ChangeResponse>(`/changes/${changeId}`).then((r) => r.data),
    enabled: !!changeId,
  });

  const approveMutation = useMutation({
    mutationFn: () =>
      apiClient.post(`/changes/${changeId}/approve`, { comment: "承認" }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["change", changeId] });
      queryClient.invalidateQueries({ queryKey: ["changes"] });
      setApproveError("");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "承認に失敗しました";
      setApproveError(typeof msg === "string" ? msg : JSON.stringify(msg));
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () =>
      apiClient.post(`/changes/${changeId}/cancel`, {}).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["change", changeId] });
      queryClient.invalidateQueries({ queryKey: ["changes"] });
      setCancelError("");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "キャンセルに失敗しました";
      setCancelError(typeof msg === "string" ? msg : JSON.stringify(msg));
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !change) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 text-gray-500">
        <XCircle className="h-10 w-10 text-red-400" />
        <p className="text-sm">変更要求が見つかりません</p>
        <Button variant="secondary" size="sm" onClick={() => router.push("/changes")}>
          一覧に戻る
        </Button>
      </div>
    );
  }

  const showApprove =
    change.status === "Pending_Approval" || change.status === "Submitted";
  const showCancel = !CANCEL_HIDDEN_STATUSES.includes(change.status);
  const riskColors = getRiskColor(change.risk_score);

  return (
    <div className="space-y-5 max-w-4xl">
      {/* ヘッダー */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <button
            onClick={() => router.push("/changes")}
            className="mt-0.5 flex items-center gap-1 text-sm text-gray-500 hover:text-blue-600 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            変更管理
          </button>
        </div>
        <div className="flex items-center gap-2">
          {showApprove && (
            <Button
              variant="primary"
              size="sm"
              loading={approveMutation.isPending}
              icon={<CheckCircle2 className="h-4 w-4" />}
              onClick={() => approveMutation.mutate()}
            >
              CAB承認
            </Button>
          )}
          {showCancel && (
            <Button
              variant="danger"
              size="sm"
              loading={cancelMutation.isPending}
              icon={<XCircle className="h-4 w-4" />}
              onClick={() => cancelMutation.mutate()}
            >
              キャンセル
            </Button>
          )}
        </div>
      </div>

      {(approveError || cancelError) && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {approveError || cancelError}
        </div>
      )}

      {/* タイトルカード */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-5 space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <GitPullRequest className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-500" />
            <div>
              <p className="text-xs font-mono text-gray-400 mb-0.5">{change.change_number}</p>
              <h2 className="text-lg font-semibold text-gray-900">{change.title}</h2>
            </div>
          </div>
          <Badge variant={getStatusVariant(change.status)}>
            {change.status.replace(/_/g, " ")}
          </Badge>
        </div>
        {change.description && (
          <p className="text-sm text-gray-600 pl-8 leading-relaxed">{change.description}</p>
        )}
      </div>

      {/* 詳細情報グリッド */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* 変更タイプ・リスク */}
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4 space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">変更情報</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 flex items-center gap-1.5">
                <Shield className="h-3.5 w-3.5" /> 変更タイプ
              </span>
              <Badge variant="info">{change.change_type}</Badge>
            </div>
            <div className="space-y-1">
              <span className="text-sm text-gray-500 flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5" /> リスクスコア
              </span>
              <RiskBar score={change.risk_score} />
            </div>
            {change.impact_level && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">影響レベル</span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${riskColors.text} ${riskColors.bg}`}>
                  {change.impact_level}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* 担当者・スケジュール */}
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4 space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">担当・スケジュール</h3>
          <div className="space-y-3">
            {change.requested_by && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5" /> 申請者
                </span>
                <span className="text-sm font-medium text-gray-800">{change.requested_by}</span>
              </div>
            )}
            {change.cab_approved_by && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> CAB承認者
                </span>
                <span className="text-sm font-medium text-gray-800">{change.cab_approved_by}</span>
              </div>
            )}
            {change.scheduled_start_at && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" /> 開始予定
                </span>
                <span className="text-sm text-gray-700">
                  {new Date(change.scheduled_start_at).toLocaleString("ja-JP", {
                    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                  })}
                </span>
              </div>
            )}
            {change.scheduled_end_at && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" /> 終了予定
                </span>
                <span className="text-sm text-gray-700">
                  {new Date(change.scheduled_end_at).toLocaleString("ja-JP", {
                    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                  })}
                </span>
              </div>
            )}
            <div className="flex items-center justify-between border-t border-gray-50 pt-2">
              <span className="text-xs text-gray-400">作成日時</span>
              <span className="text-xs text-gray-400">
                {new Date(change.created_at).toLocaleString("ja-JP", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ステータスタイムライン */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4 space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 flex items-center gap-1.5">
          <Clock className="h-3.5 w-3.5" /> ステータスタイムライン
        </h3>
        <div className="overflow-x-auto pb-1">
          <StatusTimeline changeType={change.change_type} currentStatus={change.status} />
        </div>
      </div>

      {/* 計画メモ */}
      {(change.implementation_plan || change.rollback_plan || change.test_plan || change.cab_notes) && (
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-4 space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">計画・備考</h3>
          {change.implementation_plan && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">実装計画</p>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{change.implementation_plan}</p>
            </div>
          )}
          {change.rollback_plan && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">ロールバック計画</p>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{change.rollback_plan}</p>
            </div>
          )}
          {change.test_plan && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">テスト計画</p>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{change.test_plan}</p>
            </div>
          )}
          {change.cab_notes && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">CABノート</p>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{change.cab_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
