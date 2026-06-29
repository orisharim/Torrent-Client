import { invoke } from "@tauri-apps/api/core";
import type { FeedItem, FeedStats } from "./types";

export const getFeeds = async (): Promise<FeedItem[]> =>
  invoke<FeedItem[]>("get_feeds");

export const getFeedStats = async (): Promise<FeedStats> =>
  invoke<FeedStats>("get_feed_stats");

export const addFeed = async (url: string): Promise<void> =>
  invoke("add_feed", { url });

export const refreshFeeds = async (): Promise<FeedItem[]> =>
  invoke<FeedItem[]>("refresh_feeds");

export const downloadFeedItem = async (id: number): Promise<void> =>
  invoke("download_feed_item", { id });
