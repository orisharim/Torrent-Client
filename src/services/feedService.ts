import { invoke } from "@tauri-apps/api/core";
import { safeCall, withFallback } from "./backend";
import { DEMO_FEEDS, DEMO_FEED_STATS } from "./demoData";
import type { FeedItem, FeedStats } from "./types";

export const getFeeds = async (): Promise<FeedItem[]> =>
  withFallback(invoke<FeedItem[]>("get_feeds"), () => DEMO_FEEDS);

export const getFeedStats = async (): Promise<FeedStats> =>
  withFallback(invoke<FeedStats>("get_feed_stats"), () => DEMO_FEED_STATS);

export const addFeed = async (url: string): Promise<void> =>
  safeCall(invoke("add_feed", { url }));

export const refreshFeeds = async (): Promise<FeedItem[]> =>
  withFallback(invoke<FeedItem[]>("refresh_feeds"), () => DEMO_FEEDS);

export const downloadFeedItem = async (id: number): Promise<void> =>
  safeCall(invoke("download_feed_item", { id }));
