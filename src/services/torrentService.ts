import { invoke } from "@tauri-apps/api/core";
import type { AddTorrentPayload, Torrent, TorrentDetail, TorrentPageStats, TorrentStatus } from "./types";

export const getTorrents = async (): Promise<Torrent[]> =>
  invoke<Torrent[]>("get_torrents");

export const getTorrentDetails = async (): Promise<TorrentDetail[]> =>
  invoke<TorrentDetail[]>("get_torrent_details");

export const getTorrentPageStats = async (): Promise<TorrentPageStats> =>
  invoke<TorrentPageStats>("get_torrent_page_stats");

export const addTorrent = async (payload: AddTorrentPayload): Promise<Torrent> =>
  invoke<Torrent>("add_torrent", { payload });

export const pauseTorrent = async (id: number): Promise<void> =>
  invoke("pause_torrent", { id });

export const resumeTorrent = async (id: number): Promise<void> =>
  invoke("resume_torrent", { id });

export const deleteTorrents = async (ids: number[]): Promise<void> =>
  invoke("delete_torrents", { ids });

export const updateTorrentStatus = async (id: number, status: TorrentStatus): Promise<void> =>
  invoke("update_torrent_status", { id, status });

export const clearCompleted = async (): Promise<void> =>
  invoke("clear_completed");
