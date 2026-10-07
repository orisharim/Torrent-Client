import { useEffect, useState } from "react";
import type { GlobalSettings } from "../services/types";
import { API_BASE } from "../services/backend";

export const DEFAULT_GLOBAL_SETTINGS: GlobalSettings = {
    enable_receiving: true,
    enable_dht: true,
    enable_port_downloading: true,
};

const jsonHeaders = { "Content-Type": "application/json" };

const getGlobalSettings = async (): Promise<GlobalSettings> => {
    const response = await fetch(`${API_BASE}/global_settings`, {
        method: "GET",
        headers: jsonHeaders,
    });
    if (!response.ok) throw new Error(`Request failed: ${response.status}`);

    const data = await response.json();
    return {
        enable_receiving: data.global_settings.enable_receiving_peers,
        enable_dht: data.global_settings.enable_dht,
        enable_port_downloading: data.global_settings.enable_port_forwarding,
    };
};

const saveGlobalSettings = async (settings: GlobalSettings): Promise<void> => {
    const response = await fetch(`${API_BASE}/global_settings`, {
        method: "PUT",
        headers: jsonHeaders,
        body: JSON.stringify({
            enable_receiving_peers: settings.enable_receiving,
            enable_dht: settings.enable_dht,
            enable_port_forwarding: settings.enable_port_downloading,
        }),
    });
    if (!response.ok) throw new Error(`Failed to save settings: ${response.status}`);
};

export function useSettings() {
    const [settings, setSettings] = useState<GlobalSettings>(DEFAULT_GLOBAL_SETTINGS);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getGlobalSettings()
            .then(setSettings)
            .finally(() => setLoading(false));
    }, []);

    const updateSetting = <K extends keyof GlobalSettings>(key: K, value: GlobalSettings[K]) => {
        setSettings((prev) => ({ ...prev, [key]: value }));
    };

    const saveSettings = async (next: GlobalSettings): Promise<void> => {
        await saveGlobalSettings(next);
        setSettings(next);
    };

    const resetSettings = async (): Promise<GlobalSettings> => {
        await saveSettings(DEFAULT_GLOBAL_SETTINGS);
        return DEFAULT_GLOBAL_SETTINGS;
    };

    return { settings, loading, updateSetting, saveSettings, resetSettings };
}
