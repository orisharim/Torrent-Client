import { invoke } from "@tauri-apps/api/core";
import type { HomeStats } from "./types";

export const getHomeStats = async (): Promise<HomeStats> =>
  invoke<HomeStats>("get_home_stats");
