import React, { useEffect, useState } from "react";
import { Plus, RefreshCw, Download, Rss } from "lucide-react";
import Button from "../UI/Button";
import DataTable, { tableRowCls, thCls } from "../UI/DataTable";
import PageHeader from "../UI/PageHeader";
import StatCard from "../UI/StatCard";
import { useLanguage } from "../../context/LanguageContext";
import * as feedService from "../../services/feedService";
import type { FeedItem, FeedStats } from "../../services/types";

export const FeedsPage = () => {
  const { t } = useLanguage();
  const [feeds, setFeeds] = useState<FeedItem[]>([]);
  const [feedStats, setFeedStats] = useState<FeedStats | null>(null);

  useEffect(() => {
    feedService.getFeeds().then(setFeeds);
    feedService.getFeedStats().then(setFeedStats);
  }, []);

  const handleRefresh = () => {
    feedService.refreshFeeds().then(setFeeds);
  };

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <PageHeader
        title={t("feeds.title")}
        subtitle={t("feeds.subtitle")}
        actions={
          <>
            <Button text={t("feeds.addFeed")} icon={<Plus size={16} />} action={() => feedService.addFeed("")} variant="primary" />
            <Button text={t("feeds.refresh")} icon={<RefreshCw size={16} />} action={handleRefresh} />
          </>
        }
      />

      <div className="grid grid-cols-3 gap-4">
        <StatCard label={t("feeds.totalFeeds")} value={feeds.length} />
        <StatCard
          label={t("feeds.newToday")}
          value={feedStats ? feedStats.newToday : "—"}
          valueClassName="text-blue-600 dark:text-blue-400"
        />
        <StatCard
          label={t("feeds.downloadsReady")}
          value={feedStats ? feedStats.downloadsReady : "—"}
          valueClassName="text-green-600 dark:text-green-400"
        />
      </div>

      <DataTable
        icon={<Rss className="w-4 h-4" />}
        title={t("feeds.feedItems")}
        count={feeds.length}
        countLabel={t("common.items")}
      >
        <thead className="bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900">
          <tr className="text-left text-stone-500 dark:text-stone-400">
            <th className={thCls}>{t("feeds.source")}</th>
            <th className={thCls}>{t("feeds.torrent")}</th>
            <th className={thCls}>{t("table.size")}</th>
            <th className={thCls}>{t("feeds.date")}</th>
            <th className={`${thCls} text-right`}>{t("feeds.action")}</th>
          </tr>
        </thead>
        <tbody>
          {feeds.map((feed, index) => (
            <tr key={feed.id} className={tableRowCls(index)}>
              <td className="px-4 py-4 text-stone-700 dark:text-stone-200">{feed.source}</td>
              <td className="px-4 py-4">
                <div className="font-medium text-stone-800 dark:text-stone-100">{feed.name}</div>
                <div className="text-xs text-stone-400 dark:text-stone-500">ID #{feed.id}</div>
              </td>
              <td className="px-4 py-4 text-stone-600 dark:text-stone-300">{feed.size}</td>
              <td className="px-4 py-4 text-stone-600 dark:text-stone-300">{feed.date}</td>
              <td className="px-4 py-4 text-right">
                <button
                  onClick={() => feedService.downloadFeedItem(feed.id)}
                  className="inline-flex items-center gap-2 rounded-md border border-blue-200 dark:border-blue-700 px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/40 transition"
                >
                  <Download className="w-4 h-4" />
                  {t("feeds.download")}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
};
