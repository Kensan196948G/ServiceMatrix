/**
 * 承認待ちウィジェット - 承認待ち変更要求を表示
 */
"use client";

import Link from "next/link";
import { GitPullRequest } from "lucide-react";

interface Change {
  change_id: string;
  change_number?: string;
  title: string;
  status: string;
}

interface PendingApprovalsWidgetProps {
  changes: Change[];
}

export default function PendingApprovalsWidget({ changes }: PendingApprovalsWidgetProps) {
  const pending = changes.filter((c) => c.status === "Pending" || c.status === "CAB_Review");

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <GitPullRequest className="h-5 w-5 text-blue-600" />
        <h3 className="text-sm font-semibold text-blue-800">承認待ち変更要求</h3>
        <span className="ml-auto rounded-full bg-blue-600 px-2 py-0.5 text-xs text-white font-bold">
          {pending.length}
        </span>
      </div>
      {pending.length === 0 ? (
        <p className="text-xs text-blue-600">承認待ち変更はありません</p>
      ) : (
        <ul className="space-y-1.5">
          {pending.slice(0, 5).map((c) => (
            <li key={c.change_id} className="text-xs text-blue-700 hover:underline truncate">
              <Link href={`/changes/${c.change_id}`}>
                {c.change_number && <span className="font-mono mr-1">[{c.change_number}]</span>}
                {c.title}
              </Link>
            </li>
          ))}
        </ul>
      )}
      {pending.length > 5 && (
        <Link href="/changes" className="mt-2 block text-xs text-blue-600 hover:underline">
          すべて表示 ({pending.length}件) →
        </Link>
      )}
    </div>
  );
}
