"use client";

import { useEffect, useState, useRef } from "react";
import { toastWarning } from "@/store/toastStore";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:28888";
const HEALTH_CHECK_INTERVAL = 15000; // 15s

export default function NetworkErrorBanner() {
  const [isOffline, setIsOffline] = useState(false);
  const hasShownToast = useRef(false);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/settings/token/status`, {
          method: "GET",
          signal: AbortSignal.timeout(5000),
        });
        if (res.ok) {
          setIsOffline(false);
          hasShownToast.current = false;
        } else {
          setIsOffline(true);
        }
      } catch {
        setIsOffline(true);
        if (!hasShownToast.current) {
          toastWarning("백엔드 서버에 연결할 수 없습니다.");
          hasShownToast.current = true;
        }
      }
    };

    // Initial check
    checkHealth();
    const intervalId = setInterval(checkHealth, HEALTH_CHECK_INTERVAL);

    return () => clearInterval(intervalId);
  }, []);

  if (!isOffline) return null;

  return (
    <div className="flex items-center gap-2 bg-red-900/60 border-b border-red-700 px-4 py-1.5 text-xs text-red-300">
      <span className="h-2 w-2 rounded-full bg-red-400 animate-pulse" />
      <span>
        백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요 (
        <code className="font-mono text-red-200">localhost:28888</code>)
      </span>
    </div>
  );
}
