import { invoke } from "@tauri-apps/api/core";
import { safeCall, withFallback } from "./backend";
import { DEMO_DEVICES } from "./demoData";
import type { Device } from "./types";

export const getDevices = async (): Promise<Device[]> =>
  withFallback(invoke<Device[]>("get_devices"), () => DEMO_DEVICES);

export const disconnectDevice = async (id: number): Promise<void> =>
  safeCall(invoke("disconnect_device", { id }));
