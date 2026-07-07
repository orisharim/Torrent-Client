import { useEffect, useState } from "react";
import { Plus, RefreshCw, Download, Rss, Check } from "lucide-react";
import Button from "../UI/Button";
import DataTable from "../UI/DataTable";
import { tableRowCls, thCls } from "../UI/tableStyles";
import EmptyState from "../UI/EmptyState";
import PageHeader from "../UI/PageHeader";
import StatCard from "../UI/StatCard";
import { useLanguage } from "../../context/LanguageContext";
import { useUI } from "../../context/UIContext";
import * as feedService from "../../services/feedService";
import type { FeedItem, FeedStats } from "../../services/types";

export const FeedsPage = () => {
  const { t } = useLanguage();
  const { showToast } = useUI();
  const [feeds, setFeeds] = useState<FeedItem[]>([]);
  const [feedStats, setFeedStats] = useState<FeedStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [url, setUrl] = useState("");
  const [downloadedIds, setDownloadedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    feedService.getFeeds().then((items) => {
      setFeeds(items);
      setLoading(false);
    });
    feedService.getFeedStats().then(setFeedStats);
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    const items = await feedService.refreshFeeds();
    setFeeds(items);
    setRefreshing(false);
  };

  const urlValid = /^https?:\/\/.+/.test(url.trim());

  const handleAddFeed = () => {
    if (!urlValid) return;
    const trimmed = url.trim();
    feedService.addFeed(trimmed);
    // REPLACE: backend should return the parsed feed instead of this optimistic entry
    setFeeds((prev) => [
      { id: Date.now(), source: new URL(trimmed).hostname, name: trimmed, size: "—", date: "Now" },
      ...prev,
    ]);
    showToast(t("feeds.added"));
    setUrl("");
    setShowAdd(false);
  };

  const handleDownload = (id: number) => {
    feedService.downloadFeedItem(id);
    setDownloadedIds((prev) => new Set(prev).add(id));
    showToast(t("feeds.downloadStarted"));
  };

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <PageHeader
        title={t("feeds.title")}
        subtitle={t("feeds.subtitle")}
        actions={
          <>
            <Button text={t("feeds.addFeed")} icon={<Plus size={16} />} action={() => setShowAdd((prev) => !prev)} variant="primary" />
            <Button
              text={t("feeds.refresh")}
              icon={<RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />}
              action={handleRefresh}
              disabled={refreshing}
            />
          </>
        }
      />

      {showAdd && (
        <div className="flex flex-wrap items-center gap-2 p-4 bg-white dark:bg-stone-800 border border-blue-200 dark:border-blue-800 rounded-xl">
          <input
            autoFocus
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleAddFeed(); }}
            placeholder={t("feeds.urlPlaceholder")}
            className="flex-1 min-w-48 text-sm border border-blue-200 dark:border-blue-700 rounded-lg px-3 py-2 bg-white dark:bg-stone-700 text-stone-800 dark:text-stone-100 placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Button text={t("feeds.addFeed")} action={handleAddFeed} variant="primary" disabled={!urlValid} />
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
        emptyState={
          <EmptyState
            icon={<Rss size={28} />}
            title={loading ? t("empty.loading") : t("empty.noFeeds")}
          />
        }
      >
        <thead className="bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900">
          <tr className="text-start text-stone-500 dark:text-stone-400">
            <th className={thCls}>{t("feeds.source")}</th>
            <th className={thCls}>{t("feeds.torrent")}</th>
            <th className={`${thCls} whitespace-nowrap`}>{t("table.size")}</th>
            <th className={`${thCls} hidden md:table-cell`}>{t("feeds.date")}</th>
            <th className={thCls}>{t("feeds.action")}</th>
          </tr>
        </thead>
        <tbody>
          {feeds.map((feed, index) => {
            const downloaded = downloadedIds.has(feed.id);
            return (
              <tr key={feed.id} className={tableRowCls(index)}>
                <td className="px-4 py-4 text-stone-700 dark:text-stone-200">{feed.source}</td>
                <td className="px-4 py-4">
                  <div className="font-medium text-stone-800 dark:text-stone-100 max-w-72 truncate" title={feed.name}>{feed.name}</div>
                  <div className="text-xs text-stone-400 dark:text-stone-500">ID #{feed.id}</div>
                </td>
                <td className="px-4 py-4 text-stone-600 dark:text-stone-300 whitespace-nowrap">{feed.size}</td>
                <td className="px-4 py-4 text-stone-600 dark:text-stone-300 hidden md:table-cell">{feed.date}</td>
                <td className="px-4 py-4">
                  <button
                    onClick={() => handleDownload(feed.id)}
                    disabled={downloaded}
                    className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition whitespace-nowrap ${
                      downloaded
                        ? "text-green-600 dark:text-green-400 cursor-default"
                        : "border border-blue-200 dark:border-blue-700 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/40"
                    }`}
                  >
                    {downloaded ? <Check className="w-4 h-4" /> : <Download className="w-4 h-4" />}
                    {downloaded ? t("search.added") : t("feeds.download")}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </DataTable>
    </div>
  );
};
