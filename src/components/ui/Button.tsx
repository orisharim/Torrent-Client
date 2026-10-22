import type { ReactNode } from "react";

type ButtonVariant = "default" | "primary" | "danger";

interface ButtonProps {
  text: string;
  icon?: ReactNode;
  action: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
}

const variantStyles: Record<ButtonVariant, string> = {
  default:
    "text-stone-800 dark:text-stone-200 hover:bg-blue-200 dark:hover:bg-blue-900",
  primary: "bg-blue-600 text-white hover:bg-blue-700 rounded font-bold",
  danger:
    "text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30",
};

const Button = ({ text, icon, action, variant = "default", disabled = false }: ButtonProps) => {
  return (
    <button
      onClick={action}
      disabled={disabled}
      className={`flex items-center gap-2 px-3 py-2 text-sm transition
        ${variantStyles[variant]}
        ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
      `}
    >
      {icon}
      <span>{text}</span>
    </button>
  );
};

export default Button;
