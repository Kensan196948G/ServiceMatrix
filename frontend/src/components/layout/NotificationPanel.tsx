"use client";

import { useState, useEffect } from "react";
import { Bell, X, AlertTriangle, Clock, CheckCircle, GitPullRequest, Info } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";

interface Notification {
  id: string;
  type: "incident" | "sla" | "change" | "info";
  title: string;
  body: string;
  time: string;
  read: boolean;
  timestamp: number;
}

const STORAGE_KEY = "servicematrix_notifications";
const MAX_STORED = 50;

const SAMPLE_NOTIFICATIONS: Notification[] = [
  {
    id: "n1",
    type: "incident",
    title: "P1インシデント発生",
    body: "本番DBサーバー（db-prod-01）で応答不能が検出されました",
    time: "2分前",
    read: false,
    timestamp: Date.now() - 2 * 60 * 1000,
  },
  {
    id: "n2",
    type: "sla",
    title: "SLA違反アラート",
    body: "INC-1042 の解決期限まであと15分です",
    time: "8分前",
    read: false,
    timestamp: Date.now() - 8 * 60 * 1000,
  },
  {
    id: "n3",
    type: "change",
    title: "変更承認待ち",
    body: "CHG-0251「Nginx設定変更」が CAB承認待ちです",
    time: "32分前",
    read: true,
    timestamp: Date.now() - 32 * 60 * 1000,
  },
];

function formatTime(timestamp: number): string {
  const diff = Date.now() - timestamp;
  if (diff < 60_000) return "今";
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)}分前`;
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)}時間前`;
  return new Date(timestamp).toLocaleDateString("ja-JP", { month: "short", day: "numeric" });
}

function loadFromStorage(): Notification[] {
  if (typeof window === "undefined") return SAMPLE_NOTIFICATIONS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return SAMPLE_NOTIFICATIONS;
    const stored: Notification[] = JSON.parse(raw);
    // サンプルと重複しないようにマージ
    const ids = new Set(stored.map((n) => n.id));
    const merged = [...stored];
    for (const s of SAMPLE_NOTIFICATIONS) {
      if (!ids.has(s.id)) merged.push(s);
    }
    return merged.sort((a, b) => b.timestamp - a.timestamp).slice(0, MAX_STORED);
  } catch {
    return SAMPLE_NOTIFICATIONS;
  }
}

function saveToStorage(notifications: Notification[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(notifications.slice(0, MAX_STORED))
    );
  } catch {}
}

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
  const [notifications, setNotifications] = useState<Notification[]>([]);

  // マウント時にLocalStorageから読み込み
  useEffect(() => {
    setNotifications(loadFromStorage());
  }, []);

  // 通知変更時にLocalStorageへ保存
  useEffect(() => {
    if (notifications.length > 0) {
      saveToStorage(notifications);
    }
  }, [notifications]);

  // WebSocket でリアルタイム通知を受信
  const { isConnected } = useWebSocket({
    channel: "all",
    onMessage: (data) => {
      const type = data.type as string;
      let notifType: Notification["type"] = "info";
      if (type?.includes("incident")) notifType = "incident";
      else if (type?.includes("sla")) notifType = "sla";
      else if (type?.includes("change")) notifType = "change";

      const payload = (data.payload ?? data) as Record<string, unknown>;
      const newNotif: Notification = {
        id: `ws-${Date.now()}`,
        type: notifType,
        title: (payload.title as string) ?? type ?? "新しい通知",
        body: (payload.description as string) ?? (payload.message as string) ?? JSON.stringify(payload).slice(0, 80),
        time: "今",
        read: false,
        timestamp: Date.now(),
      };
      setNotifications((prev) => [newNotif, ...prev].slice(0, MAX_STORED));
    },
    autoReconnect: true,
  });

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

  const clearAll = () => {
    setNotifications([]);
    if (typeof window !== "undefined") {
      localStorage.removeItem(STORAGE_KEY);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
        title={isConnected ? "リアルタイム接続中" : "オフライン"}
      >
        <Bell style={{ width: "18px", height: "18px" }} />
        {/* 接続状態インジケーター */}
        <span className={`absolute right-0.5 bottom-0.5 w-2 h-2 rounded-full border border-white ${isConnected ? "bg-green-400" : "bg-gray-300"}`} />
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
                      <p className="text-[11px] text-gray-400 mt-1">
                        {n.timestamp ? formatTime(n.timestamp) : n.time}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* フッター */}
            {notifications.length > 0 && (
              <div className="border-t border-gray-100 px-4 py-2.5 text-center">
                <button
                  onClick={clearAll}
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
