import React, { useState } from "react";
import {
  Settings as SettingsIcon,
  Download,
  Wifi,
  Lock,
  SlidersHorizontal,
} from "lucide-react";

type Section = "general" | "downloads" | "connection" | "privacy" | "advanced";

type AppSettings = {
  startOnStartup: boolean;
  minimizeToTray: boolean;
  language: string;
  theme: string;
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
  theme: "System default",
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
  { id: "general", label: "General", icon: <SettingsIcon size={16} /> },
  { id: "downloads", label: "Downloads", icon: <Download size={16} /> },
  { id: "connection", label: "Connection", icon: <Wifi size={16} /> },
  { id: "privacy", label: "Privacy", icon: <Lock size={16} /> },
  { id: "advanced", label: "Advanced", icon: <SlidersHorizontal size={16} /> },
];

const Toggle = ({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    onClick={() => onChange(!checked)}
    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none ${
      checked ? "bg-blue-500" : "bg-stone-300"
    }`}
  >
    <span
      className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-200 ${
        checked ? "translate-x-4" : "translate-x-1"
      }`}
    />
  </button>
);

const Row = ({
  label,
  sub,
  children,
}: {
  label: string;
  sub?: string;
  children: React.ReactNode;
}) => (
  <div className="flex items-center justify-between px-4 py-3 border-b border-blue-100 last:border-b-0">
    <div>
      <div className="text-sm text-stone-700">{label}</div>
      {sub && <div className="text-xs text-stone-400 mt-0.5">{sub}</div>}
    </div>
    <div className="ml-4 shrink-0">{children}</div>
  </div>
);

const SectionCard = ({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) => (
  <div className="bg-white border border-blue-200 rounded-lg overflow-hidden shadow-sm">
    <div className="px-4 py-2.5 border-b border-blue-100 bg-blue-50">
      <span className="text-sm font-semibold text-blue-800">{title}</span>
    </div>
    {children}
  </div>
);

export const SettingsPage = () => {
  const [activeSection, setActiveSection] = useState<Section>("general");
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [saved, setSaved] = useState(false);

  const update = <K extends keyof AppSettings>(
    key: K,
    value: AppSettings[K]
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    if (confirm("Reset all settings to defaults?")) {
      setSettings(defaultSettings);
    }
  };

  return (
    <div className="min-h-screen bg-stone-50 flex flex-col">
      {/* Top buttons */}
      <div className="sticky top-0 z-50 mt-4 bg-blue-100 px-4 py-2 flex gap-2 overflow-x-auto">
        {navItems.map(({ id, label, icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setActiveSection(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded text-sm whitespace-nowrap transition ${
              activeSection === id
                ? "bg-stone-50 text-blue-600 font-semibold"
                : "text-stone-600 hover:bg-stone-50"
            }`}
          >
            {icon}
            <span>{label}</span>
          </button>
        ))}
      </div>

      <main className="flex-1 p-4 flex flex-col gap-5 w-full">
        {activeSection === "general" && (
          <>
            <SectionCard title="General">
              <Row
                label="Start on system startup"
                sub="Launch automatically when you log in"
              >
                <Toggle
                  checked={settings.startOnStartup}
                  onChange={(v) => update("startOnStartup", v)}
                />
              </Row>

              <Row
                label="Minimize to tray on close"
                sub="Keep running in the background"
              >
                <Toggle
                  checked={settings.minimizeToTray}
                  onChange={(v) => update("minimizeToTray", v)}
                />
              </Row>

              <Row label="Language">
                <select
                  value={settings.language}
                  onChange={(e) => update("language", e.target.value)}
                  className="text-sm border border-blue-200 rounded px-2 py-1 bg-white text-stone-700 focus:outline-none focus:ring-1 focus:ring-blue-400"
                >
                  {["English", "Hebrew", "Spanish", "French", "German"].map(
                    (l) => (
                      <option key={l}>{l}</option>
                    )
                  )}
                </select>
              </Row>

              <Row label="Theme">
                <select
                  value={settings.theme}
                  onChange={(e) => update("theme", e.target.value)}
                  className="text-sm border border-blue-200 rounded px-2 py-1 bg-white text-stone-700 focus:outline-none focus:ring-1 focus:ring-blue-400"
                >
                  {["System default", "Light", "Dark"].map((t) => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </Row>
            </SectionCard>

            <DangerZone onReset={handleReset} />
          </>
        )}

        {activeSection === "downloads" && (
          <SectionCard title="Downloads">
            <Row label="Default save location" sub={settings.savePath}>
              <button
                type="button"
                className="text-sm px-3 py-1 border border-blue-200 rounded hover:bg-blue-50 text-stone-600"
              >
                Browse
              </button>
            </Row>

            <Row label="Download speed limit" sub="0 = unlimited">
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={0}
                  value={settings.downloadLimit}
                  onChange={(e) =>
                    update("downloadLimit", Number(e.target.value))
                  }
                  className="w-20 text-sm text-right border border-blue-200 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <span className="text-xs text-stone-400">KB/s</span>
              </div>
            </Row>

            <Row label="Upload speed limit" sub="0 = unlimited">
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={0}
                  value={settings.uploadLimit}
                  onChange={(e) =>
                    update("uploadLimit", Number(e.target.value))
                  }
                  className="w-20 text-sm text-right border border-blue-200 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <span className="text-xs text-stone-400">KB/s</span>
              </div>
            </Row>

            <Row
              label="Auto-start downloads"
              sub="Begin as soon as a torrent is added"
            >
              <Toggle
                checked={settings.autoStart}
                onChange={(v) => update("autoStart", v)}
              />
            </Row>

            <Row label="Notify when complete">
              <Toggle
                checked={settings.notifyOnComplete}
                onChange={(v) => update("notifyOnComplete", v)}
              />
            </Row>
          </SectionCard>
        )}

        {activeSection === "connection" && (
          <SectionCard title="Connection">
            <Row label="Listening port">
              <input
                type="number"
                value={settings.listeningPort}
                onChange={(e) =>
                  update("listeningPort", Number(e.target.value))
                }
                className="w-20 text-sm text-right border border-blue-200 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </Row>

            <Row label="Enable UPnP port mapping">
              <Toggle
                checked={settings.enableUPnP}
                onChange={(v) => update("enableUPnP", v)}
              />
            </Row>

            <Row
              label="Enable DHT"
              sub="Distributed hash table for trackerless torrents"
            >
              <Toggle
                checked={settings.enableDHT}
                onChange={(v) => update("enableDHT", v)}
              />
            </Row>

            <Row label="Proxy">
              <select
                value={settings.proxy}
                onChange={(e) => update("proxy", e.target.value)}
                className="text-sm border border-blue-200 rounded px-2 py-1 bg-white text-stone-700 focus:outline-none focus:ring-1 focus:ring-blue-400"
              >
                {["None", "SOCKS5", "HTTP"].map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </Row>
          </SectionCard>
        )}

        {activeSection === "privacy" && (
          <SectionCard title="Privacy">
            <Row
              label="Enable encryption"
              sub="Encrypt peer connections when possible"
            >
              <Toggle
                checked={settings.enableEncryption}
                onChange={(v) => update("enableEncryption", v)}
              />
            </Row>

            <Row
              label="Anonymous mode"
              sub="Hides client identity from trackers and peers"
            >
              <Toggle
                checked={settings.anonymousMode}
                onChange={(v) => update("anonymousMode", v)}
              />
            </Row>
          </SectionCard>
        )}

        {activeSection === "advanced" && (
          <SectionCard title="Advanced">
            <Row label="Max global connections">
              <input
                type="number"
                min={1}
                value={settings.maxConnections}
                onChange={(e) =>
                  update("maxConnections", Number(e.target.value))
                }
                className="w-20 text-sm text-right border border-blue-200 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </Row>

            <Row label="Max peers per torrent">
              <input
                type="number"
                min={1}
                value={settings.maxPeersPerTorrent}
                onChange={(e) =>
                  update("maxPeersPerTorrent", Number(e.target.value))
                }
                className="w-20 text-sm text-right border border-blue-200 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </Row>
          </SectionCard>
        )}

        <div className="flex items-center justify-end gap-3 pt-1">
          <button
            type="button"
            onClick={() => setSettings(defaultSettings)}
            className="text-sm px-4 py-2 border border-blue-200 rounded hover:bg-blue-50 text-stone-600"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleSave}
            className={`text-sm px-4 py-2 rounded text-white transition-colors ${
              saved ? "bg-green-500" : "bg-blue-500 hover:bg-blue-600"
            }`}
          >
            {saved ? "Saved!" : "Save changes"}
          </button>
        </div>
      </main>
    </div>
  );
};

const DangerZone = ({ onReset }: { onReset: () => void }) => (
  <SectionCard title="Danger zone">
    <Row
      label="Clear all completed torrents"
      sub="Removes completed entries from the list"
    >
      <button
        type="button"
        className="text-sm px-3 py-1 border border-red-200 rounded text-red-600 hover:bg-red-50"
      >
        Clear
      </button>
    </Row>

    <Row label="Reset all settings" sub="Restores defaults — cannot be undone">
      <button
        type="button"
        onClick={onReset}
        className="text-sm px-3 py-1 border border-red-200 rounded text-red-600 hover:bg-red-50"
      >
        Reset
      </button>
    </Row>
  </SectionCard>
);