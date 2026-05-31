import type { ReactNode } from "react";
import IconBox from "./IconBox";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  valueClassName?: string;
}

const StatCard = ({ label, value, icon, valueClassName = "text-stone-800 dark:text-stone-100" }: StatCardProps) => (
  <div className="bg-white dark:bg-stone-800 border border-blue-200 dark:border-blue-800 rounded-lg p-4 shadow-sm">
    <div className="flex items-center justify-between">
      <p className="text-sm text-stone-500 dark:text-stone-400">{label}</p>
      {icon && <IconBox icon={icon} />}
    </div>
    <p className={`text-xl font-bold mt-2 ${valueClassName}`}>{value}</p>
  </div>
);

export default StatCard;
