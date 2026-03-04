/**
 * Sidebar コンポーネント - ライトテーマサイドバー（モバイルドロワー対応）
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
  BookOpen,
  ShieldAlert,
  Brain,
  Database,
  ScrollText,
  Settings,
  Users,
  Bell,
  Lock,
  HardDrive,
  Palette,
  SlidersHorizontal,
  ChevronRight,
  CalendarDays,
  BarChart2,
  X,
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
}

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
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
      { label: "変更カレンダー", href: "/changes/calendar", icon: CalendarDays },
      { label: "問題管理", href: "/problems", icon: HelpCircle },
      { label: "サービスリクエスト", href: "/service-requests", icon: ClipboardList },
      { label: "サービスカタログ", href: "/service-catalog", icon: BookOpen },
    ],
  },
  {
    label: "監視・統治",
    items: [
      { label: "SLA監視", href: "/sla", icon: ShieldAlert },
      { label: "AI分析", href: "/ai", icon: Brain },
      { label: "CMDB管理", href: "/cmdb", icon: Database },
      { label: "監査ログ", href: "/audit-logs", icon: ScrollText },
      { label: "レポート", href: "/reports", icon: BarChart2 },
    ],
  },
  {
    label: "システム管理",
    items: [
      { label: "ユーザー管理", href: "/settings/users", icon: Users },
      { label: "通知管理", href: "/settings/notifications", icon: Bell },
      { label: "セキュリティ管理", href: "/settings/security", icon: Lock },
      { label: "データ管理", href: "/settings/data", icon: HardDrive },
      { label: "外観設定", href: "/settings/appearance", icon: Palette },
      { label: "システム全般", href: "/settings/general", icon: SlidersHorizontal },
    ],
  },
];

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const pathname = usePathname();

  const sidebarContent = (
    <aside className="flex h-full w-60 flex-col bg-white border-r border-gray-200 flex-shrink-0">
      {/* ロゴ */}
      <div className="flex h-14 items-center justify-between px-4 border-b border-gray-200">
        <Link href="/" className="flex items-center gap-2.5" onClick={onClose}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 font-bold text-white text-sm">
            SM
          </div>
          <div>
            <div className="text-sm font-bold text-gray-900 leading-tight">ServiceMatrix</div>
            <div className="text-[10px] text-gray-400 leading-tight">ITSM Governance</div>
          </div>
        </Link>
        {/* モバイル閉じるボタン */}
        {onClose && (
          <button
            onClick={onClose}
            className="md:hidden rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="サイドバーを閉じる"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* ナビゲーション */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {navGroups.map((group, gi) => (
          <div key={gi} className={gi > 0 ? "mt-4" : ""}>
            {group.label && (
              <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
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
                      onClick={onClose}
                      className={`flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors group ${
                        isActive
                          ? "bg-blue-50 text-blue-700 font-medium"
                          : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                      }`}
                    >
                      <span className="flex items-center gap-2.5">
                        <item.icon className={`h-4 w-4 flex-shrink-0 ${isActive ? "text-blue-600" : "text-gray-400 group-hover:text-gray-600"}`} />
                        <span className="truncate">{item.label}</span>
                      </span>
                      {isActive && <ChevronRight className="h-3.5 w-3.5 text-blue-400" />}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* フッター */}
      <div className="border-t border-gray-200 px-4 py-3">
        <p className="text-[10px] text-gray-400">v1.0.0 · ITIL 4 準拠</p>
      </div>
    </aside>
  );

  return (
    <>
      {/* デスクトップ: 固定サイドバー */}
      <div className="hidden md:flex h-full">
        {sidebarContent}
      </div>

      {/* モバイル: オーバーレイドロワー */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          {/* オーバーレイ背景 */}
          <div
            className="absolute inset-0 bg-black/40"
            onClick={onClose}
            aria-hidden="true"
          />
          {/* サイドバー本体 */}
          <div className="relative flex h-full">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
