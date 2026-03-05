"use client";

import { useState, useCallback } from "react";
import { useProjectStore } from "@/store/projectStore";
import { approvePlan, submitFeedback } from "@/lib/api";
import Spinner from "./Spinner";
import { toastSuccess, toastInfo, toastError } from "@/store/toastStore";

interface ApprovalBarProps {
  /** Called after successful approval */
  onApprove?: () => void;
  /** Called after successful feedback submission */
  onFeedback?: () => void;
}

export default function ApprovalBar({ onApprove, onFeedback }: ApprovalBarProps) {
  const selectedId = useProjectStore((s) => s.selectedId);
  const [showFeedbackInput, setShowFeedbackInput] = useState(false);
  const [feedbackText, setFeedbackText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApprove = useCallback(async () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    try {
      await approvePlan(selectedId);
      toastSuccess("기획이 승인되었습니다!");
      onApprove?.();
    } catch (e) {
      const errMsg = (e as Error).message;
      setError(errMsg);
      toastError(`승인 실패: ${errMsg}`);
    } finally {
      setLoading(false);
    }
  }, [selectedId, onApprove]);

  const handleSubmitFeedback = useCallback(async () => {
    if (!selectedId || !feedbackText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await submitFeedback(selectedId, feedbackText.trim());
      toastInfo("피드백이 전달되었습니다.");
      setFeedbackText("");
      setShowFeedbackInput(false);
      onFeedback?.();
    } catch (e) {
      const errMsg = (e as Error).message;
      setError(errMsg);
      toastError(`피드백 전송 실패: ${errMsg}`);
    } finally {
      setLoading(false);
    }
  }, [selectedId, feedbackText, onFeedback]);

  return (
    <div className="border-b border-yellow-700/40 bg-yellow-900/20 px-4 py-2.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm">📋</span>
          <span className="text-sm font-medium text-yellow-200">
            기획 검토가 완료되었습니다. 승인하시겠습니까?
          </span>
        </div>
        {!showFeedbackInput && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFeedbackInput(true)}
              disabled={loading}
              className="flex items-center gap-1 rounded-md border border-gray-600 bg-gray-700 px-3 py-1.5 text-xs font-medium text-gray-200 hover:bg-gray-600 disabled:opacity-50 transition"
            >
              💬 피드백
            </button>
            <button
              onClick={handleApprove}
              disabled={loading}
              className="flex items-center gap-1 rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-500 disabled:opacity-50 transition"
            >
              {loading ? <><Spinner size="sm" /> 처리중...</> : "✅ 승인"}
            </button>
          </div>
        )}
      </div>

      {/* Feedback input */}
      {showFeedbackInput && (
        <div className="mt-2 flex gap-2">
          <input
            type="text"
            placeholder="피드백을 입력하세요..."
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmitFeedback();
              }
              if (e.key === "Escape") {
                setShowFeedbackInput(false);
                setFeedbackText("");
              }
            }}
            disabled={loading}
            className="flex-1 rounded-md border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
            autoFocus
          />
          <button
            onClick={handleSubmitFeedback}
            disabled={loading || !feedbackText.trim()}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition"
          >
            {loading ? "전송중..." : "전송"}
          </button>
          <button
            onClick={() => {
              setShowFeedbackInput(false);
              setFeedbackText("");
            }}
            disabled={loading}
            className="rounded-md px-2 py-1.5 text-xs text-gray-400 hover:text-white transition"
          >
            취소
          </button>
        </div>
      )}

      {error && (
        <p className="mt-1 text-xs text-red-400">{error}</p>
      )}
    </div>
  );
}
