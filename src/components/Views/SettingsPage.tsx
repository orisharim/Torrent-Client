import React, { useEffect, useState } from "react";
import { Settings as SettingsIcon, X } from "lucide-react";
import { useTorrents } from "../../context/TorrentContext";
import { useUI } from "../../context/UIContext";
import Button from "../UI/Button";
import Modal from "../UI/Modal";
import Toggle from "../UI/Toggle";
import * as settingsService from "../../services/settingsService";
import type { AppSettings } from "../../services/types";

const Row = ({ label, sub, children }: { label: string; sub?: string; children: React.ReactNode }) => (
  <div className="flex items-center justify-between gap-3">
    <div className="min-w-0">
      <div className="text-sm text-stone-700 dark:text-stone-200">{label}</div>
      {sub && <div className="text-xs text-stone-400 dark:text-stone-500 mt-0.5 truncate" title={sub}>{sub}</div>}
    </div>
    <div className="ms-4 shrink-0">{children}</div>
  </div>
);

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="flex flex-col gap-3">
    <h3 className="text-xs font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wide">{title}</h3>
    <div className="flex flex-col gap-4">{children}</div>
  </div>
);

const inputCls = "text-sm border border-blue-200 dark:border-blue-700 rounded-lg px-2 py-1 bg-white dark:bg-stone-700 text-stone-700 dark:text-stone-200 focus:outline-none focus:ring-1 focus:ring-blue-400";

type SettingsPageProps = {
  onClose: () => void;
};

export const SettingsPage = ({ onClose }: SettingsPageProps) => {
  const { showToast } = useUI();
  const [settings, setSettings] = useState<AppSettings>(settingsService.DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    settingsService.getSettings().then(setSettings);
  }, []);

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    settingsService.saveSettings(settings); // REPLACE: await + error handling
    setSaved(true);
    showToast("Settings saved");
    setTimeout(() => { setSaved(false); onClose(); }, 1200);
  };

  const handleReset = () => {
    if (confirm("Reset all settings to defaults?")) {
      settingsService.resetSettings().then(setSettings);
    }
  };

  return (
    <Modal
      onClose={onClose}
      widthCls="max-w-xl h-[85vh] max-h-[600px]"
      panelCls="bg-stone-50 dark:bg-stone-900 flex flex-col overflow-hidden"
    >
      <div className="flex items-center justify-between px-5 py-4 bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900 shrink-0">
        <div className="flex items-center gap-2 text-blue-700 dark:text-blue-400">
          <SettingsIcon size={18} />
          <span className="font-semibold text-base">Settings</span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-full text-stone-400 dark:text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-700 hover:text-stone-600 dark:hover:text-stone-300 transition-colors"
        >
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-5">
        <div className="bg-white dark:bg-stone-800 border border-blue-100 dark:border-blue-900 rounded-xl p-5 flex flex-col gap-6">
          <Section title="Connection">
            <Row label="Max connections" sub="0 = unlimited">
              <input
                type="number"
                min={0}
                value={settings.maxConnections}
                onChange={(e) => update("maxConnections", Number(e.target.value))}
                className={`w-20 text-end ${inputCls}`}
              />
            </Row>
            <Row label="Tracker amount" sub="0 = contact all trackers">
              <input
                type="number"
                min={0}
                value={settings.trackerAmount}
                onChange={(e) => update("trackerAmount", Number(e.target.value))}
                className={`w-20 text-end ${inputCls}`}
              />
            </Row>
            <Row label="Enable receiving peers">
              <Toggle checked={settings.enableReceivingPeers} onChange={(v) => update("enableReceivingPeers", v)} />
            </Row>
            <Row label="Enable DHT" sub="Distributed hash table for trackerless torrents">
              <Toggle checked={settings.enableDht} onChange={(v) => update("enableDht", v)} />
            </Row>
            <Row label="Enable port forwarding">
              <Toggle checked={settings.enablePortForwarding} onChange={(v) => update("enablePortForwarding", v)} />
            </Row>
          </Section>

          <Section title="Speed Limits">
            <Row label="Download speed limit" sub="0 = unlimited">
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={0}
                  step={0.1}
                  value={settings.downloadSpeedLimit}
                  onChange={(e) => update("downloadSpeedLimit", Number(e.target.value))}
                  className={`w-20 text-end ${inputCls}`}
                />
                <span className="text-xs text-stone-400 dark:text-stone-500">MB/s</span>
              </div>
            </Row>
            <Row label="Upload speed limit" sub="0 = unlimited">
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={0}
                  step={0.1}
                  value={settings.uploadSpeedLimit}
                  onChange={(e) => update("uploadSpeedLimit", Number(e.target.value))}
                  className={`w-20 text-end ${inputCls}`}
                />
                <span className="text-xs text-stone-400 dark:text-stone-500">MB/s</span>
              </div>
            </Row>
          </Section>

          <DangerZone onReset={handleReset} />
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 px-5 py-3 bg-white dark:bg-stone-800 border-t border-blue-100 dark:border-blue-900 shrink-0">
        <Button text="Cancel" action={onClose} />
        <button
          type="button"
          onClick={handleSave}
          className={`text-sm px-4 py-2 rounded-full text-white font-medium transition-colors ${
            saved ? "bg-green-500" : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          {saved ? "Saved!" : "Save changes"}
        </button>
      </div>
    </Modal>
  );
};

const DangerZone = ({ onReset }: { onReset: () => void }) => {
  const { torrents, clearCompleted } = useTorrents();
  const { showToast } = useUI();
  const hasCompleted = torrents.some((torrent) => torrent.status === "Completed");

  return (
    <Section title="Danger zone">
      <Row label="Clear all completed torrents" sub="Removes completed entries from the list">
        <Button
          text="Clear"
          action={() => { clearCompleted(); showToast("Completed torrents cleared"); }}
          variant="danger"
          disabled={!hasCompleted}
        />
      </Row>
      <Row label="Reset all settings" sub="Restores defaults — cannot be undone">
        <Button text="Reset" action={onReset} variant="danger" />
      </Row>
    </Section>
  );
};
