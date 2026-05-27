import React, { useState } from "react";
import {
  Settings as SettingsIcon,
  Download,
  Wifi,
  Lock,
  SlidersHorizontal,
  Palette,
  X,
} from "lucide-react";
import { useLanguage, type Language } from "../../context/LanguageContext";
import Button from "../UI/Button";

type Section = "general" | "appearance" | "downloads" | "connection" | "privacy" | "advanced";

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
  const { language, setLanguage, t } = useLanguage();
  const [activeSection, setActiveSection] = useState<Section>("general");
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [saved, setSaved] = useState(false);

  const navItems: { id: Section; label: string; icon: React.ReactNode }[] = [
    { id: "general",    label: t("settings.general"),    icon: <SettingsIcon size={15} /> },
    { id: "appearance", label: t("settings.appearance"), icon: <Palette size={15} /> },
    { id: "downloads",  label: t("settings.downloads"),  icon: <Download size={15} /> },
    { id: "connection", label: t("settings.connection"), icon: <Wifi size={15} /> },
    { id: "privacy",    label: t("settings.privacy"),    icon: <Lock size={15} /> },
    { id: "advanced",   label: t("settings.advanced"),   icon: <SlidersHorizontal size={15} /> },
  ];

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => { setSaved(false); onClose(); }, 1200);
  };

  const handleReset = () => {
    if (confirm(t("settings.resetConfirm"))) setSettings(defaultSettings);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-stone-50 dark:bg-stone-900 rounded-2xl shadow-2xl w-[700px] h-[80vh] flex flex-col overflow-hidden">

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

          <div className="w-44 shrink-0 bg-white dark:bg-stone-800 border-r border-blue-100 dark:border-blue-900 flex flex-col py-2">
            {navItems.map(({ id, label, icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setActiveSection(id)}
                className={`flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium transition-colors text-left
                  ${activeSection === id
                    ? "bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border-r-2 border-blue-600"
                    : "text-stone-500 dark:text-stone-400 hover:bg-stone-50 dark:hover:bg-stone-700/50 hover:text-stone-700 dark:hover:text-stone-200"
                  }`}
              >
                {icon}
                {label}
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

            {activeSection === "appearance" && (
              <SectionCard title={t("settings.appearance")}>
                <Row label={t("settings.language")}>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value as Language)}
                    className={inputCls}
                  >
                    {["English", "Hebrew", "Spanish", "French", "German"].map((l) => <option key={l}>{l}</option>)}
                  </select>
                </Row>
              </SectionCard>
            )}

            {activeSection === "downloads" && (
              <SectionCard title={t("settings.downloads")}> 
                <Row label={t("settings.saveLocation")} sub={settings.savePath}>
                  <Button text={t("settings.browse")} action={() => {}} />
                </Row>
                <Row label={t("settings.downloadLimit")} sub={t("settings.unlimited")}>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      min={0}
                      value={settings.downloadLimit}
                      onChange={(e) => update("downloadLimit", Number(e.target.value))}
                      className={`w-20 text-right ${inputCls}`}
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
                      className={`w-20 text-right ${inputCls}`}
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
                    className={`w-20 text-right ${inputCls}`}
                  />
                </Row>
                <Row label={t("settings.upnp")}>
                  <Toggle checked={settings.enableUPnP} onChange={(v) => update("enableUPnP", v)} />
                </Row>
                <Row label={t("settings.dht")} sub={t("settings.dhtSub")}>
                  <Toggle checked={settings.enableDHT} onChange={(v) => update("enableDHT", v)} />
                </Row>
                <Row label={t("settings.proxy")}>
                  <select value={settings.proxy} onChange={(e) => update("proxy", e.target.value)} className={inputCls}>
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
                    className={`w-20 text-right ${inputCls}`}
                  />
                </Row>
                <Row label={t("settings.maxPeers")}>
                  <input type="number" min={1} value={settings.maxPeersPerTorrent}
                    onChange={(e) => update("maxPeersPerTorrent", Number(e.target.value))}
                    className={`w-20 text-right ${inputCls}`}
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
      </div>
    </div>
  );
};

const DangerZone = ({ onReset }: { onReset: () => void }) => {
  const { t } = useLanguage();
  return (
    <SectionCard title={t("settings.dangerZone")}>
      <Row label={t("settings.clearCompleted")} sub={t("settings.clearCompletedSub")}>
        <Button text={t("settings.clear")} action={() => {}} variant="danger" />
      </Row>
      <Row label={t("settings.resetAll")} sub={t("settings.resetAllSub")}>
        <Button text={t("settings.reset")} action={onReset} variant="danger" />
      </Row>
    </SectionCard>
  );
};
