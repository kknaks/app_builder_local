"use client";

import { useEffect, useState } from "react";
import { useToastStore, type Toast, type ToastType } from "@/store/toastStore";

const TYPE_CONFIG: Record<
  ToastType,
  { icon: string; bg: string; border: string; text: string }
> = {
  success: {
    icon: "✅",
    bg: "bg-green-900/90",
    border: "border-green-600/50",
    text: "text-green-200",
  },
  error: {
    icon: "❌",
    bg: "bg-red-900/90",
    border: "border-red-600/50",
    text: "text-red-200",
  },
  info: {
    icon: "ℹ️",
    bg: "bg-blue-900/90",
    border: "border-blue-600/50",
    text: "text-blue-200",
  },
  warning: {
    icon: "⚠️",
    bg: "bg-yellow-900/90",
    border: "border-yellow-600/50",
    text: "text-yellow-200",
  },
};

function ToastItem({ toast: t }: { toast: Toast }) {
  const removeToast = useToastStore((s) => s.removeToast);
  const config = TYPE_CONFIG[t.type];
  const [exiting, setExiting] = useState(false);

  const handleDismiss = () => {
    setExiting(true);
    setTimeout(() => removeToast(t.id), 200);
  };

  // Auto-exit animation before removal
  useEffect(() => {
    const duration = t.duration ?? 4000;
    if (duration > 0 && duration > 300) {
      const timer = setTimeout(() => setExiting(true), duration - 300);
      return () => clearTimeout(timer);
    }
  }, [t.duration]);

  return (
    <div
      className={`flex items-center gap-3 rounded-lg border ${config.border} ${config.bg} px-4 py-3 shadow-xl backdrop-blur-sm transition-all duration-200 ${
        exiting
          ? "translate-x-full opacity-0"
          : "translate-x-0 opacity-100 animate-toast-in"
      }`}
    >
      <span className="text-sm flex-shrink-0">{config.icon}</span>
      <p className={`text-sm font-medium ${config.text} flex-1`}>
        {t.message}
      </p>
      <button
        onClick={handleDismiss}
        className="flex-shrink-0 rounded p-0.5 text-gray-400 hover:text-white transition"
      >
        <svg
          className="h-3.5 w-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  );
}

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} />
      ))}
    </div>
  );
}
