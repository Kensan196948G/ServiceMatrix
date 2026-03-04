'use client';
import { useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

interface Notification {
  id: string;
  type: string;
  message: string;
  timestamp: string;
}

export function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  const { isConnected } = useWebSocket({
    url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1/ws/notifications',
    onMessage: (msg) => {
      if (msg.type === 'notification') {
        setNotifications(prev => [{
          id: Date.now().toString(),
          type: msg.type,
          message: JSON.stringify(msg.data),
          timestamp: new Date().toISOString(),
        }, ...prev].slice(0, 50));
      }
    },
  });

  const unreadCount = notifications.length;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 hover:text-gray-900"
        aria-label="通知"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
        {isConnected && (
          <span className="absolute bottom-0 right-0 w-2 h-2 bg-green-500 rounded-full" />
        )}
      </button>
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white border rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
          <div className="p-3 border-b font-semibold text-sm">通知 ({unreadCount})</div>
          {notifications.length === 0 ? (
            <p className="p-4 text-gray-500 text-sm text-center">通知はありません</p>
          ) : (
            notifications.map(n => (
              <div key={n.id} className="p-3 border-b hover:bg-gray-50 text-sm">
                <p>{n.message}</p>
                <p className="text-gray-400 text-xs mt-1">{new Date(n.timestamp).toLocaleString('ja-JP')}</p>
              </div>
            ))
          )}
          <button
            onClick={() => setNotifications([])}
            className="w-full p-2 text-center text-sm text-gray-500 hover:bg-gray-50"
          >
            すべてクリア
          </button>
        </div>
      )}
    </div>
  );
}
