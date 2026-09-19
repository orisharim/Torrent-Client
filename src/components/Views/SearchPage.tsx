import { useEffect, useState } from "react";
import { Download, Loader2, Search, SearchX } from "lucide-react";
import DataTable from "../UI/DataTable";
import { tableRowCls, thCls } from "../UI/tableStyles";
import EmptyState from "../UI/EmptyState";
import PageHeader from "../UI/PageHeader";
import { useUI } from "../../context/UIContext";
import * as searchService from "../../services/searchService";
import type { SearchResult } from "../../services/types";

export const SearchPage = () => {
  const { searchQuery, showToast } = useUI();

  const [results, setResults] = useState<SearchResult[]>([]);
  const [loadedQuery, setLoadedQuery] = useState("");

  const loading = searchQuery !== "" && loadedQuery !== searchQuery;

  useEffect(() => {
    if (!searchQuery) return;
    let cancelled = false;
    searchService.searchTorrents(searchQuery).then((found) => {
      if (cancelled) return;
      setResults(found);
      setLoadedQuery(searchQuery);
    });
    return () => { cancelled = true; };
  }, [searchQuery]);

  // TODO: backend only accepts add-by-local-file-path — search results are remote magnet
  // links with no local torrentFilePath, so this can't be wired up until the backend
  // supports adding by magnet/URL (or fetches the .torrent itself before handing back a path).
  const handleDownload = (result: SearchResult) => {
    void result;
    showToast("Adding from search isn't supported by the backend yet");
  };

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <PageHeader
        title="Search Results"
        subtitle={`Results for "${searchQuery}"`}
      />

      <DataTable
        icon={<Search className="w-4 h-4" />}
        title="Search Results"
        count={loading ? 0 : results.length}
        countLabel="results"
        emptyState={
          loading ? (
            <EmptyState
              icon={<Loader2 size={28} className="animate-spin" />}
              title="Searching…"
            />
          ) : (
            <EmptyState
              icon={<SearchX size={28} />}
              title="No torrents found"
              description="Try a different search term"
            />
          )
        }
      >
        <thead className="bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900">
          <tr className="text-start text-stone-500 dark:text-stone-400">
            <th className={thCls}>Name</th>
            <th className={`${thCls} whitespace-nowrap`}>Size</th>
            <th className={thCls}>Seeds</th>
            <th className={`${thCls} hidden md:table-cell`}>Peers</th>
            <th className={thCls}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result, index) => (
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
              <td className="px-4 py-4">
                <button
                  onClick={() => handleDownload(result)}
                  disabled
                  title="Not supported yet — backend only adds torrents by local file path"
                  className="inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm whitespace-nowrap text-stone-400 dark:text-stone-500 border border-stone-200 dark:border-stone-700 cursor-not-allowed"
                >
                  <Download className="w-4 h-4" />
                  Download
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
};
