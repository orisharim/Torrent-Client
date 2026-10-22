import type { ReactNode } from "react";

type EmptyStateProps = {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
};

const EmptyState = ({ icon, title, description, action }: EmptyStateProps) => (
  <div className="flex flex-col items-center justify-center gap-2 py-10 px-4 text-center">
    {icon && <div className="text-stone-300 dark:text-stone-600 mb-1">{icon}</div>}
    <p className="text-sm font-medium text-stone-600 dark:text-stone-300">{title}</p>
    {description && <p className="text-xs text-stone-400 dark:text-stone-500">{description}</p>}
    {action && <div className="mt-3">{action}</div>}
  </div>
);

export default EmptyState;
