import { useEffect, useState } from "react";
import { Check, Download, Loader2, Search, SearchX } from "lucide-react";
import DataTable from "../UI/DataTable";
import { tableRowCls, thCls } from "../UI/tableStyles";
import EmptyState from "../UI/EmptyState";
import PageHeader from "../UI/PageHeader";
import { healthStyles } from "../UI/badgeStyles";
import { useLanguage } from "../../context/LanguageContext";
import { useTorrents } from "../../context/TorrentContext";
import { useUI } from "../../context/UIContext";
import * as searchService from "../../services/searchService";
import type { SearchResult } from "../../services/types";

export const SearchPage = () => {
  const { t } = useLanguage();
  const { addTorrent } = useTorrents();
  const { searchQuery, showToast } = useUI();

  const [results, setResults] = useState<SearchResult[]>([]);
  const [loadedQuery, setLoadedQuery] = useState("");
  const [addedIds, setAddedIds] = useState<Set<number>>(new Set());

  const loading = searchQuery !== "" && loadedQuery !== searchQuery;

  useEffect(() => {
    if (!searchQuery) return;
    let cancelled = false;
    searchService.searchTorrents(searchQuery).then((found) => {
      if (cancelled) return;
      setResults(found);
      setAddedIds(new Set());
      setLoadedQuery(searchQuery);
    });
    return () => { cancelled = true; };
  }, [searchQuery]);

  const handleDownload = async (result: SearchResult) => {
    setAddedIds((prev) => new Set(prev).add(result.id));
    await addTorrent({ type: "magnet", uri: result.magnet });
    showToast(t("add.success"));
  };

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <PageHeader
        title={t("search.title")}
        subtitle={t("search.subtitle").replace("{query}", searchQuery)}
      />

      <DataTable
        icon={<Search className="w-4 h-4" />}
        title={t("search.title")}
        count={loading ? 0 : results.length}
        countLabel={t("search.results")}
        emptyState={
          loading ? (
            <EmptyState
              icon={<Loader2 size={28} className="animate-spin" />}
              title={t("search.searching")}
            />
          ) : (
            <EmptyState
              icon={<SearchX size={28} />}
              title={t("search.noResults")}
              description={t("search.tryDifferent")}
            />
          )
        }
      >
        <thead className="bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900">
          <tr className="text-start text-stone-500 dark:text-stone-400">
            <th className={thCls}>{t("table.name")}</th>
            <th className={`${thCls} whitespace-nowrap`}>{t("table.size")}</th>
            <th className={thCls}>{t("search.seeds")}</th>
            <th className={`${thCls} hidden md:table-cell`}>{t("search.peers")}</th>
            <th className={`${thCls} hidden lg:table-cell`}>{t("table.health")}</th>
            <th className={thCls}>{t("feeds.action")}</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result, index) => {
            const added = addedIds.has(result.id);
            return (
              <tr key={result.id} className={tableRowCls(index)}>
                <td className="px-4 py-4">
                  <div className="font-medium text-stone-800 dark:text-stone-100 max-w-[20rem] truncate" title={result.name}>
                    {result.name}
                  </div>
                  <div className="text-xs text-stone-400 dark:text-stone-500">{result.source}</div>
                </td>
                <td className="px-4 py-4 text-stone-600 dark:text-stone-300 whitespace-nowrap">{result.size} GB</td>
                <td className="px-4 py-4 font-medium text-green-600 dark:text-green-400">{result.seeds}</td>
                <td className="px-4 py-4 text-stone-600 dark:text-stone-300 hidden md:table-cell">{result.peers}</td>
                <td className="px-4 py-4 hidden lg:table-cell">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${healthStyles[result.health]}`}>
                    {t(`health.${result.health.toLowerCase()}`)}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <button
                    onClick={() => handleDownload(result)}
                    disabled={added}
                    className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition whitespace-nowrap ${
                      added
                        ? "text-green-600 dark:text-green-400 cursor-default"
                        : "border border-blue-200 dark:border-blue-700 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/40"
                    }`}
                  >
                    {added ? <Check className="w-4 h-4" /> : <Download className="w-4 h-4" />}
                    {added ? t("search.added") : t("search.download")}
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
