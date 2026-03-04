/**
 * ヘッダーコンポーネント
 * ユーザー情報表示・ログアウトボタンを提供
 */
"use client";

import UserMenu from "@/components/UserMenu";

export default function Header() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      {/* ページタイトル領域 */}
      <div />

      {/* ユーザーメニュー */}
      <UserMenu />
    </header>
  );
}
