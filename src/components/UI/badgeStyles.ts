import type { TorrentStatus } from "../../services/types";

export const statusStyles: Record<TorrentStatus, string> = {
  Downloading: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  Paused:      "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  Completed:   "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  Seeding:     "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300",
};
