/**
 * WebSocket リアルタイム通知フック
 * JWT token をローカルストレージから取得して ws 接続・自動再接続を管理する
 */
"use client";

import { useEffect, useCallback, useRef, useState } from "react";

export interface WsMessage {
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

interface UseWebSocketOptions {
  channel?: "incidents" | "changes" | "sla_alerts" | "all" | "connect";
  onMessage?: (data: Record<string, unknown>) => void;
  autoReconnect?: boolean;
}

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8001/api/v1`
    : "ws://localhost:8001/api/v1");

const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { channel = "connect", onMessage, autoReconnect = true } = options;

  const [status, setStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("disconnected");
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<WsMessage[]>([]);
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null);

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
      setIsConnected(true);
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
        const msg: WsMessage = {
          type: (data.type as string) ?? "unknown",
          payload: (data.payload as Record<string, unknown>) ?? data,
          timestamp: (data.timestamp as string) ?? new Date().toISOString(),
        };
        setLastMessage(msg);
        setMessages((prev) => [...prev.slice(-99), msg]);
      } catch {
        // non-JSON frames ignored
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      setIsConnected(false);
      if (autoReconnect && attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        attemptsRef.current += 1;
        timerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [channel, autoReconnect]);

  const disconnect = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    attemptsRef.current = MAX_RECONNECT_ATTEMPTS; // prevent auto-reconnect
    wsRef.current?.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { status, isConnected, messages, lastMessage, connect, disconnect };
}
