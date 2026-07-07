import React, { useEffect, useState } from "react";
import {
  Settings as SettingsIcon,
  Download,
  Wifi,
  Lock,
  SlidersHorizontal,
  Languages,
  X,
} from "lucide-react";
import { useLanguage, type Language } from "../../context/LanguageContext";
import { useTorrents } from "../../context/TorrentContext";
import { useUI } from "../../context/UIContext";
import Button from "../UI/Button";
import Modal from "../UI/Modal";
import Toggle from "../UI/Toggle";
import * as settingsService from "../../services/settingsService";
import type { AppSettings, ProxyType } from "../../services/types";

type Section = "general" | "language" | "downloads" | "connection" | "privacy" | "advanced";

const Row = ({ label, sub, children }: { label: string; sub?: string; children: React.ReactNode }) => (
  <div className="flex items-center justify-between gap-3 px-5 py-3 border-b border-blue-50 dark:border-blue-900/50 last:border-b-0">
    <div className="min-w-0">
      <div className="text-sm text-stone-700 dark:text-stone-200">{label}</div>
      {sub && <div className="text-xs text-stone-400 dark:text-stone-500 mt-0.5 truncate" title={sub}>{sub}</div>}
    </div>
    <div className="ms-4 shrink-0">{children}</div>
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
  const { language, setLanguage, t } = useLanguage();
  const { showToast } = useUI();
  const [activeSection, setActiveSection] = useState<Section>("general");
  const [settings, setSettings] = useState<AppSettings>(settingsService.DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);

  // Load persisted settings from service on mount.
  // Keep the UI language from localStorage as the source of truth — the loaded
  // settings.language is synced to it instead of overriding it.
  useEffect(() => {
    settingsService.getSettings().then((loaded) => {
      setSettings({ ...loaded, language });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const navItems: { id: Section; label: string; icon: React.ReactNode }[] = [
    { id: "general",    label: t("settings.general"),    icon: <SettingsIcon size={15} /> },
    { id: "language",   label: t("settings.language"),   icon: <Languages size={15} /> },
    { id: "downloads",  label: t("settings.downloads"),  icon: <Download size={15} /> },
    { id: "connection", label: t("settings.connection"), icon: <Wifi size={15} /> },
    { id: "privacy",    label: t("settings.privacy"),    icon: <Lock size={15} /> },
    { id: "advanced",   label: t("settings.advanced"),   icon: <SlidersHorizontal size={15} /> },
  ];

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    settingsService.saveSettings(settings); // REPLACE: await + error handling
    setSaved(true);
    showToast(t("settings.savedToast"));
    setTimeout(() => { setSaved(false); onClose(); }, 1200);
  };

  const handleReset = () => {
    if (confirm(t("settings.resetConfirm"))) {
      settingsService.resetSettings().then(setSettings); // REPLACE: uses returned defaults
    }
  };

  return (
    <Modal
      onClose={onClose}
      widthCls="max-w-3xl h-[85vh] max-h-[600px]"
      panelCls="bg-stone-50 dark:bg-stone-900 flex flex-col overflow-hidden"
    >
      <div className="flex items-center justify-between px-5 py-4 bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900 shrink-0">
        <div className="flex items-center gap-2 text-blue-700 dark:text-blue-400">
          <SettingsIcon size={18} />
          <span className="font-semibold text-base">{t("settings.title")}</span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-full text-stone-400 dark:text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-700 hover:text-stone-600 dark:hover:text-stone-300 transition-colors"
        >
          <X size={18} />
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">

        <div className="w-14 sm:w-44 shrink-0 bg-white dark:bg-stone-800 border-e border-blue-100 dark:border-blue-900 flex flex-col py-2">
          {navItems.map(({ id, label, icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveSection(id)}
              title={label}
              className={`flex items-center justify-center sm:justify-start gap-2.5 px-4 py-2.5 text-sm font-medium transition-colors text-start
                ${activeSection === id
                  ? "bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border-e-2 border-blue-600"
                  : "text-stone-500 dark:text-stone-400 hover:bg-stone-50 dark:hover:bg-stone-700/50 hover:text-stone-700 dark:hover:text-stone-200"
                }`}
            >
              {icon}
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto p-4 flex flex-col gap-4">
          {activeSection === "general" && (
            <>
              <SectionCard title={t("settings.general")}>
                <Row label={t("settings.startOnStartup")} sub={t("settings.startOnStartupSub")}>
                  <Toggle checked={settings.startOnStartup} onChange={(v) => update("startOnStartup", v)} />
                </Row>
                <Row label={t("settings.minimizeToTray")} sub={t("settings.minimizeToTraySub")}>
                  <Toggle checked={settings.minimizeToTray} onChange={(v) => update("minimizeToTray", v)} />
                </Row>
              </SectionCard>
              <DangerZone onReset={handleReset} />
            </>
          )}

          {activeSection === "language" && (
            <SectionCard title={t("settings.language")}>
              <Row label={t("settings.language")}>
                <select
                  value={language}
                  onChange={(e) => {
                    const next = e.target.value as Language;
                    setLanguage(next);
                    update("language", next);
                  }}
                  className={inputCls}
                >
                  {["English", "Hebrew", "Spanish", "French", "German"].map((l) => <option key={l}>{l}</option>)}
                </select>
              </Row>
            </SectionCard>
          )}

          {activeSection === "downloads" && (
            <SectionCard title={t("settings.downloads")}>
              <Row label={t("settings.saveLocation")}>
                {/* REPLACE: use tauri-plugin-dialog folder picker for native browsing */}
                <input
                  type="text"
                  value={settings.savePath}
                  onChange={(e) => update("savePath", e.target.value)}
                  className={`w-40 sm:w-56 ${inputCls}`}
                />
              </Row>
              <Row label={t("settings.downloadLimit")} sub={t("settings.unlimited")}>
                <div className="flex items-center gap-1.5">
                  <input
                    type="number"
                    min={0}
                    value={settings.downloadLimit}
                    onChange={(e) => update("downloadLimit", Number(e.target.value))}
                    className={`w-20 text-end ${inputCls}`}
                  />
                  <span className="text-xs text-stone-400 dark:text-stone-500">{t("settings.kbps")}</span>
                </div>
              </Row>
              <Row label={t("settings.uploadLimit")} sub={t("settings.unlimited")}>
                <div className="flex items-center gap-1.5">
                  <input
                    type="number"
                    min={0}
                    value={settings.uploadLimit}
                    onChange={(e) => update("uploadLimit", Number(e.target.value))}
                    className={`w-20 text-end ${inputCls}`}
                  />
                  <span className="text-xs text-stone-400 dark:text-stone-500">{t("settings.kbps")}</span>
                </div>
              </Row>
              <Row label={t("settings.autoStart")} sub={t("settings.autoStartSub")}>
                <Toggle checked={settings.autoStart} onChange={(v) => update("autoStart", v)} />
              </Row>
              <Row label={t("settings.notifyComplete")}>
                <Toggle checked={settings.notifyOnComplete} onChange={(v) => update("notifyOnComplete", v)} />
              </Row>
            </SectionCard>
          )}

          {activeSection === "connection" && (
            <SectionCard title={t("settings.connection")}>
              <Row label={t("settings.listeningPort")}>
                <input type="number" value={settings.listeningPort}
                  onChange={(e) => update("listeningPort", Number(e.target.value))}
                  className={`w-20 text-end ${inputCls}`}
                />
              </Row>
              <Row label={t("settings.upnp")}>
                <Toggle checked={settings.enableUPnP} onChange={(v) => update("enableUPnP", v)} />
              </Row>
              <Row label={t("settings.dht")} sub={t("settings.dhtSub")}>
                <Toggle checked={settings.enableDHT} onChange={(v) => update("enableDHT", v)} />
              </Row>
              <Row label={t("settings.proxy")}>
                <select
                  value={settings.proxy}
                  onChange={(e) => update("proxy", e.target.value as ProxyType)}
                  className={inputCls}
                >
                  {["None", "SOCKS5", "HTTP"].map((p) => <option key={p}>{p}</option>)}
                </select>
              </Row>
            </SectionCard>
          )}

          {activeSection === "privacy" && (
            <SectionCard title={t("settings.privacy")}>
              <Row label={t("settings.encryption")} sub={t("settings.encryptionSub")}>
                <Toggle checked={settings.enableEncryption} onChange={(v) => update("enableEncryption", v)} />
              </Row>
              <Row label={t("settings.anonymous")} sub={t("settings.anonymousSub")}>
                <Toggle checked={settings.anonymousMode} onChange={(v) => update("anonymousMode", v)} />
              </Row>
            </SectionCard>
          )}

          {activeSection === "advanced" && (
            <SectionCard title={t("settings.advanced")}>
              <Row label={t("settings.maxConnections")}>
                <input type="number" min={1} value={settings.maxConnections}
                  onChange={(e) => update("maxConnections", Number(e.target.value))}
                  className={`w-20 text-end ${inputCls}`}
                />
              </Row>
              <Row label={t("settings.maxPeers")}>
                <input type="number" min={1} value={settings.maxPeersPerTorrent}
                  onChange={(e) => update("maxPeersPerTorrent", Number(e.target.value))}
                  className={`w-20 text-end ${inputCls}`}
                />
              </Row>
            </SectionCard>
          )}
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 px-5 py-3 bg-white dark:bg-stone-800 border-t border-blue-100 dark:border-blue-900 shrink-0">
        <Button text={t("settings.cancel")} action={onClose} />
        <button
          type="button"
          onClick={handleSave}
          className={`text-sm px-4 py-2 rounded-full text-white font-medium transition-colors ${
            saved ? "bg-green-500" : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          {saved ? t("settings.saved") : t("settings.saveChanges")}
        </button>
      </div>
    </Modal>
  );
};

const DangerZone = ({ onReset }: { onReset: () => void }) => {
  const { t } = useLanguage();
  const { torrents, clearCompleted } = useTorrents();
  const { showToast } = useUI();
  const hasCompleted = torrents.some((torrent) => torrent.status === "Completed");

  return (
    <SectionCard title={t("settings.dangerZone")}>
      <Row label={t("settings.clearCompleted")} sub={t("settings.clearCompletedSub")}>
        <Button
          text={t("settings.clear")}
          action={() => { clearCompleted(); showToast(t("settings.clearedToast")); }}
          variant="danger"
          disabled={!hasCompleted}
        />
      </Row>
      <Row label={t("settings.resetAll")} sub={t("settings.resetAllSub")}>
        <Button text={t("settings.reset")} action={onReset} variant="danger" />
      </Row>
    </SectionCard>
  );
};
