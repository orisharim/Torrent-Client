import React from "react";
import { Plus, Link, Download, Upload, Activity, Share2 } from "lucide-react";
import Button from "../UI/Button";
import PageHeader from "../UI/PageHeader";
import StatCard from "../UI/StatCard";
import { useLanguage } from "../../context/LanguageContext";

export const HomePage = () => {
  const { t } = useLanguage();

  const stats = [
    { label: t("home.download"), value: "1.8 MB/s", icon: <Download className="w-5 h-5" /> },
    { label: t("home.upload"),   value: "0.3 MB/s", icon: <Upload className="w-5 h-5" />   },
    { label: t("home.active"),   value: "3",         icon: <Activity className="w-5 h-5" /> },
    { label: t("home.seeding"),  value: "2",         icon: <Share2 className="w-5 h-5" />   },
  ];

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <PageHeader
        title={t("home.title")}
        subtitle={t("home.subtitle")}
        actions={
          <>
            <Button text={t("home.addTorrent")} icon={<Plus size={16} />} action={() => {}} variant="primary" />
            <Button text={t("home.magnet")} icon={<Link size={16} />} action={() => {}} />
          </>
        }
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <StatCard key={stat.label} label={stat.label} value={stat.value} icon={stat.icon} />
        ))}
      </div>
    </div>
  );
};
