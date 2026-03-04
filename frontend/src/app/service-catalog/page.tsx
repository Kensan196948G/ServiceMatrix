/**
 * サービスカタログページ
 */
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Clock, Tag, CheckCircle2, AlertCircle } from "lucide-react";
import apiClient from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Button from "@/components/ui/Button";

interface CatalogItem {
  catalog_id: string;
  name: string;
  description?: string;
  category?: string;
  sla_hours?: number;
  is_active: boolean;
}

export default function ServiceCatalogPage() {
  const queryClient = useQueryClient();
  const [requesting, setRequesting] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery<CatalogItem[]>({
    queryKey: ["service-catalog"],
    queryFn: () => apiClient.get("/service-catalog").then((r) => r.data),
  });

  const requestMutation = useMutation({
    mutationFn: (catalogId: string) =>
      apiClient.post(`/service-catalog/${catalogId}/request`).then((r) => r.data),
    onSuccess: (data) => {
      setSuccessMsg(`サービスリクエスト ${data.request_number} を作成しました`);
      setRequesting(null);
      queryClient.invalidateQueries({ queryKey: ["service-requests"] });
      setTimeout(() => setSuccessMsg(null), 4000);
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "申請に失敗しました";
      setErrorMsg(typeof msg === "string" ? msg : JSON.stringify(msg));
      setRequesting(null);
      setTimeout(() => setErrorMsg(null), 4000);
    },
  });

  const handleRequest = (catalogId: string) => {
    setRequesting(catalogId);
    setErrorMsg(null);
    requestMutation.mutate(catalogId);
  };

  const catalogs: CatalogItem[] = data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-blue-500" />
            サービスカタログ
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">利用可能なサービス一覧</p>
        </div>
      </div>

      {successMsg && (
        <div className="flex items-center gap-2 p-3 rounded-md bg-green-50 text-green-700 text-sm border border-green-200">
          <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
          {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="flex items-center gap-2 p-3 rounded-md bg-red-50 text-red-700 text-sm border border-red-200">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {errorMsg}
        </div>
      )}

      {isLoading && (
        <div className="flex justify-center py-12">
          <LoadingSpinner />
        </div>
      )}

      {error && (
        <div className="text-center py-12 text-red-500 text-sm">
          データの取得に失敗しました
        </div>
      )}

      {!isLoading && !error && catalogs.length === 0 && (
        <div className="text-center py-12 text-gray-400 text-sm">
          利用可能なサービスがありません
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {catalogs.map((item) => (
          <div
            key={item.catalog_id}
            className="bg-white rounded-lg border border-gray-200 p-5 flex flex-col gap-3 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between gap-2">
              <h2 className="text-base font-semibold text-gray-900 leading-snug">{item.name}</h2>
              {item.category && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-100 whitespace-nowrap">
                  <Tag className="h-3 w-3" />
                  {item.category}
                </span>
              )}
            </div>

            {item.description && (
              <p className="text-sm text-gray-600 leading-relaxed line-clamp-3">
                {item.description}
              </p>
            )}

            <div className="flex items-center gap-2 mt-auto pt-2 border-t border-gray-100">
              {item.sla_hours != null && (
                <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                  <Clock className="h-3.5 w-3.5" />
                  SLA: {item.sla_hours}時間
                </span>
              )}
              <div className="ml-auto">
                <Button
                  size="sm"
                  onClick={() => handleRequest(item.catalog_id)}
                  disabled={requesting === item.catalog_id || requestMutation.isPending}
                >
                  {requesting === item.catalog_id ? "申請中..." : "リクエスト申請"}
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
