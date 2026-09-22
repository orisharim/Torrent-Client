import { useEffect, useState } from "react";
import type { AppSettings } from "../services/types";

// TODO put real url (temp)
const URL = "http://localhost:8080";

export const DEFAULT_SETTINGS: AppSettings = {
    max_connection: 50,
    download_speed: 0,
    upload_speed_limit: 0,
    tracker_amount: 4,
    enable_receiving: true,
    enable_dht: true,
    enable_port_downloading: true,
};

const jsonHeaders = { "Content-Type": "application/json" };

// TODO put real url (temp) — path unconfirmed, guessing "/settings" to match the /torrents convention
const getSettings = async (): Promise<AppSettings> => {
    const response = await fetch(`${URL}/settings`, {
        method: "GET",
        headers: jsonHeaders,
    });
    if (!response.ok) throw new Error(`Request failed: ${response.status}`);
    return response.json();
};

// contract from teammate: POST {settingsName, value} — one field per call
const postSetting = async <K extends keyof AppSettings>(settingsName: K, value: AppSettings[K]): Promise<boolean> => {
    const response = await fetch(`${URL}/settings`, {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ settingsName, value }),
    });
    return response.ok;
};

export function useSettings() {
    const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getSettings()
            .then(setSettings)
            .finally(() => setLoading(false));
    }, []);

    const updateSetting = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
        setSettings((prev) => ({ ...prev, [key]: value }));
    };

    // sends every field in `next` to the backend, one POST per field per the {settingsName, value} contract
    const saveSettings = async (next: AppSettings): Promise<void> => {
        const keys = Object.keys(next) as (keyof AppSettings)[];
        await Promise.all(keys.map((key) => postSetting(key, next[key])));
        setSettings(next);
    };

    const resetSettings = async (): Promise<AppSettings> => {
        await saveSettings(DEFAULT_SETTINGS);
        return DEFAULT_SETTINGS;
    };

    return { settings, loading, updateSetting, saveSettings, resetSettings };
}
