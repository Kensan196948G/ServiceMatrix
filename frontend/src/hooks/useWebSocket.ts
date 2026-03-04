/**
 * WebSocket リアルタイム通知フック
 * JWT token をローカルストレージから取得して ws 接続・自動再接続を管理する
 */
"use client";

import { useEffect, useCallback, useRef, useState } from "react";

interface UseWebSocketOptions {
  channel: "incidents" | "changes" | "sla_alerts" | "all";
  onMessage?: (data: Record<string, unknown>) => void;
  autoReconnect?: boolean;
}

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8000/api/v1`
    : "ws://localhost:8000/api/v1");

const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useWebSocket({
  channel,
  onMessage,
  autoReconnect = true,
}: UseWebSocketOptions) {
  const [status, setStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("access_token");
    if (!token) return;

    setStatus("connecting");
    const url = `${WS_BASE_URL}/ws/${channel}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      attemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>;
        if (data.type === "ping") {
          ws.send("ping");
          return;
        }
        onMessageRef.current?.(data);
      } catch {
        // non-JSON frames ignored
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      if (autoReconnect && attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        attemptsRef.current += 1;
        timerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [channel, autoReconnect]);

  useEffect(() => {
    connect();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { status };
}
