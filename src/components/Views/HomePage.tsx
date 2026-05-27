import React from "react";
import {
  Plus,
  Link,
  Download,
  Upload,
  Activity,
  Share2,
  FileDown,
} from "lucide-react";
import Button from "../UI/Button";
import { useLanguage } from "../../context/LanguageContext";

const recentTorrents = [
  { id: 1, name: "ubuntu.iso", size: "2.5 GB", status: "Completed" },
  { id: 2, name: "movie.mp4", size: "1.2 GB", status: "Paused" },
  { id: 3, name: "linux_tools.tar.gz", size: "4.7 GB", status: "Downloading" },
];

export const HomePage = () => {
  const { t } = useLanguage();

  const stats = [
    { label: t("home.download"), value: "1.8 MB/s", icon: <Download className="w-5 h-5" /> },
    { label: t("home.upload"), value: "0.3 MB/s", icon: <Upload className="w-5 h-5" /> },
    { label: t("home.active"), value: "3", icon: <Activity className="w-5 h-5" /> },
    { label: t("home.seeding"), value: "2", icon: <Share2 className="w-5 h-5" /> },
  ];

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-stone-800 dark:text-stone-100">{t("home.title")}</h1>
          <p className="text-sm text-stone-500 dark:text-stone-400 mt-1">
            {t("home.subtitle")}
          </p>
        </div>

        <div className="flex gap-2">
          <Button text={t("home.addTorrent")} icon={<Plus size={16} />} action={() => {}} variant="primary" />
          <Button text={t("home.magnet")} icon={<Link size={16} />} action={() => {}} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="bg-white dark:bg-stone-800 border border-blue-200 dark:border-blue-800 rounded-lg p-4 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm text-stone-500 dark:text-stone-400">{stat.label}</p>
              <div className="h-9 w-9 rounded-lg bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                {stat.icon}
              </div>
            </div>
            <p className="text-xl font-bold text-stone-800 dark:text-stone-100 mt-2">
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      

        
      
    </div>
  );
};
