/**
 * バックアップ管理ページ - バックアップ作成・一覧・ダウンロード・削除
 */
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { HardDrive, RefreshCw, Download, Trash2, Database, Clock } from "lucide-react";
import apiClient from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

interface BackupFile {
  filename: string;
  size_bytes: number;
  created_at: string;
}

interface BackupListResponse {
  backups: BackupFile[];
  total: number;
}

interface BackupStatusResponse {
  backup_dir: string;
  db_type: string;
  total_backups: number;
  last_backup: BackupFile | null;
}

interface CreateBackupResponse {
  filename: string;
  size_bytes: number;
  created_at: string;
  type: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(isoStr: string): string {
  return new Date(isoStr).toLocaleString("ja-JP");
}

export default function BackupPage() {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const statusQuery = useQuery<BackupStatusResponse>({
    queryKey: ["backup-status"],
    queryFn: () => apiClient.get("/backup/status").then((r) => r.data),
  });

  const listQuery = useQuery<BackupListResponse>({
    queryKey: ["backup-list"],
    queryFn: () => apiClient.get("/backup/list").then((r) => r.data),
  });

  const createMutation = useMutation<CreateBackupResponse>({
    mutationFn: () => apiClient.post("/backup/create").then((r) => r.data),
    onSuccess: (data) => {
      setMessage({ type: "success", text: `バックアップを作成しました: ${data.filename}` });
      queryClient.invalidateQueries({ queryKey: ["backup-list"] });
      queryClient.invalidateQueries({ queryKey: ["backup-status"] });
    },
    onError: () => {
      setMessage({ type: "error", text: "バックアップの作成に失敗しました" });
    },
  });

  const deleteMutation = useMutation<void, Error, string>({
    mutationFn: (filename: string) => apiClient.delete(`/backup/${filename}`).then((r) => r.data),
    onSuccess: () => {
      setMessage({ type: "success", text: "バックアップを削除しました" });
      queryClient.invalidateQueries({ queryKey: ["backup-list"] });
      queryClient.invalidateQueries({ queryKey: ["backup-status"] });
    },
    onError: () => {
      setMessage({ type: "error", text: "削除に失敗しました" });
    },
  });

  const handleDownload = (filename: string) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const a = document.createElement("a");
    a.href = `${base}/backup/download/${filename}`;
    if (token) {
      // Axiosを通じてダウンロード
      apiClient
        .get(`/backup/download/${filename}`, { responseType: "blob" })
        .then((res) => {
          const url = window.URL.createObjectURL(new Blob([res.data]));
          a.href = url;
          a.download = filename;
          a.click();
          window.URL.revokeObjectURL(url);
        });
    } else {
      a.download = filename;
      a.click();
    }
  };

  const handleDelete = (filename: string) => {
    if (!window.confirm(`${filename} を削除しますか？`)) return;
    deleteMutation.mutate(filename);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <HardDrive className="h-7 w-7 text-green-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">バックアップ管理</h1>
            <p className="text-sm text-gray-500">データベースのバックアップ作成・管理</p>
          </div>
        </div>
        <button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
          className="flex items-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          {createMutation.isPending ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <Database className="h-4 w-4" />
          )}
          今すぐバックアップ
        </button>
      </div>

      {/* メッセージ */}
      {message && (
        <div
          className={`rounded-md px-4 py-3 text-sm font-medium ${
            message.type === "success"
              ? "bg-green-50 text-green-700 border border-green-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {message.text}
          <button onClick={() => setMessage(null)} className="ml-4 text-xs underline opacity-70 hover:opacity-100">
            閉じる
          </button>
        </div>
      )}

      {/* ステータスカード */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          {
            label: "DBタイプ",
            value: statusQuery.data?.db_type?.toUpperCase() ?? "—",
            icon: Database,
          },
          {
            label: "バックアップ保存先",
            value: statusQuery.data?.backup_dir ?? "—",
            icon: HardDrive,
            small: true,
          },
          {
            label: "バックアップ数",
            value: statusQuery.data?.total_backups?.toString() ?? "—",
            icon: Database,
          },
          {
            label: "最終バックアップ",
            value: statusQuery.data?.last_backup
              ? formatDate(statusQuery.data.last_backup.created_at)
              : "なし",
            icon: Clock,
            small: true,
          },
        ].map((card) => (
          <div key={card.label} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <card.icon className="h-4 w-4 text-gray-400" />
              <span className="text-xs text-gray-500">{card.label}</span>
            </div>
            <div className={`font-semibold text-gray-800 ${card.small ? "text-xs break-all" : "text-lg"}`}>
              {statusQuery.isLoading ? "…" : card.value}
            </div>
          </div>
        ))}
      </div>

      {/* バックアップ一覧 */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">バックアップファイル一覧</h2>
          <button
            onClick={() => listQuery.refetch()}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${listQuery.isFetching ? "animate-spin" : ""}`} />
            更新
          </button>
        </div>

        {listQuery.isLoading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="md" message="一覧を読み込み中..." />
          </div>
        ) : listQuery.data?.backups.length === 0 ? (
          <div className="py-12 text-center text-gray-400 text-sm">
            バックアップファイルがありません。「今すぐバックアップ」から作成してください。
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-gray-600">ファイル名</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-600 w-28">サイズ</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-600 w-44">作成日時</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-600 w-28">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {listQuery.data?.backups.map((backup) => (
                  <tr key={backup.filename} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-700">{backup.filename}</td>
                    <td className="px-4 py-3 text-gray-500">{formatBytes(backup.size_bytes)}</td>
                    <td className="px-4 py-3 text-gray-500">{formatDate(backup.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleDownload(backup.filename)}
                          title="ダウンロード"
                          className="rounded p-1 text-blue-600 hover:bg-blue-50"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(backup.filename)}
                          disabled={deleteMutation.isPending}
                          title="削除"
                          className="rounded p-1 text-red-500 hover:bg-red-50 disabled:opacity-40"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
