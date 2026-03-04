/**
 * インシデントサマリウィジェット - インシデント統計を表示
 */
"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { IncidentResponse } from "@/types/api";

interface IncidentSummaryWidgetProps {
  incidents: IncidentResponse[];
  total?: number;
  title?: string;
}

export default function IncidentSummaryWidget({
  incidents,
  total,
  title = "インシデントサマリ",
}: IncidentSummaryWidgetProps) {
  const open = incidents.filter(
    (i) => !["Resolved", "Closed"].includes(i.status)
  ).length;
  const critical = incidents.filter((i) => i.priority === "P1").length;
  const breached = incidents.filter((i) => i.sla_breached).length;
  const displayTotal = total ?? incidents.length;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="h-4 w-4 text-orange-500" />
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-2xl font-bold text-gray-900">{open}</p>
          <p className="text-xs text-gray-500">オープン</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-red-600">{critical}</p>
          <p className="text-xs text-gray-500">P1緊急</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-orange-500">{breached}</p>
          <p className="text-xs text-gray-500">SLA違反</p>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-gray-400">
        <span>合計 {displayTotal}件</span>
        {breached === 0 ? (
          <span className="flex items-center gap-1 text-green-500">
            <CheckCircle2 className="h-3 w-3" /> SLA正常
          </span>
        ) : (
          <Link href="/sla" className="text-red-500 hover:underline">
            SLA確認 →
          </Link>
        )}
      </div>
    </div>
  );
}
