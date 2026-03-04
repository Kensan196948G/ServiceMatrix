"use client";

import { useState } from "react";
import { Bell, X, AlertTriangle, Clock, CheckCircle, GitPullRequest, Info } from "lucide-react";

interface Notification {
  id: string;
  type: "incident" | "sla" | "change" | "info";
  title: string;
  body: string;
  time: string;
  read: boolean;
}

const SAMPLE_NOTIFICATIONS: Notification[] = [
  {
    id: "n1",
    type: "incident",
    title: "P1インシデント発生",
    body: "本番DBサーバー（db-prod-01）で応答不能が検出されました",
    time: "2分前",
    read: false,
  },
  {
    id: "n2",
    type: "sla",
    title: "SLA違反アラート",
    body: "INC-1042 の解決期限まであと15分です",
    time: "8分前",
    read: false,
  },
  {
    id: "n3",
    type: "change",
    title: "変更承認待ち",
    body: "CHG-0251「Nginx設定変更」が CAB承認待ちです",
    time: "32分前",
    read: false,
  },
  {
    id: "n4",
    type: "incident",
    title: "P2インシデント更新",
    body: "INC-1039 のステータスが「調査中」に更新されました",
    time: "1時間前",
    read: true,
  },
  {
    id: "n5",
    type: "sla",
    title: "SLA違反",
    body: "INC-1035 が解決SLAを超過しました（4時間超過）",
    time: "2時間前",
    read: true,
  },
  {
    id: "n6",
    type: "change",
    title: "変更承認完了",
    body: "CHG-0248「APIサーバー増設」が承認されました",
    time: "3時間前",
    read: true,
  },
  {
    id: "n7",
    type: "info",
    title: "定期メンテナンス予告",
    body: "本日 02:00〜04:00 に DB メンテナンスが予定されています",
    time: "5時間前",
    read: true,
  },
];

const TYPE_ICON: Record<Notification["type"], React.ReactNode> = {
  incident: <AlertTriangle className="w-4 h-4 text-red-500" />,
  sla: <Clock className="w-4 h-4 text-orange-500" />,
  change: <GitPullRequest className="w-4 h-4 text-blue-500" />,
  info: <Info className="w-4 h-4 text-gray-400" />,
};

const TYPE_BG: Record<Notification["type"], string> = {
  incident: "bg-red-50",
  sla: "bg-orange-50",
  change: "bg-blue-50",
  info: "bg-gray-50",
};

export default function NotificationPanel() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>(SAMPLE_NOTIFICATIONS);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const dismiss = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const markRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
      >
        <Bell style={{ width: "18px", height: "18px" }} />
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white ring-2 ring-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full z-20 mt-1 w-96 rounded-xl border border-gray-200 bg-white shadow-xl overflow-hidden">
            {/* ヘッダー */}
            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-gray-600" />
                <span className="font-semibold text-gray-900 text-sm">通知</span>
                {unreadCount > 0 && (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                    {unreadCount}件 未読
                  </span>
                )}
              </div>
              {unreadCount > 0 && (
                <button
                  onClick={markAllRead}
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <CheckCircle className="w-3.5 h-3.5" /> すべて既読
                </button>
              )}
            </div>

            {/* 通知一覧 */}
            <div className="max-h-[440px] overflow-y-auto divide-y divide-gray-50">
              {notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-gray-400">
                  <Bell className="w-8 h-8 mb-2 text-gray-200" />
                  <p className="text-sm">通知はありません</p>
                </div>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    onClick={() => markRead(n.id)}
                    className={`flex gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors ${!n.read ? "bg-blue-50/40" : ""}`}
                  >
                    <div className={`mt-0.5 flex-shrink-0 p-1.5 rounded-full ${TYPE_BG[n.type]}`}>
                      {TYPE_ICON[n.type]}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className={`text-sm font-medium ${n.read ? "text-gray-700" : "text-gray-900"}`}>
                          {n.title}
                          {!n.read && <span className="ml-1.5 inline-block w-1.5 h-1.5 rounded-full bg-blue-500 align-middle" />}
                        </p>
                        <button
                          onClick={(e) => { e.stopPropagation(); dismiss(n.id); }}
                          className="flex-shrink-0 p-0.5 rounded text-gray-300 hover:text-gray-500"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.body}</p>
                      <p className="text-[11px] text-gray-400 mt-1">{n.time}</p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* フッター */}
            {notifications.length > 0 && (
              <div className="border-t border-gray-100 px-4 py-2.5 text-center">
                <button
                  onClick={() => setNotifications([])}
                  className="text-xs text-gray-400 hover:text-gray-600"
                >
                  すべてクリア
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
