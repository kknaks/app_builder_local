"use client";

import { useState } from "react";
import { saveToken } from "@/lib/api";
import Spinner from "./Spinner";
import { toastSuccess, toastError } from "@/store/toastStore";

interface TokenModalProps {
  open: boolean;
  onClose: () => void;
}

export default function TokenModal({ open, onClose }: TokenModalProps) {
  const [token, setToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const handleSave = async () => {
    if (!token.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await saveToken(token.trim());
      toastSuccess("API 토큰이 저장되었습니다.");
      onClose();
    } catch (e) {
      const errMsg = (e as Error).message;
      setError(errMsg);
      toastError(`토큰 저장 실패: ${errMsg}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-xl bg-gray-800 p-6 shadow-2xl">
        <h2 className="text-xl font-bold text-white mb-2">API 토큰 설정</h2>
        <p className="text-gray-400 text-sm mb-4">
          Claude API 토큰을 입력하세요. 안전하게 암호화되어 저장됩니다.
        </p>
        <input
          type="password"
          placeholder="sk-ant-..."
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="w-full rounded-lg border border-gray-600 bg-gray-700 px-4 py-2.5 text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none"
          onKeyDown={(e) => e.key === "Enter" && handleSave()}
        />
        {error && (
          <p className="mt-2 text-sm text-red-400">{error}</p>
        )}
        <div className="mt-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-gray-300 hover:text-white transition"
          >
            나중에
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !token.trim()}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition"
          >
            {saving && <Spinner size="sm" />}
            {saving ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}
