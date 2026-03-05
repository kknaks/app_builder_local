"use client";

import { useEffect, useState } from "react";
import { getTokenStatus } from "@/lib/api";
import Spinner from "./Spinner";

interface TokenModalProps {
  open: boolean;
  onClose: () => void;
}

export default function TokenModal({ open, onClose }: TokenModalProps) {
  const [checking, setChecking] = useState(true);
  const [status, setStatus] = useState<{
    configured: boolean;
    valid: boolean | null;
    message?: string;
  } | null>(null);

  useEffect(() => {
    if (!open) return;
    setChecking(true);
    getTokenStatus()
      .then((s) => setStatus(s))
      .catch(() => setStatus({ configured: false, valid: false, message: "Backend unreachable" }))
      .finally(() => setChecking(false));
  }, [open]);

  if (!open) return null;

  const isOk = status?.configured && status?.valid;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-xl bg-gray-800 p-6 shadow-2xl">
        <h2 className="text-xl font-bold text-white mb-2">Claude CLI 상태</h2>

        {checking ? (
          <div className="flex items-center gap-3 py-4 text-gray-400">
            <Spinner size="sm" />
            <span>Claude CLI 인증 상태 확인 중...</span>
          </div>
        ) : isOk ? (
          <div className="rounded-lg bg-green-900/30 border border-green-700 p-4 my-3">
            <p className="text-green-400 font-medium">Claude CLI 인증됨</p>
            <p className="text-green-300/70 text-sm mt-1">{status?.message}</p>
          </div>
        ) : (
          <div className="rounded-lg bg-red-900/30 border border-red-700 p-4 my-3">
            <p className="text-red-400 font-medium">Claude CLI 미인증</p>
            <p className="text-red-300/70 text-sm mt-1">{status?.message}</p>
            <p className="text-gray-400 text-sm mt-3">
              터미널에서 <code className="bg-gray-700 px-1.5 py-0.5 rounded text-white">claude login</code> 을 실행하세요.
            </p>
          </div>
        )}

        <div className="mt-4 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg bg-gray-700 px-4 py-2 text-sm text-white hover:bg-gray-600 transition"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
