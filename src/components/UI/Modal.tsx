import { useEffect } from "react";
import type { ReactNode } from "react";

type ModalProps = {
  onClose: () => void;
  children: ReactNode;
  widthCls?: string;
  panelCls?: string;
};

const Modal = ({ onClose, children, widthCls = "max-w-md", panelCls = "bg-white dark:bg-stone-800" }: ModalProps) => {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className={`rounded-2xl shadow-2xl w-full mx-4 ${widthCls} ${panelCls}`}>
        {children}
      </div>
    </div>
  );
};

export default Modal;
