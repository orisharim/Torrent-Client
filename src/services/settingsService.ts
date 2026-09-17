import { invoke } from "@tauri-apps/api/core";
import { safeCall, withFallback } from "./backend";
import type { AppSettings } from "./types";

// Used as the initial React state while getSettings() is in-flight.
export const DEFAULT_SETTINGS: AppSettings = {
  maxConnections: 50,
  downloadSpeedLimit: 0,
  uploadSpeedLimit: 0,
  trackerAmount: 4,
  enableReceivingPeers: true,
  enableDht: true,
  enablePortForwarding: true,
};

export const getSettings = async (): Promise<AppSettings> =>
  withFallback(invoke<AppSettings>("get_settings"), () => DEFAULT_SETTINGS);

export const saveSettings = async (settings: AppSettings): Promise<void> =>
  safeCall(invoke("save_settings", { settings }));

export const resetSettings = async (): Promise<AppSettings> =>
  withFallback(invoke<AppSettings>("reset_settings"), () => DEFAULT_SETTINGS);
