/**
 * サイドバーナビゲーションコンポーネント
 * ITSMモジュールへのナビゲーションリンクを提供
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertTriangle,
  GitPullRequest,
  Search,
  ClipboardList,
  Settings,
  Gauge,
  type LucideIcon,
} from "lucide-react";

/** ナビゲーション項目の型 */
interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

/** サイドバーナビゲーション項目一覧 */
const navItems: NavItem[] = [
  { label: "ダッシュボード", href: "/", icon: LayoutDashboard },
  { label: "インシデント", href: "/incidents", icon: AlertTriangle },
  { label: "変更管理", href: "/changes", icon: GitPullRequest },
  { label: "問題管理", href: "/problems", icon: Search },
  {
    label: "サービスリクエスト",
    href: "/service-requests",
    icon: ClipboardList,
  },
  { label: "SLAダッシュボード", href: "/sla", icon: Gauge },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 flex-col border-r border-gray-200 bg-white">
      {/* ロゴ・アプリ名 */}
      <div className="flex h-16 items-center border-b border-gray-200 px-6">
        <Link href="/" className="flex items-center gap-2">
          <Settings className="h-6 w-6 text-primary-600" />
          <span className="text-lg font-bold text-gray-900">
            ServiceMatrix
          </span>
        </Link>
      </div>

      {/* ナビゲーション */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href));

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary-50 text-primary-700"
                      : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                  }`}
                >
                  <item.icon
                    className={`h-5 w-5 ${isActive ? "text-primary-600" : "text-gray-400"}`}
                  />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* フッター */}
      <div className="border-t border-gray-200 px-6 py-3">
        <p className="text-xs text-gray-400">ServiceMatrix v0.1.0</p>
        <p className="text-xs text-gray-400">ITSM Governance Platform</p>
      </div>
    </aside>
  );
}
