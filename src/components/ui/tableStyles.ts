export const tableRowCls = (index: number) =>
  `border-b border-blue-50 dark:border-blue-900/50 last:border-b-0 transition ${
    index % 2 === 1 ? "bg-blue-50/40 dark:bg-blue-900/10" : "bg-white dark:bg-stone-800"
  } hover:bg-blue-50 dark:hover:bg-blue-900/20`;

export const thCls = "px-4 py-3 font-medium text-start";
