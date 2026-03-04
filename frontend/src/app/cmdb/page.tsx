/**
 * CMDBページ（CI管理）
 * Configuration Item の一覧・検索・フィルター・詳細モーダルを提供
 */
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, ChevronRight, X, Search, Plus, Share2, Download, Upload } from "lucide-react";
import apiClient from "@/lib/api";
import Table from "@/components/ui/Table";
import Badge from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import type { CI, PaginatedResponse } from "@/types/api";

const PAGE_SIZE = 20;

const CI_TYPES = ["Server", "Network", "Application", "Database", "Virtual", "Container"] as const;
const CI_STATUSES = ["Active", "Inactive", "Maintenance", "Retired"] as const;

function getCiTypeVariant(type: string): "info" | "warning" | "success" | "default" {
  switch (type) {
    case "Server": return "info";
    case "Network": return "warning";
    case "Application": return "success";
    case "Database": return "info";
    default: return "default";
  }
}

function getCiStatusVariant(status: string): "success" | "danger" | "warning" | "default" {
  switch (status) {
    case "Active": return "success";
    case "Inactive": return "danger";
    case "Maintenance": return "warning";
    case "Retired": return "default";
    default: return "default";
  }
}

export default function CMDBPage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [skip, setSkip] = useState(0);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterDepartment, setFilterDepartment] = useState("");
  const [selectedCI, setSelectedCI] = useState<CI | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [importResult, setImportResult] = useState<{ created: number; failed: number; errors: string[] } | null>(null);
  const [form, setForm] = useState({ ci_name: "", ci_type: "Server", ci_class: "", version: "", description: "" });
  const [createError, setCreateError] = useState("");

  const handleExport = async (format: "json" | "csv") => {
    setShowExportMenu(false);
    const response = await apiClient.get(`/cmdb/export?format=${format}`, { responseType: "blob" });
    const url = URL.createObjectURL(response.data as Blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cmdb_export.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await apiClient.post<{ created: number; failed: number; errors: string[] }>(
        "/cmdb/import",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setImportResult(res.data);
      queryClient.invalidateQueries({ queryKey: ["cmdb-cis"] });
    } catch {
      setImportResult({ created: 0, failed: 1, errors: ["インポートに失敗しました"] });
    }
    e.target.value = "";
  };

  const createMutation = useMutation({
    mutationFn: (data: typeof form) =>
      apiClient.post("/cmdb/cis", {
        ci_name: data.ci_name,
        ci_type: data.ci_type,
        ci_class: data.ci_class || undefined,
        version: data.version || undefined,
        description: data.description || undefined,
      }).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cmdb-cis"] });
      setShowCreate(false);
      setForm({ ci_name: "", ci_type: "Server", ci_class: "", version: "", description: "" });
      setCreateError("");
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setCreateError(msg ?? "CI登録に失敗しました");
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.ci_name.trim()) { setCreateError("CI名は必須です"); return; }
    setCreateError("");
    createMutation.mutate(form);
  };

  const { data, isLoading, error } = useQuery({
    queryKey: ["cmdb-cis", skip, search, filterType, filterStatus, filterDepartment],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<CI> | CI[]>("/cmdb/cis", {
          params: {
            skip,
            limit: PAGE_SIZE,
            ...(search && { name: search }),
            ...(filterType && { ci_type: filterType }),
            ...(filterStatus && { status: filterStatus }),
            ...(filterDepartment && { department: filterDepartment }),
          },
        })
        .then((r) => r.data),
  });

  if (isLoading) {
    return <LoadingSpinner size="lg" message="CIを読み込み中..." />;
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
        CI一覧の取得に失敗しました。
      </div>
    );
  }

  const isPaginated = data && !Array.isArray(data) && "items" in data;
  const cis: CI[] = isPaginated
    ? (data as PaginatedResponse<CI>).items
    : Array.isArray(data)
      ? (data as CI[])
      : [];
  const total = isPaginated ? (data as PaginatedResponse<CI>).total : cis.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(skip / PAGE_SIZE) + 1;

  const handleSearch = (val: string) => {
    setSearch(val);
    setSkip(0);
  };

  const handleFilterType = (val: string) => {
    setFilterType(val);
    setSkip(0);
  };

  const handleFilterStatus = (val: string) => {
    setFilterStatus(val);
    setSkip(0);
  };

  const handleFilterDepartment = (val: string) => {
    setFilterDepartment(val);
    setSkip(0);
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">CMDB管理</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{total} 件</span>
          {/* エクスポートドロップダウン */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu((v) => !v)}
              className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
            >
              <Download className="h-4 w-4" /> エクスポート
            </button>
            {showExportMenu && (
              <div className="absolute right-0 mt-1 w-36 rounded-lg border border-gray-200 bg-white shadow-lg z-10">
                <button
                  onClick={() => handleExport("json")}
                  className="block w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                >
                  JSON形式
                </button>
                <button
                  onClick={() => handleExport("csv")}
                  className="block w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                >
                  CSV形式
                </button>
              </div>
            )}
          </div>
          {/* インポートボタン */}
          <label className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition">
            <Upload className="h-4 w-4" /> インポート
            <input type="file" accept=".csv,.json" onChange={handleImport} className="hidden" />
          </label>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 transition"
          >
            <Plus className="h-4 w-4" /> 新規CI登録
          </button>
          <Link
            href="/cmdb/graph"
            className="flex items-center gap-1.5 rounded-lg bg-purple-600 px-3 py-2 text-sm font-medium text-white hover:bg-purple-700 transition"
          >
            <Share2 className="h-4 w-4" /> 依存関係グラフ
          </Link>
        </div>
      </div>

      {/* インポート結果表示 */}
      {importResult && (
        <div className={`mb-4 rounded-lg border p-3 text-sm ${importResult.failed > 0 ? "border-orange-200 bg-orange-50" : "border-green-200 bg-green-50"}`}>
          <div className="flex items-center justify-between">
            <span className={importResult.failed > 0 ? "text-orange-800" : "text-green-800"}>
              インポート完了: {importResult.created} 件作成、{importResult.failed} 件失敗
            </span>
            <button onClick={() => setImportResult(null)} className="text-gray-400 hover:text-gray-600">
              <X className="h-4 w-4" />
            </button>
          </div>
          {importResult.errors.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-xs text-orange-700">
              {importResult.errors.map((e, i) => <li key={i}>・{e}</li>)}
            </ul>
          )}
        </div>
      )}

      {/* フィルター・検索バー */}
      <div className="mb-4 flex flex-wrap gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="CI名で検索..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => handleFilterType(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">全タイプ</option>
          {CI_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => handleFilterStatus(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">全ステータス</option>
          {CI_STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={filterDepartment}
          onChange={(e) => handleFilterDepartment(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">全部署</option>
          {["IT", "HR", "Finance", "Operations", "Development", "Management"].map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        {(search || filterType || filterStatus || filterDepartment) && (
          <button
            onClick={() => { setSearch(""); setFilterType(""); setFilterStatus(""); setFilterDepartment(""); setSkip(0); }}
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium px-2"
          >
            <X className="h-3.5 w-3.5" /> フィルタをリセット
          </button>
        )}
        {/* フィルター結果サマリー */}
        {(filterType || filterStatus) && (
          <div className="flex items-center gap-2 ml-auto">
            {filterType && (
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                タイプ: {filterType}
                <button onClick={() => handleFilterType("")}><X className="h-3 w-3" /></button>
              </span>
            )}
            {filterStatus && (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                状態: {filterStatus}
                <button onClick={() => handleFilterStatus("")}><X className="h-3 w-3" /></button>
              </span>
            )}
          </div>
        )}
      </div>

      <Table<CI>
        columns={[
          { header: "CI名", accessor: "name" },
          {
            header: "タイプ",
            accessor: (row) => (
              <Badge variant={getCiTypeVariant(row.ci_type)}>{row.ci_type}</Badge>
            ),
            className: "w-36",
          },
          {
            header: "ステータス",
            accessor: (row) => (
              <Badge variant={getCiStatusVariant(row.status)}>{row.status}</Badge>
            ),
            className: "w-32",
          },
          {
            header: "担当チーム",
            accessor: (row) => row.team_id ?? "—",
            className: "w-40",
          },
          {
            header: "最終更新",
            accessor: (row) =>
              new Date(row.updated_at).toLocaleDateString("ja-JP"),
            className: "w-32",
          },
        ]}
        data={cis}
        onRowClick={(row) => router.push(`/cmdb/${row.ci_id}`)}
        emptyMessage="CIはありません"
      />

      {/* ページネーション */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {skip + 1}〜{Math.min(skip + PAGE_SIZE, total)} 件 / 全 {total} 件
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
              disabled={skip === 0}
              className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
              前へ
            </button>
            <span className="text-sm text-gray-600">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setSkip(skip + PAGE_SIZE)}
              disabled={skip + PAGE_SIZE >= total}
              className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              次へ
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* CI詳細モーダル */}
      {selectedCI && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setSelectedCI(null)}
        >
          <div
            className="relative w-full max-w-lg rounded-xl bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setSelectedCI(null)}
              className="absolute right-4 top-4 rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
            <h2 className="mb-4 text-lg font-bold text-gray-900">
              {selectedCI.name}
            </h2>
            <dl className="space-y-3 text-sm">
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">CI ID</dt>
                <dd className="font-mono text-gray-800">{selectedCI.ci_id}</dd>
              </div>
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">タイプ</dt>
                <dd>
                  <Badge variant={getCiTypeVariant(selectedCI.ci_type)}>
                    {selectedCI.ci_type}
                  </Badge>
                </dd>
              </div>
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">ステータス</dt>
                <dd>
                  <Badge variant={getCiStatusVariant(selectedCI.status)}>
                    {selectedCI.status}
                  </Badge>
                </dd>
              </div>
              {selectedCI.description && (
                <div className="flex gap-4">
                  <dt className="w-32 text-gray-500">説明</dt>
                  <dd className="text-gray-800">{selectedCI.description}</dd>
                </div>
              )}
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">担当チーム</dt>
                <dd className="text-gray-800">{selectedCI.team_id ?? "—"}</dd>
              </div>
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">関連インシデント数</dt>
                <dd className="font-semibold text-gray-800">
                  {selectedCI.incident_count ?? 0}
                </dd>
              </div>
              {selectedCI.depends_on && selectedCI.depends_on.length > 0 && (
                <div className="flex gap-4">
                  <dt className="w-32 text-gray-500">依存関係</dt>
                  <dd className="flex flex-wrap gap-1">
                    {selectedCI.depends_on.map((dep) => (
                      <span
                        key={dep}
                        className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-600"
                      >
                        {dep}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">作成日時</dt>
                <dd className="text-gray-800">
                  {new Date(selectedCI.created_at).toLocaleString("ja-JP")}
                </dd>
              </div>
              <div className="flex gap-4">
                <dt className="w-32 text-gray-500">最終更新</dt>
                <dd className="text-gray-800">
                  {new Date(selectedCI.updated_at).toLocaleString("ja-JP")}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      )}

      {/* 新規CI登録モーダル */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-xl bg-white shadow-xl mx-4">
            <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
              <h2 className="text-base font-semibold text-gray-900">新規CI登録</h2>
              <button onClick={() => { setShowCreate(false); setCreateError(""); }} className="rounded p-1 text-gray-400 hover:bg-gray-100">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-5 space-y-4">
              {createError && (
                <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">{createError}</div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">CI名 <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  value={form.ci_name}
                  onChange={(e) => setForm({ ...form, ci_name: e.target.value })}
                  placeholder="例: web-server-01"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">CIタイプ <span className="text-red-500">*</span></label>
                  <select
                    value={form.ci_type}
                    onChange={(e) => setForm({ ...form, ci_type: e.target.value })}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {CI_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">CIクラス</label>
                  <input
                    type="text"
                    value={form.ci_class}
                    onChange={(e) => setForm({ ...form, ci_class: e.target.value })}
                    placeholder="例: Linux"
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">バージョン</label>
                <input
                  type="text"
                  value={form.version}
                  onChange={(e) => setForm({ ...form, version: e.target.value })}
                  placeholder="例: 1.0.0"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">説明</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  rows={3}
                  placeholder="CIの説明を入力..."
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => { setShowCreate(false); setCreateError(""); }} className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50">
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
                >
                  {createMutation.isPending ? "登録中..." : "CI登録"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
