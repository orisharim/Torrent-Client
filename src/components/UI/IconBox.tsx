import type { ReactNode } from "react";

const IconBox = ({ icon }: { icon: ReactNode }) => (
  <div className="h-9 w-9 rounded-lg bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center">
    {icon}
  </div>
);

export default IconBox;
