import type { ReactNode } from "react";

interface DataTableProps {
  icon?: ReactNode;
  title: string;
  count: number;
  countLabel: string;
  children: ReactNode;
  maxHeight?: string;
  emptyState?: ReactNode;
}

const DataTable = ({ icon, title, count, countLabel, children, maxHeight = "max-h-80", emptyState }: DataTableProps) => (
  <div className="w-full border border-blue-200 dark:border-blue-800 rounded-xl overflow-hidden shadow-sm bg-white dark:bg-stone-800">
    <div className="px-4 py-3 border-b border-blue-100 dark:border-blue-900 bg-blue-50 dark:bg-blue-950/60 flex items-center justify-between">
      <h2 className="text-sm font-semibold text-blue-800 dark:text-blue-300 flex items-center gap-2">
        {icon}
        {title}
      </h2>
      <span className="text-xs text-stone-500 dark:text-stone-400">{count} {countLabel}</span>
    </div>
    {count === 0 && emptyState ? (
      emptyState
    ) : (
      <div className={`overflow-y-auto overflow-x-auto ${maxHeight}`}>
        <table className="w-full text-sm">
          {children}
        </table>
      </div>
    )}
  </div>
);

export default DataTable;
