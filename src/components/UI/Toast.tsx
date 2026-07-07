import { AlertCircle, CheckCircle2 } from "lucide-react";
import { useUI } from "../../context/UIContext";

export const ToastViewport = () => {
  const { toasts } = useUI();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 end-4 z-[60] flex flex-col gap-2 items-end">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`flex items-center gap-2 px-4 py-2.5 rounded-full shadow-lg text-sm font-medium animate-[toast-in_0.2s_ease-out]
            ${toast.variant === "error"
              ? "bg-red-600 text-white"
              : "bg-stone-800 dark:bg-stone-100 text-white dark:text-stone-900"
            }`}
        >
          {toast.variant === "error" ? <AlertCircle size={16} /> : <CheckCircle2 size={16} className="text-green-400 dark:text-green-600" />}
          {toast.message}
        </div>
      ))}
    </div>
  );
};
