import { invoke } from "@tauri-apps/api/core";
import { safeCall, withFallback } from "./backend";
import { DEMO_TORRENTS, DEMO_TORRENT_DETAILS, DEMO_TORRENT_PAGE_STATS, demoAddedTorrent } from "./demoData";
import type { AddTorrentPayload, Torrent, TorrentDetail, TorrentPageStats, TorrentStatus } from "./types";

export const getTorrents = async (): Promise<Torrent[]> =>
  withFallback(invoke<Torrent[]>("get_torrents"), () => DEMO_TORRENTS);

export const getTorrentDetails = async (): Promise<TorrentDetail[]> =>
  withFallback(invoke<TorrentDetail[]>("get_torrent_details"), () => DEMO_TORRENT_DETAILS);

export const getTorrentPageStats = async (): Promise<TorrentPageStats> =>
  withFallback(invoke<TorrentPageStats>("get_torrent_page_stats"), () => DEMO_TORRENT_PAGE_STATS);

export const addTorrent = async (payload: AddTorrentPayload): Promise<Torrent> => {
  try {
    return await invoke<Torrent>("add_torrent", { payload });
  } catch (error) {
    console.warn("[backend unavailable — using demo fallback]", error);
    return demoAddedTorrent(payload);
  }
};

export const pauseTorrent = async (id: number): Promise<void> =>
  safeCall(invoke("pause_torrent", { id }));

export const resumeTorrent = async (id: number): Promise<void> =>
  safeCall(invoke("resume_torrent", { id }));

export const deleteTorrents = async (ids: number[]): Promise<void> =>
  safeCall(invoke("delete_torrents", { ids }));

export const updateTorrentStatus = async (id: number, status: TorrentStatus): Promise<void> =>
  safeCall(invoke("update_torrent_status", { id, status }));

export const clearCompleted = async (): Promise<void> =>
  safeCall(invoke("clear_completed"));
