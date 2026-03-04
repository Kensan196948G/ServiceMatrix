/**
 * WebSocket リアルタイム通知トースト
 * インシデント更新・SLAアラートを受信してトースト表示する
 */
"use client";

import { useEffect, useState, useCallback } from "react";
import { AlertTriangle, Bell, X } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";

interface Toast {
  id: number;
  message: string;
  type: "info" | "alert";
}

let _nextId = 0;

export function NotificationToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message: string, type: Toast["type"]) => {
      const id = ++_nextId;
      setToasts((prev) => [...prev.slice(-4), { id, message, type }]);
      setTimeout(() => dismiss(id), 5000);
    },
    [dismiss]
  );

  const handleMessage = useCallback(
    (data: Record<string, unknown>) => {
      if (data.type === "incident_update") {
        const action = data.action as string;
        const num =
          (data.data as Record<string, unknown>)?.incident_number ?? data.incident_id;
        const label =
          action === "created"
            ? "作成"
            : action === "closed"
            ? "クローズ"
            : "更新";
        addToast(`インシデント ${num} が${label}されました`, "info");
      } else if (data.type === "sla_alert") {
        const level = data.warning_level as string;
        addToast(
          `SLAアラート: インシデント ${data.incident_id} — ${level}`,
          "alert"
        );
      }
    },
    [addToast]
  );

  useWebSocket({ channel: "all", onMessage: handleMessage });

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-start gap-3 rounded-lg px-4 py-3 shadow-lg text-sm text-white max-w-sm ${
            toast.type === "alert" ? "bg-red-600" : "bg-gray-800"
          }`}
        >
          {toast.type === "alert" ? (
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          ) : (
            <Bell className="h-4 w-4 mt-0.5 shrink-0" />
          )}
          <span className="flex-1">{toast.message}</span>
          <button onClick={() => dismiss(toast.id)}>
            <X className="h-4 w-4 opacity-70 hover:opacity-100" />
          </button>
        </div>
      ))}
    </div>
  );
}
