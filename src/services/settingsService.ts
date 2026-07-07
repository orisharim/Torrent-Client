import { invoke } from "@tauri-apps/api/core";
import { safeCall, withFallback } from "./backend";
import type { AppSettings } from "./types";

// Used as the initial React state while getSettings() is in-flight.
export const DEFAULT_SETTINGS: AppSettings = {
  startOnStartup: true,
  minimizeToTray: true,
  language: "English",
  savePath: "/Users/user/Downloads",
  downloadLimit: 0,
  uploadLimit: 50,
  autoStart: true,
  notifyOnComplete: true,
  listeningPort: 6881,
  enableUPnP: true,
  enableDHT: true,
  proxy: "None",
  enableEncryption: true,
  anonymousMode: false,
  maxConnections: 200,
  maxPeersPerTorrent: 50,
};

export const getSettings = async (): Promise<AppSettings> =>
  withFallback(invoke<AppSettings>("get_settings"), () => DEFAULT_SETTINGS);

export const saveSettings = async (settings: AppSettings): Promise<void> =>
  safeCall(invoke("save_settings", { settings }));

export const resetSettings = async (): Promise<AppSettings> =>
  withFallback(invoke<AppSettings>("reset_settings"), () => DEFAULT_SETTINGS);
