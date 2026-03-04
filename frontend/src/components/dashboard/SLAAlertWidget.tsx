/**
 * SLAアラートウィジェット - SLA違反・警告インシデントを表示
 */
"use client";

import Link from "next/link";
import { AlertTriangle, XCircle } from "lucide-react";
import type { IncidentResponse } from "@/types/api";

interface SLAAlertWidgetProps {
  incidents: IncidentResponse[];
}

export default function SLAAlertWidget({ incidents }: SLAAlertWidgetProps) {
  const breached = incidents.filter((i) => i.sla_breached);

  if (breached.length === 0) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
        ✅ SLA違反なし
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle className="h-5 w-5 text-red-500 shrink-0" />
        <p className="text-sm font-semibold text-red-800">
          SLA違反 <strong>{breached.length}件</strong>
        </p>
      </div>
      <ul className="space-y-1">
        {breached.slice(0, 5).map((inc) => (
          <li key={inc.incident_id} className="flex items-center gap-2 text-xs text-red-700">
            <XCircle className="h-3 w-3 shrink-0" />
            <Link
              href={`/incidents/${inc.incident_id}`}
              className="hover:underline truncate"
            >
              [{inc.incident_number}] {inc.title}
            </Link>
          </li>
        ))}
      </ul>
      {breached.length > 5 && (
        <Link href="/sla" className="mt-2 block text-xs text-red-600 hover:underline">
          他 {breached.length - 5} 件を表示 →
        </Link>
      )}
    </div>
  );
}
