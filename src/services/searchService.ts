import { invoke } from "@tauri-apps/api/core";
import { withFallback } from "./backend";
import { demoSearchResults } from "./demoData";
import type { SearchResult } from "./types";

export const searchTorrents = async (query: string): Promise<SearchResult[]> =>
  withFallback(invoke<SearchResult[]>("search_torrents", { query }), () => demoSearchResults(query));
