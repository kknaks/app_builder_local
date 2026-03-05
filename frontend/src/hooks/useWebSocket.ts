import { useEffect, useRef, useCallback, useState } from "react";

export type WSStatus = "connecting" | "connected" | "reconnecting" | "disconnected";

interface UseWebSocketOptions {
  /** WebSocket URL */
  url: string | null;
  /** Called when a message is received */
  onMessage?: (data: unknown) => void;
  /** Called when connection is established */
  onOpen?: () => void;
  /** Called when connection is closed */
  onClose?: () => void;
  /** Called when an error occurs */
  onError?: (error: Event) => void;
  /** Max reconnect attempts (default: 3) */
  maxReconnectAttempts?: number;
  /** Whether to auto-connect (default: true) */
  enabled?: boolean;
}

interface UseWebSocketReturn {
  /** Send a JSON message */
  sendMessage: (data: unknown) => void;
  /** Current connection status */
  status: WSStatus;
  /** Manually reconnect */
  reconnect: () => void;
  /** Manually disconnect */
  disconnect: () => void;
}

export function useWebSocket({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  maxReconnectAttempts = 3,
  enabled = true,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<WSStatus>("disconnected");

  // Keep callbacks in refs to avoid reconnection on callback changes
  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);

  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);
  useEffect(() => { onOpenRef.current = onOpen; }, [onOpen]);
  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!url) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setStatus(reconnectAttemptsRef.current > 0 ? "reconnecting" : "connecting");

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptsRef.current = 0;
        setStatus("connected");
        onOpenRef.current?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current?.(data);
        } catch {
          // If not JSON, pass raw data
          onMessageRef.current?.(event.data);
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        onCloseRef.current?.();

        // Auto-reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000; // 1s, 2s, 4s
          setStatus("reconnecting");
          reconnectAttemptsRef.current += 1;
          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setStatus("disconnected");
        }
      };

      ws.onerror = (error) => {
        onErrorRef.current?.(error);
      };
    } catch {
      setStatus("disconnected");
    }
  }, [url, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    clearReconnectTimer();
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent auto-reconnect
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus("disconnected");
  }, [clearReconnectTimer, maxReconnectAttempts]);

  const reconnect = useCallback(() => {
    clearReconnectTimer();
    reconnectAttemptsRef.current = 0;
    connect();
  }, [clearReconnectTimer, connect]);

  const sendMessage = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // Connect/disconnect on url or enabled change
  useEffect(() => {
    if (enabled && url) {
      reconnectAttemptsRef.current = 0;
      connect();
    } else {
      disconnect();
    }

    return () => {
      clearReconnectTimer();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [url, enabled, connect, disconnect, clearReconnectTimer]);

  return { sendMessage, status, reconnect, disconnect };
}
