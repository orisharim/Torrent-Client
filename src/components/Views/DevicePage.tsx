import React from "react";
import { Monitor, Smartphone, Tablet, Power, Wifi, WifiOff } from "lucide-react";
import Button from "../UI/Button";
import DataTable, { tableRowCls, thCls } from "../UI/DataTable";
import IconBox from "../UI/IconBox";
import PageHeader from "../UI/PageHeader";
import { useLanguage } from "../../context/LanguageContext";

const devices = [
  { id: 1, name: "My PC",     type: "Desktop", status: "Online",  lastSeen: "Now"         },
  { id: 2, name: "iPhone 13", type: "Phone",   status: "Offline", lastSeen: "2 hours ago" },
  { id: 3, name: "Tablet",    type: "Tablet",  status: "Online",  lastSeen: "5 min ago"   },
];

const getIcon = (type: string) => {
  if (type === "Desktop") return <Monitor className="w-5 h-5" />;
  if (type === "Phone") return <Smartphone className="w-5 h-5" />;
  return <Tablet className="w-5 h-5" />;
};

export const DevicePage = () => {
  const { t } = useLanguage();

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <PageHeader title={t("devices.title")} subtitle={t("devices.subtitle")} />

      <DataTable title={t("devices.connected")} count={devices.length} countLabel={t("common.devices")}>
        <thead className="bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900">
          <tr className="text-left text-stone-500 dark:text-stone-400">
            <th className={thCls}>{t("devices.device")}</th>
            <th className={thCls}>{t("devices.type")}</th>
            <th className={thCls}>{t("devices.status")}</th>
            <th className={thCls}>{t("devices.lastSeen")}</th>
            <th className={`${thCls} text-right`}>{t("devices.action")}</th>
          </tr>
        </thead>
        <tbody>
          {devices.map((device, index) => {
            const isOnline = device.status === "Online";
            return (
              <tr key={device.id} className={tableRowCls(index)}>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-3">
                    <IconBox icon={getIcon(device.type)} />
                    <div>
                      <div className="font-medium text-stone-800 dark:text-stone-100">{device.name}</div>
                      <div className="text-xs text-stone-400 dark:text-stone-500">ID #{device.id}</div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4 text-stone-600 dark:text-stone-300">{device.type}</td>
                <td className="px-4 py-4">
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                    isOnline
                      ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
                      : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400"
                  }`}>
                    {isOnline ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
                    {t(isOnline ? "devices.online" : "devices.offline")}
                  </span>
                </td>
                <td className="px-4 py-4 text-stone-600 dark:text-stone-300">{device.lastSeen}</td>
                <td className="px-4 py-4 text-right">
                  <Button
                    text={t("devices.disconnect")}
                    icon={<Power className="w-4 h-4" />}
                    action={() => {}}
                    variant="danger"
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </DataTable>
    </div>
  );
};
