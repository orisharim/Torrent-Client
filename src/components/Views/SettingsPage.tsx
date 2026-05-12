import React, { useState } from "react";
import {
  Settings as SettingsIcon,
  Download,
  Wifi,
  Lock,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useTheme, type Theme } from "../../context/ThemeContext";

type Section = "general" | "downloads" | "connection" | "privacy" | "advanced";

type AppSettings = {
  startOnStartup: boolean;
  minimizeToTray: boolean;
  language: string;
  savePath: string;
  downloadLimit: number;
  uploadLimit: number;
  autoStart: boolean;
  notifyOnComplete: boolean;
  listeningPort: number;
  enableUPnP: boolean;
  enableDHT: boolean;
  proxy: string;
  enableEncryption: boolean;
  anonymousMode: boolean;
  maxConnections: number;
  maxPeersPerTorrent: number;
};

const defaultSettings: AppSettings = {
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

const navItems: { id: Section; label: string; icon: React.ReactNode }[] = [
  { id: "general",    label: "General",    icon: <SettingsIcon size={15} /> },
  { id: "downloads",  label: "Downloads",  icon: <Download size={15} /> },
  { id: "connection", label: "Connection", icon: <Wifi size={15} /> },
  { id: "privacy",    label: "Privacy",    icon: <Lock size={15} /> },
  { id: "advanced",   label: "Advanced",   icon: <SlidersHorizontal size={15} /> },
];

const Toggle = ({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    onClick={() => onChange(!checked)}
    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none ${
      checked ? "bg-blue-500" : "bg-stone-300 dark:bg-stone-600"
    }`}
  >
    <span
      className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-200 ${
        checked ? "translate-x-4" : "translate-x-1"
      }`}
    />
  </button>
);

const Row = ({ label, sub, children }: { label: string; sub?: string; children: React.ReactNode }) => (
  <div className="flex items-center justify-between px-5 py-3 border-b border-blue-50 dark:border-blue-900/50 last:border-b-0">
    <div>
      <div className="text-sm text-stone-700 dark:text-stone-200">{label}</div>
      {sub && <div className="text-xs text-stone-400 dark:text-stone-500 mt-0.5">{sub}</div>}
    </div>
    <div className="ml-4 shrink-0">{children}</div>
  </div>
);

const SectionCard = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="bg-white dark:bg-stone-800 border border-blue-100 dark:border-blue-900 rounded-xl overflow-hidden">
    <div className="px-5 py-2.5 border-b border-blue-100 dark:border-blue-900 bg-blue-50 dark:bg-blue-950/60">
      <span className="text-xs font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wide">{title}</span>
    </div>
    {children}
  </div>
);

const inputCls = "text-sm border border-blue-200 dark:border-blue-700 rounded-lg px-2 py-1 bg-white dark:bg-stone-700 text-stone-700 dark:text-stone-200 focus:outline-none focus:ring-1 focus:ring-blue-400";

type SettingsPageProps = {
  onClose: () => void;
};

export const SettingsPage = ({ onClose }: SettingsPageProps) => {
  const { theme, setTheme } = useTheme();
  const [activeSection, setActiveSection] = useState<Section>("general");
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [saved, setSaved] = useState(false);

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => { setSaved(false); onClose(); }, 1200);
  };

  const handleReset = () => {
    if (confirm("Reset all settings to defaults?")) setSettings(defaultSettings);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-stone-50 dark:bg-stone-900 rounded-2xl shadow-2xl w-full max-w-lg mx-4 flex flex-col overflow-hidden max-h-[90vh]">

        {/* Header */}
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

        {/* Section nav */}
        <div className="flex gap-1 px-4 py-2.5 bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900 overflow-x-auto shrink-0">
          {navItems.map(({ id, label, icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveSection(id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                activeSection === id
                  ? "bg-blue-600 text-white"
                  : "text-stone-500 dark:text-stone-400 hover:bg-blue-50 dark:hover:bg-blue-900/40 hover:text-blue-600 dark:hover:text-blue-300"
              }`}
            >
              {icon}
              {label}
            </button>
          ))}
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
          {activeSection === "general" && (
            <>
              <SectionCard title="General">
                <Row label="Start on system startup" sub="Launch automatically when you log in">
                  <Toggle checked={settings.startOnStartup} onChange={(v) => update("startOnStartup", v)} />
                </Row>
                <Row label="Minimize to tray on close" sub="Keep running in the background">
                  <Toggle checked={settings.minimizeToTray} onChange={(v) => update("minimizeToTray", v)} />
                </Row>
                <Row label="Language">
                  <select value={settings.language} onChange={(e) => update("language", e.target.value)} className={inputCls}>
                    {["English", "Hebrew", "Spanish", "French", "German"].map((l) => <option key={l}>{l}</option>)}
                  </select>
                </Row>
                <Row label="Theme" sub="Takes effect immediately">
                  <select
                    value={theme}
                    onChange={(e) => setTheme(e.target.value as Theme)}
                    className={inputCls}
                  >
                    {["System default", "Light", "Dark"].map((t) => <option key={t}>{t}</option>)}
                  </select>
                </Row>
              </SectionCard>
              <DangerZone onReset={handleReset} />
            </>
          )}

          {activeSection === "downloads" && (
            <SectionCard title="Downloads">
              <Row label="Default save location" sub={settings.savePath}>
                <button type="button" className={`text-sm px-3 py-1 border border-blue-200 dark:border-blue-700 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/40 text-stone-600 dark:text-stone-300`}>
                  Browse
                </button>
              </Row>
              <Row label="Download speed limit" sub="0 = unlimited">
                <div className="flex items-center gap-1.5">
                  <input type="number" min={0} value={settings.downloadLimit}
                    onChange={(e) => update("downloadLimit", Number(e.target.value))}
                    className={`w-20 text-right ${inputCls}`}
                  />
                  <span className="text-xs text-stone-400 dark:text-stone-500">KB/s</span>
                </div>
              </Row>
              <Row label="Upload speed limit" sub="0 = unlimited">
                <div className="flex items-center gap-1.5">
                  <input type="number" min={0} value={settings.uploadLimit}
                    onChange={(e) => update("uploadLimit", Number(e.target.value))}
                    className={`w-20 text-right ${inputCls}`}
                  />
                  <span className="text-xs text-stone-400 dark:text-stone-500">KB/s</span>
                </div>
              </Row>
              <Row label="Auto-start downloads" sub="Begin as soon as a torrent is added">
                <Toggle checked={settings.autoStart} onChange={(v) => update("autoStart", v)} />
              </Row>
              <Row label="Notify when complete">
                <Toggle checked={settings.notifyOnComplete} onChange={(v) => update("notifyOnComplete", v)} />
              </Row>
            </SectionCard>
          )}

          {activeSection === "connection" && (
            <SectionCard title="Connection">
              <Row label="Listening port">
                <input type="number" value={settings.listeningPort}
                  onChange={(e) => update("listeningPort", Number(e.target.value))}
                  className={`w-20 text-right ${inputCls}`}
                />
              </Row>
              <Row label="Enable UPnP port mapping">
                <Toggle checked={settings.enableUPnP} onChange={(v) => update("enableUPnP", v)} />
              </Row>
              <Row label="Enable DHT" sub="Distributed hash table for trackerless torrents">
                <Toggle checked={settings.enableDHT} onChange={(v) => update("enableDHT", v)} />
              </Row>
              <Row label="Proxy">
                <select value={settings.proxy} onChange={(e) => update("proxy", e.target.value)} className={inputCls}>
                  {["None", "SOCKS5", "HTTP"].map((p) => <option key={p}>{p}</option>)}
                </select>
              </Row>
            </SectionCard>
          )}

          {activeSection === "privacy" && (
            <SectionCard title="Privacy">
              <Row label="Enable encryption" sub="Encrypt peer connections when possible">
                <Toggle checked={settings.enableEncryption} onChange={(v) => update("enableEncryption", v)} />
              </Row>
              <Row label="Anonymous mode" sub="Hides client identity from trackers and peers">
                <Toggle checked={settings.anonymousMode} onChange={(v) => update("anonymousMode", v)} />
              </Row>
            </SectionCard>
          )}

          {activeSection === "advanced" && (
            <SectionCard title="Advanced">
              <Row label="Max global connections">
                <input type="number" min={1} value={settings.maxConnections}
                  onChange={(e) => update("maxConnections", Number(e.target.value))}
                  className={`w-20 text-right ${inputCls}`}
                />
              </Row>
              <Row label="Max peers per torrent">
                <input type="number" min={1} value={settings.maxPeersPerTorrent}
                  onChange={(e) => update("maxPeersPerTorrent", Number(e.target.value))}
                  className={`w-20 text-right ${inputCls}`}
                />
              </Row>
            </SectionCard>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-3 bg-white dark:bg-stone-800 border-t border-blue-100 dark:border-blue-900 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="text-sm px-4 py-2 rounded-full border border-blue-200 dark:border-blue-700 text-stone-600 dark:text-stone-300 hover:bg-blue-50 dark:hover:bg-blue-900/40 transition-colors"
          >
            Cancel
          </button>
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
      </div>
    </div>
  );
};

const DangerZone = ({ onReset }: { onReset: () => void }) => (
  <SectionCard title="Danger zone">
    <Row label="Clear all completed torrents" sub="Removes completed entries from the list">
      <button type="button" className="text-sm px-3 py-1 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30">
        Clear
      </button>
    </Row>
    <Row label="Reset all settings" sub="Restores defaults — cannot be undone">
      <button type="button" onClick={onReset} className="text-sm px-3 py-1 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30">
        Reset
      </button>
    </Row>
  </SectionCard>
);
