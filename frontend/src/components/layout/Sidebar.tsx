/**
 * Sidebar コンポーネント - Jira風ダークサイドバー
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertTriangle,
  GitPullRequest,
  HelpCircle,
  ClipboardList,
  ShieldAlert,
  Brain,
  Database,
  ScrollText,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";

interface NavGroup {
  label?: string;
  items: NavItem[];
}

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
}

const navGroups: NavGroup[] = [
  {
    items: [
      { label: "ダッシュボード", href: "/", icon: LayoutDashboard },
    ],
  },
  {
    label: "ITSMプロセス",
    items: [
      { label: "インシデント", href: "/incidents", icon: AlertTriangle },
      { label: "変更管理", href: "/changes", icon: GitPullRequest },
      { label: "問題管理", href: "/problems", icon: HelpCircle },
      { label: "サービスリクエスト", href: "/service-requests", icon: ClipboardList },
    ],
  },
  {
    label: "監視・統治",
    items: [
      { label: "SLA監視", href: "/sla", icon: ShieldAlert },
      { label: "AI分析", href: "/ai", icon: Brain },
      { label: "CMDB管理", href: "/cmdb", icon: Database },
      { label: "監査ログ", href: "/audit-logs", icon: ScrollText },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-60 flex-col bg-[#1e2433] text-gray-100 flex-shrink-0">
      {/* ロゴ */}
      <div className="flex h-14 items-center px-4 border-b border-white/10">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500 font-bold text-white text-sm">
            SM
          </div>
          <div>
            <div className="text-sm font-bold text-white leading-tight">ServiceMatrix</div>
            <div className="text-[10px] text-gray-400 leading-tight">ITSM Governance</div>
          </div>
        </Link>
      </div>

      {/* ナビゲーション */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {navGroups.map((group, gi) => (
          <div key={gi} className={gi > 0 ? "mt-4" : ""}>
            {group.label && (
              <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                {group.label}
              </p>
            )}
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href));

                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors group ${
                        isActive
                          ? "bg-blue-600 text-white"
                          : "text-gray-300 hover:bg-white/10 hover:text-white"
                      }`}
                    >
                      <span className="flex items-center gap-2.5">
                        <item.icon className={`h-4 w-4 flex-shrink-0 ${isActive ? "text-white" : "text-gray-400 group-hover:text-white"}`} />
                        <span className="truncate">{item.label}</span>
                      </span>
                      {isActive && <ChevronRight className="h-3.5 w-3.5 text-white/60" />}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* フッター */}
      <div className="border-t border-white/10 px-4 py-3">
        <p className="text-[10px] text-gray-500">v1.0.0 · ITIL 4 準拠</p>
      </div>
    </aside>
  );
}
