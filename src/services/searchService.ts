import { invoke } from "@tauri-apps/api/core";
import type { SearchResult } from "./types";

export const searchTorrents = async (query: string): Promise<SearchResult[]> =>
  invoke<SearchResult[]>("search_torrents", { query });
