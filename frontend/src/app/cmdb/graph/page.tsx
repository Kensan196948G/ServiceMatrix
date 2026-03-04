"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Node,
  Edge,
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import apiClient from "@/lib/api";
import { useAuthStore } from "@/hooks/useAuth";
import Link from "next/link";
import { ArrowLeft, RefreshCw, ZoomIn } from "lucide-react";

interface CI {
  ci_id: string;
  name: string;
  ci_type: string;
  status: string;
}

interface CIRelationship {
  relationship_id: string;
  source_ci_id: string;
  target_ci_id: string;
  relationship_type: string;
}

const CI_TYPE_COLORS: Record<string, string> = {
  Server: "#3b82f6",
  Database: "#8b5cf6",
  Application: "#10b981",
  Network: "#f59e0b",
  Storage: "#ef4444",
  Service: "#06b6d4",
  VM: "#6366f1",
};

function getCIColor(ciType: string): string {
  return CI_TYPE_COLORS[ciType] || "#6b7280";
}

function buildGraph(cis: CI[], relationships: CIRelationship[]) {
  const COLS = 4;
  const X_GAP = 220;
  const Y_GAP = 140;

  const nodes: Node[] = cis.map((ci, i) => ({
    id: ci.ci_id,
    type: "default",
    data: {
      label: (
        <div className="text-center">
          <div className="font-semibold text-sm">{ci.name}</div>
          <div className="text-xs text-gray-500 mt-0.5">{ci.ci_type}</div>
          <div
            className="text-xs mt-1 px-1.5 py-0.5 rounded-full inline-block"
            style={{
              background: ci.status === "Active" ? "#dcfce7" : "#f3f4f6",
              color: ci.status === "Active" ? "#16a34a" : "#6b7280",
            }}
          >
            {ci.status}
          </div>
        </div>
      ),
    },
    position: {
      x: (i % COLS) * X_GAP + 50,
      y: Math.floor(i / COLS) * Y_GAP + 50,
    },
    style: {
      background: "#fff",
      border: `2px solid ${getCIColor(ci.ci_type)}`,
      borderRadius: "8px",
      padding: "8px",
      minWidth: "160px",
    },
  }));

  const edges: Edge[] = relationships.map((rel) => ({
    id: rel.relationship_id,
    source: rel.source_ci_id,
    target: rel.target_ci_id,
    label: rel.relationship_type,
    animated: rel.relationship_type === "depends_on",
    style: { stroke: "#6b7280" },
    labelStyle: { fontSize: 10, fill: "#6b7280" },
  }));

  return { nodes, edges };
}

export default function CMDBGraphPage() {
  const { isAuthenticated } = useAuthStore();
  const [cis, setCIs] = useState<CI[]>([]);
  const [relationships, setRelationships] = useState<CIRelationship[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  const fetchData = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    setError(null);
    try {
      const ciRes = await apiClient.get<CI[]>("/cmdb/cis?size=200");
      const ciList = ciRes.data;

      // 各CIのリレーションシップを取得
      const relPromises = ciList.map((ci) =>
        apiClient
          .get<CIRelationship[]>(`/cmdb/cis/${ci.ci_id}/relationships`)
          .then((r) => r.data)
          .catch(() => [] as CIRelationship[]),
      );
      const relResults = await Promise.all(relPromises);
      const allRels: CIRelationship[] = relResults.flat();

      // 重複排除
      const uniqueRels = Array.from(
        new Map(allRels.map((r) => [r.relationship_id, r])).values(),
      );

      setCIs(ciList);
      setRelationships(uniqueRels);

      const { nodes: newNodes, edges: newEdges } = buildGraph(ciList, uniqueRels);
      setNodes(newNodes);
      setEdges(newEdges);
    } catch (err) {
      setError(err instanceof Error ? err.message : "データの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, setNodes, setEdges]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const legend = useMemo(
    () =>
      Object.entries(CI_TYPE_COLORS).map(([type, color]) => ({
        type,
        color,
      })),
    [],
  );

  return (
    <div className="h-full flex flex-col">
      {/* ヘッダー */}
      <div className="flex items-center justify-between p-4 border-b bg-white">
        <div className="flex items-center gap-3">
          <Link
            href="/cmdb"
            className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft size={16} />
            CMDB一覧へ
          </Link>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <ZoomIn size={20} className="text-blue-600" />
            CMDB 依存関係グラフ
          </h1>
          <span className="text-sm text-gray-500">
            {cis.length} CI・{relationships.length} リレーション
          </span>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          更新
        </button>
      </div>

      {error && (
        <div className="m-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && cis.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <RefreshCw size={32} className="animate-spin mx-auto mb-3" />
            <p>グラフを読み込み中...</p>
          </div>
        </div>
      ) : cis.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <p>CIが登録されていません</p>
        </div>
      ) : (
        <div className="flex-1" style={{ minHeight: "600px" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
            attributionPosition="bottom-right"
          >
            <Controls />
            <MiniMap
              nodeStrokeColor={(n) => {
                const ci = cis.find((c) => c.ci_id === n.id);
                return ci ? getCIColor(ci.ci_type) : "#6b7280";
              }}
              nodeColor={() => "#fff"}
            />
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
            <Panel position="top-left">
              <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                <p className="text-xs font-semibold text-gray-700 mb-2">CI タイプ凡例</p>
                <div className="space-y-1">
                  {legend.map(({ type, color }) => (
                    <div key={type} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-sm border-2"
                        style={{ borderColor: color }}
                      />
                      <span className="text-xs text-gray-600">{type}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Panel>
          </ReactFlow>
        </div>
      )}
    </div>
  );
}
