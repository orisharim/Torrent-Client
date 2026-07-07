import { invoke } from "@tauri-apps/api/core";
import { withFallback } from "./backend";
import { DEMO_HOME_STATS } from "./demoData";
import type { HomeStats } from "./types";

export const getHomeStats = async (): Promise<HomeStats> =>
  withFallback(invoke<HomeStats>("get_home_stats"), () => DEMO_HOME_STATS);
