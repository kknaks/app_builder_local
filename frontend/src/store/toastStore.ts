import { create } from "zustand";

export type ToastType = "success" | "error" | "info" | "warning";

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  /** Auto-dismiss timeout in ms (default: 4000, 0 = manual dismiss) */
  duration?: number;
}

interface ToastState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => string;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],

  addToast: (toast) => {
    const id = crypto.randomUUID();
    const newToast: Toast = { ...toast, id };
    set({ toasts: [...get().toasts, newToast] });

    // Auto-dismiss
    const duration = toast.duration ?? 4000;
    if (duration > 0) {
      setTimeout(() => {
        set({ toasts: get().toasts.filter((t) => t.id !== id) });
      }, duration);
    }

    return id;
  },

  removeToast: (id) => {
    set({ toasts: get().toasts.filter((t) => t.id !== id) });
  },

  clearAll: () => set({ toasts: [] }),
}));

// Convenience helpers
export function toast(message: string, type: ToastType = "info", duration?: number) {
  return useToastStore.getState().addToast({ message, type, duration });
}

export function toastSuccess(message: string) {
  return toast(message, "success");
}

export function toastError(message: string) {
  return toast(message, "error", 6000);
}

export function toastInfo(message: string) {
  return toast(message, "info");
}

export function toastWarning(message: string) {
  return toast(message, "warning", 5000);
}
