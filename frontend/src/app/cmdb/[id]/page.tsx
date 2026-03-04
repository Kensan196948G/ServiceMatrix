"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import ReactFlow, {
  Node, Edge, Background, Controls, MiniMap,
  useNodesState, useEdgesState, addEdge,
  Connection, MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { ArrowLeft, RefreshCw, Server, Network, Database, Box, Cpu, Container } from "lucide-react";
import apiClient from "@/lib/api";
import type { CI } from "@/types/api";

interface CIRelationship {
  relationship_id: string;
  source_ci_id: string;
  target_ci_id: string;
  relationship_type: string;
}

interface ImpactAnalysis {
  ci_id: string;
  ci_name: string;
  affected_cis: CI[];
  incident_count: number;
}

const CI_TYPE_COLORS: Record<string, string> = {
  Server: "#3b82f6",
  Network: "#f59e0b",
  Application: "#10b981",
  Database: "#8b5cf6",
  Virtual: "#06b6d4",
  Container: "#ec4899",
};

const CI_TYPE_BG: Record<string, string> = {
  Server: "#eff6ff",
  Network: "#fffbeb",
  Application: "#f0fdf4",
  Database: "#faf5ff",
  Virtual: "#ecfeff",
  Container: "#fdf2f8",
};

function CINode({ data }: { data: { label: string; ci_type: string; status: string; isCenter: boolean } }) {
  const color = CI_TYPE_COLORS[data.ci_type] ?? "#6b7280";
  const bg = CI_TYPE_BG[data.ci_type] ?? "#f9fafb";
  return (
    <div
      className={`rounded-xl border-2 px-4 py-3 min-w-[140px] shadow-sm ${data.isCenter ? "ring-2 ring-blue-400 ring-offset-1" : ""}`}
      style={{ borderColor: color, background: bg }}
    >
      <div className="flex items-center gap-2 mb-1">
        <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
        <span className="text-[10px] font-semibold" style={{ color }}>{data.ci_type}</span>
      </div>
      <p className="text-sm font-bold text-gray-800 leading-tight">{data.label}</p>
      <p className={`text-[10px] mt-0.5 ${data.status === "Active" ? "text-green-600" : "text-gray-400"}`}>
        ● {data.status}
      </p>
    </div>
  );
}

const nodeTypes = { ciNode: CINode };

export default function CMDBDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const { data: ci, isLoading } = useQuery<CI>({
    queryKey: ["ci", id],
    queryFn: () => apiClient.get(`/cmdb/cis/${id}`).then(r => r.data),
    enabled: !!id,
  });

  const { data: relationships } = useQuery<CIRelationship[]>({
    queryKey: ["ci-relationships", id],
    queryFn: () => apiClient.get(`/cmdb/cis/${id}/relationships`).then(r => r.data),
    enabled: !!id,
  });

  const { data: impact } = useQuery<ImpactAnalysis>({
    queryKey: ["ci-impact", id],
    queryFn: () => apiClient.get(`/cmdb/cis/${id}/impact`).then(r => r.data),
    enabled: !!id,
  });

  // グラフ構築
  useEffect(() => {
    if (!ci) return;

    const newNodes: Node[] = [
      {
        id: ci.ci_id,
        type: "ciNode",
        position: { x: 300, y: 200 },
        data: { label: ci.name ?? ci.ci_id, ci_type: ci.ci_type, status: ci.status, isCenter: true },
      },
    ];

    const newEdges: Edge[] = [];
    const relatedCIs = impact?.affected_cis ?? [];

    // 影響CIをグラフに追加
    relatedCIs.forEach((related, i) => {
      const angle = (i * 2 * Math.PI) / Math.max(relatedCIs.length, 1);
      const r = 230;
      const x = 300 + r * Math.cos(angle);
      const y = 200 + r * Math.sin(angle);
      newNodes.push({
        id: related.ci_id,
        type: "ciNode",
        position: { x, y },
        data: { label: related.name ?? related.ci_id, ci_type: related.ci_type, status: related.status, isCenter: false },
      });
    });

    // リレーションシップエッジ
    (relationships ?? []).forEach((rel) => {
      const sourceExists = newNodes.some(n => n.id === rel.source_ci_id);
      const targetExists = newNodes.some(n => n.id === rel.target_ci_id);
      if (sourceExists && targetExists) {
        newEdges.push({
          id: rel.relationship_id,
          source: rel.source_ci_id,
          target: rel.target_ci_id,
          label: rel.relationship_type,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: "#94a3b8" },
          labelStyle: { fontSize: 10, fill: "#64748b" },
        });
      } else if (sourceExists || targetExists) {
        // リレーション先がimpact CIsにない場合もエッジ追加
        const missingId = sourceExists ? rel.target_ci_id : rel.source_ci_id;
        const existingId = sourceExists ? rel.source_ci_id : rel.target_ci_id;
        if (!newNodes.some(n => n.id === missingId)) {
          newNodes.push({
            id: missingId,
            type: "ciNode",
            position: { x: 300 + Math.random() * 400 - 200, y: 200 + Math.random() * 400 - 200 },
            data: { label: missingId.slice(0, 8), ci_type: "Server", status: "Unknown", isCenter: false },
          });
        }
        newEdges.push({
          id: rel.relationship_id,
          source: rel.source_ci_id,
          target: rel.target_ci_id,
          label: rel.relationship_type,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: "#94a3b8" },
        });
      }
    });

    // relatedCIsをcenterノードからエッジで繋ぐ（リレーション未定義でも可視化）
    relatedCIs.forEach((related) => {
      const alreadyLinked = newEdges.some(
        e => (e.source === ci.ci_id && e.target === related.ci_id) ||
             (e.source === related.ci_id && e.target === ci.ci_id)
      );
      if (!alreadyLinked) {
        newEdges.push({
          id: `impact-${related.ci_id}`,
          source: ci.ci_id,
          target: related.ci_id,
          label: "影響",
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: "#f97316", strokeDasharray: "4 2" },
          labelStyle: { fontSize: 10, fill: "#f97316" },
        });
      }
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [ci, relationships, impact, setNodes, setEdges]);

  const onConnect = useCallback(
    (connection: Connection) => setEdges(eds => addEdge(connection, eds)),
    [setEdges]
  );

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center"><RefreshCw className="w-6 h-6 animate-spin text-blue-500" /></div>;
  }

  if (!ci) {
    return (
      <div className="p-6 text-center text-red-600">
        CIが見つかりませんでした
        <button onClick={() => router.push("/cmdb")} className="block mx-auto mt-3 text-sm text-blue-600 hover:underline">CMDB一覧へ戻る</button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => router.push("/cmdb")} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">{ci.name ?? ci.ci_id}</h1>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs font-mono text-gray-400">{ci.ci_id}</span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ background: CI_TYPE_BG[ci.ci_type] ?? "#f3f4f6", color: CI_TYPE_COLORS[ci.ci_type] ?? "#374151" }}>
              {ci.ci_type}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${ci.status === "Active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
              {ci.status}
            </span>
          </div>
        </div>
      </div>

      {/* 影響分析サマリー */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-orange-600">{impact?.affected_cis?.length ?? 0}</p>
          <p className="text-xs text-gray-500 mt-0.5">影響を受けるCI数</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-red-600">{impact?.incident_count ?? ci.incident_count ?? 0}</p>
          <p className="text-xs text-gray-500 mt-0.5">関連インシデント数</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-blue-600">{relationships?.length ?? 0}</p>
          <p className="text-xs text-gray-500 mt-0.5">依存関係数</p>
        </div>
      </div>

      {/* 依存関係グラフ */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">依存関係グラフ</h2>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-gray-400 inline-block" /> 依存関係</span>
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-orange-400 inline-block border-dashed border-t border-orange-400" /> 影響関係</span>
          </div>
        </div>
        <div style={{ height: "480px" }}>
          {nodes.length === 0 ? (
            <div className="flex h-full items-center justify-center text-gray-400">
              <div className="text-center">
                <Server className="w-10 h-10 mx-auto mb-2 text-gray-200" />
                <p className="text-sm">依存関係データがありません</p>
              </div>
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              fitView
              attributionPosition="bottom-right"
            >
              <Background color="#f1f5f9" gap={20} />
              <Controls />
              <MiniMap nodeColor={(n) => CI_TYPE_COLORS[(n.data as { ci_type: string }).ci_type] ?? "#94a3b8"} />
            </ReactFlow>
          )}
        </div>
      </div>

      {/* CI詳細情報 */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-900 mb-3">CI詳細情報</h2>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
          {[
            { label: "CI名", value: ci.name ?? "—" },
            { label: "CIタイプ", value: ci.ci_type },
            { label: "CIクラス", value: ci.ci_class ?? "—" },
            { label: "ステータス", value: ci.status },
            { label: "バージョン", value: ci.version ?? "—" },
            { label: "担当チーム", value: ci.team_id ?? "—" },
            { label: "作成日時", value: new Date(ci.created_at).toLocaleString("ja-JP") },
            { label: "最終更新", value: new Date(ci.updated_at).toLocaleString("ja-JP") },
          ].map(item => (
            <div key={item.label} className="bg-gray-50 rounded p-3">
              <p className="text-xs text-gray-400">{item.label}</p>
              <p className="font-medium text-gray-800 mt-0.5">{item.value}</p>
            </div>
          ))}
        </dl>
        {ci.description && (
          <div className="mt-4">
            <p className="text-xs text-gray-400 mb-1">説明</p>
            <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded">{ci.description}</p>
          </div>
        )}
      </div>
    </div>
  );
}
