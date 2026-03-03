/**
 * ルートレイアウト
 * アプリ全体の共通構造（Sidebar + Header + メインコンテンツ）
 */
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import AppShell from "./AppShell";
import QueryProvider from "@/providers/QueryProvider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ServiceMatrix - ITSM Governance Platform",
  description:
    "GitHubネイティブ x AI統治型 多次元ITサービス統治基盤",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className={inter.className}>
        <QueryProvider>
          <AppShell>{children}</AppShell>
        </QueryProvider>
      </body>
    </html>
  );
}
