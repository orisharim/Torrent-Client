import { invoke } from "@tauri-apps/api/core";
import type { Device } from "./types";

export const getDevices = async (): Promise<Device[]> =>
  invoke<Device[]>("get_devices");

export const disconnectDevice = async (id: number): Promise<void> =>
  invoke("disconnect_device", { id });
