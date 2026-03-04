/**
 * 変更詳細ページ - CAB承認・ワークフローアクション・リスクバー・ステータスタイムライン
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
  Play,
  Square,
  Archive,
  Send,
} from "lucide-react";
import apiClient from "@/lib/api";
import Badge, { getStatusVariant } from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Button from "@/components/ui/Button";
import type { ChangeResponse } from "@/types/api";

// 実際のバックエンドステータスに基づくタイムライン
const STATUS_STEPS = [
  "Draft",
  "Submitted",
  "CAB_Review",
  "Approved",
  "Scheduled",
  "In_Progress",
  "Completed",
  "Closed",
];

const STATUS_LABELS: Record<string, string> = {
  Draft: "下書き",
  Submitted: "申請済",
  CAB_Review: "CABレビュー中",
  Approved: "承認済",
  Rejected: "却下",
  Scheduled: "スケジュール済",
  In_Progress: "実施中",
  Completed: "実装完了",
  Closed: "クローズ",
  Cancelled: "キャンセル",
  Failed: "失敗",
};

const TERMINAL_STATUSES = ["Closed", "Cancelled", "Failed", "Rejected"];

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
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${text} ${bg}`}>
          {label} {score}点
        </span>
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

function StatusTimeline({ currentStatus }: { currentStatus: string }) {
  const isTerminal = TERMINAL_STATUSES.includes(currentStatus);
  const currentIdx = STATUS_STEPS.indexOf(currentStatus);

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {STATUS_STEPS.map((step, i) => {
        const done = i < currentIdx;
        const active = step === currentStatus;
        return (
          <div key={step} className="flex items-center gap-1">
            <div className="flex flex-col items-center">
              <div className={`h-6 w-6 rounded-full flex items-center justify-center text-[10px] font-bold border-2
                ${active ? "border-blue-500 bg-blue-500 text-white"
                  : done ? "border-green-500 bg-green-500 text-white"
                  : "border-gray-200 bg-white text-gray-400"}`}>
                {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : <span>{i + 1}</span>}
              </div>
              <span className={`text-[10px] mt-0.5 whitespace-nowrap
                ${active ? "text-blue-600 font-semibold"
                  : done ? "text-green-600"
                  : "text-gray-400"}`}>
                {STATUS_LABELS[step] ?? step}
              </span>
            </div>
            {i < STATUS_STEPS.length - 1 && (
              <div className={`h-0.5 w-6 mb-3 ${i < currentIdx ? "bg-green-400" : "bg-gray-200"}`} />
            )}
          </div>
        );
      })}
      {isTerminal && currentStatus !== "Closed" && (
        <div className="flex items-center gap-1 ml-1">
          <div className="h-0.5 w-6 mb-3 bg-red-300" />
          <div className="flex flex-col items-center">
            <div className="h-6 w-6 rounded-full flex items-center justify-center border-2 border-red-500 bg-red-500 text-white">
              <XCircle className="h-3.5 w-3.5" />
            </div>
            <span className="text-[10px] mt-0.5 text-red-600 font-semibold">
              {STATUS_LABELS[currentStatus]}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

interface ScheduleModalProps {
  onConfirm: (start: string, end: string) => void;
  onCancel: () => void;
  loading: boolean;
}

function ScheduleModal({ onConfirm, onCancel, loading }: ScheduleModalProps) {
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-4">
        <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
          <Calendar className="h-5 w-5 text-blue-500" />
          実装スケジュール設定
        </h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">開始日時</label>
            <input
              type="datetime-local"
              value={startAt}
              onChange={e => setStartAt(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">終了日時（任意）</label>
            <input
              type="datetime-local"
              value={endAt}
              onChange={e => setEndAt(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            キャンセル
          </button>
          <button
            disabled={!startAt || loading}
            onClick={() => onConfirm(startAt, endAt)}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "設定中..." : "スケジュール確定"}
          </button>
        </div>
      </div>
    </div>
  );
}

interface CABApprovalModalProps {
  onConfirm: (approved: boolean, notes: string) => void;
  onCancel: () => void;
  loading: boolean;
}

function CABApprovalModal({ onConfirm, onCancel, loading }: CABApprovalModalProps) {
  const [notes, setNotes] = useState("");
  const [decision, setDecision] = useState<boolean | null>(null);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-4">
        <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
          <Shield className="h-5 w-5 text-blue-500" />
          CAB 承認・却下
        </h3>
        <div className="flex gap-3">
          <button
            onClick={() => setDecision(true)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors
              ${decision === true ? "bg-green-600 text-white border-green-600" : "border-gray-300 text-gray-700 hover:border-green-400"}`}
          >
            ✓ 承認
          </button>
          <button
            onClick={() => setDecision(false)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors
              ${decision === false ? "bg-red-600 text-white border-red-600" : "border-gray-300 text-gray-700 hover:border-red-400"}`}
          >
            ✗ 却下
          </button>
        </div>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          placeholder="コメント（任意）"
          rows={3}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            キャンセル
          </button>
          <button
            disabled={decision === null || loading}
            onClick={() => decision !== null && onConfirm(decision, notes)}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "処理中..." : "確定"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ChangeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const changeId = params.id as string;

  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [showCABModal, setShowCABModal] = useState(false);
  const [actionError, setActionError] = useState("");

  const { data: change, isLoading, error } = useQuery({
    queryKey: ["change", changeId],
    queryFn: () => apiClient.get<ChangeResponse>(`/changes/${changeId}`).then((r) => r.data),
    enabled: !!changeId,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["change", changeId] });
    queryClient.invalidateQueries({ queryKey: ["changes"] });
    setActionError("");
  };

  const handleError = (e: unknown) => {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "操作に失敗しました";
    setActionError(typeof msg === "string" ? msg : JSON.stringify(msg));
  };

  const submitForCABMutation = useMutation({
    mutationFn: () => apiClient.post(`/changes/${changeId}/submit-for-cab`).then(r => r.data),
    onSuccess: invalidate,
    onError: handleError,
  });

  const cabApprovalMutation = useMutation({
    mutationFn: ({ approved, notes }: { approved: boolean; notes: string }) =>
      apiClient.post(`/changes/${changeId}/cab-approval`, { approved, notes }).then(r => r.data),
    onSuccess: () => { invalidate(); setShowCABModal(false); },
    onError: handleError,
  });

  const scheduleMutation = useMutation({
    mutationFn: ({ scheduled_start_at, scheduled_end_at }: { scheduled_start_at: string; scheduled_end_at?: string }) =>
      apiClient.post(`/changes/${changeId}/schedule`, { scheduled_start_at, scheduled_end_at }).then(r => r.data),
    onSuccess: () => { invalidate(); setShowScheduleModal(false); },
    onError: handleError,
  });

  const implementMutation = useMutation({
    mutationFn: () => apiClient.post(`/changes/${changeId}/implement`).then(r => r.data),
    onSuccess: invalidate,
    onError: handleError,
  });

  const completeMutation = useMutation({
    mutationFn: () => apiClient.post(`/changes/${changeId}/complete`).then(r => r.data),
    onSuccess: invalidate,
    onError: handleError,
  });

  const closeMutation = useMutation({
    mutationFn: () => apiClient.post(`/changes/${changeId}/close`).then(r => r.data),
    onSuccess: invalidate,
    onError: handleError,
  });

  const cancelMutation = useMutation({
    mutationFn: () =>
      apiClient.post(`/changes/${changeId}/transitions`, { new_status: "Cancelled" }).then(r => r.data),
    onSuccess: invalidate,
    onError: handleError,
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

  const riskColors = getRiskColor(change.risk_score);
  const isTerminal = TERMINAL_STATUSES.includes(change.status);

  return (
    <div className="space-y-5 max-w-4xl">
      {showScheduleModal && (
        <ScheduleModal
          loading={scheduleMutation.isPending}
          onCancel={() => setShowScheduleModal(false)}
          onConfirm={(start, end) => {
            const payload: { scheduled_start_at: string; scheduled_end_at?: string } = {
              scheduled_start_at: new Date(start).toISOString(),
            };
            if (end) payload.scheduled_end_at = new Date(end).toISOString();
            scheduleMutation.mutate(payload);
          }}
        />
      )}
      {showCABModal && (
        <CABApprovalModal
          loading={cabApprovalMutation.isPending}
          onCancel={() => setShowCABModal(false)}
          onConfirm={(approved, notes) => cabApprovalMutation.mutate({ approved, notes })}
        />
      )}

      {/* ヘッダー */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <button
          onClick={() => router.push("/changes")}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          変更管理
        </button>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Draft: CABレビュー申請 */}
          {change.status === "Draft" && (
            <Button
              variant="primary"
              size="sm"
              loading={submitForCABMutation.isPending}
              icon={<Send className="h-4 w-4" />}
              onClick={() => submitForCABMutation.mutate()}
            >
              CABレビューに申請
            </Button>
          )}
          {/* CAB_Review: 承認・却下（管理者向け） */}
          {change.status === "CAB_Review" && (
            <Button
              variant="primary"
              size="sm"
              icon={<Shield className="h-4 w-4" />}
              onClick={() => setShowCABModal(true)}
            >
              CAB 承認・却下
            </Button>
          )}
          {/* Approved: スケジュール設定 */}
          {change.status === "Approved" && (
            <Button
              variant="primary"
              size="sm"
              icon={<Calendar className="h-4 w-4" />}
              onClick={() => setShowScheduleModal(true)}
            >
              スケジュール設定
            </Button>
          )}
          {/* Scheduled: 実装開始 */}
          {change.status === "Scheduled" && (
            <Button
              variant="primary"
              size="sm"
              loading={implementMutation.isPending}
              icon={<Play className="h-4 w-4" />}
              onClick={() => implementMutation.mutate()}
            >
              実装開始
            </Button>
          )}
          {/* In_Progress: 実装完了 */}
          {change.status === "In_Progress" && (
            <Button
              variant="primary"
              size="sm"
              loading={completeMutation.isPending}
              icon={<CheckCircle2 className="h-4 w-4" />}
              onClick={() => completeMutation.mutate()}
            >
              実装完了
            </Button>
          )}
          {/* Completed: クローズ */}
          {change.status === "Completed" && (
            <Button
              variant="secondary"
              size="sm"
              loading={closeMutation.isPending}
              icon={<Archive className="h-4 w-4" />}
              onClick={() => closeMutation.mutate()}
            >
              クローズ
            </Button>
          )}
          {/* Cancel (terminal 以外) */}
          {!isTerminal && (
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

      {actionError && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {actionError}
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
            {STATUS_LABELS[change.status] ?? change.status.replace(/_/g, " ")}
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
            {change.risk_level && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">リスクレベル</span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${riskColors.text} ${riskColors.bg}`}>
                  {change.risk_level}
                </span>
              </div>
            )}
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
                <span className="text-xs font-mono text-gray-600 truncate max-w-[140px]">{change.requested_by}</span>
              </div>
            )}
            {change.cab_approved_by && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> CAB承認者
                </span>
                <span className="text-xs font-mono text-gray-600 truncate max-w-[140px]">{change.cab_approved_by}</span>
              </div>
            )}
            {change.cab_reviewed_at && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" /> CABレビュー日時
                </span>
                <span className="text-xs text-gray-600">
                  {new Date(change.cab_reviewed_at).toLocaleString("ja-JP", {
                    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                  })}
                </span>
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
                  <Square className="h-3.5 w-3.5" /> 終了予定
                </span>
                <span className="text-sm text-gray-700">
                  {new Date(change.scheduled_end_at).toLocaleString("ja-JP", {
                    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                  })}
                </span>
              </div>
            )}
            {change.actual_start_at && (
              <div className="flex items-center justify-between border-t border-gray-50 pt-2">
                <span className="text-sm text-gray-500 flex items-center gap-1.5">
                  <Play className="h-3.5 w-3.5 text-blue-500" /> 実装開始
                </span>
                <span className="text-xs text-gray-600">
                  {new Date(change.actual_start_at).toLocaleString("ja-JP", {
                    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                  })}
                </span>
              </div>
            )}
            {change.actual_end_at && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> 実装完了
                </span>
                <span className="text-xs text-gray-600">
                  {new Date(change.actual_end_at).toLocaleString("ja-JP", {
                    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                  })}
                </span>
              </div>
            )}
            <div className="flex items-center justify-between border-t border-gray-50 pt-2">
              <span className="text-xs text-gray-400">作成日時</span>
              <span className="text-xs text-gray-400">
                {new Date(change.created_at).toLocaleString("ja-JP", {
                  month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                })}
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
          <StatusTimeline currentStatus={change.status} />
        </div>
      </div>

      {/* CABノート */}
      {change.cab_notes && (
        <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 space-y-2">
          <h3 className="text-xs font-semibold text-blue-600 flex items-center gap-1.5">
            <Shield className="h-3.5 w-3.5" /> CABコメント
          </h3>
          <p className="text-sm text-blue-800 whitespace-pre-wrap">{change.cab_notes}</p>
        </div>
      )}

      {/* 計画メモ */}
      {(change.implementation_plan || change.rollback_plan || change.test_plan) && (
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
        </div>
      )}
    </div>
  );
}
