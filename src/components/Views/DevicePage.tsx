import React from "react";
import { Monitor, Smartphone, Tablet, Power, Wifi, WifiOff } from "lucide-react";

const devices = [
  { id: 1, name: "My PC", type: "Desktop", status: "Online", lastSeen: "Now" },
  { id: 2, name: "iPhone 13", type: "Phone", status: "Offline", lastSeen: "2 hours ago" },
  { id: 3, name: "Tablet", type: "Tablet", status: "Online", lastSeen: "5 min ago" },
];

const getIcon = (type: string) => {
  if (type === "Desktop") return <Monitor className="w-5 h-5 text-blue-600" />;
  if (type === "Phone") return <Smartphone className="w-5 h-5 text-blue-600" />;
  return <Tablet className="w-5 h-5 text-blue-600" />;
};

export const DevicePage = () => {
  return (
    <div className="w-full min-h-screen bg-stone-50 p-6">
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-stone-800">Devices</h1>
        <p className="text-sm text-stone-500 mt-1">
          Manage connected devices and active sessions
        </p>
      </div>

      <div className="w-full border border-blue-200 rounded-xl overflow-hidden shadow-sm bg-white">
        <div className="px-4 py-3 border-b border-blue-100 bg-blue-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-blue-800">
            Connected Devices
          </h2>

          <span className="text-xs text-stone-500">
            {devices.length} devices
          </span>
        </div>

        <table className="w-full text-sm">
          <thead className="bg-white border-b border-blue-100">
            <tr className="text-left text-stone-500">
              <th className="px-4 py-3 font-medium">Device</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Last Seen</th>
              <th className="px-4 py-3 font-medium text-right">Action</th>
            </tr>
          </thead>

          <tbody>
            {devices.map((device, index) => {
              const isOnline = device.status === "Online";

              return (
                <tr
                  key={device.id}
                  className={`border-b border-blue-50 last:border-b-0 transition ${
                    index % 2 === 1 ? "bg-blue-50/40" : "bg-white"
                  } hover:bg-blue-50`}
                >
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 rounded-lg bg-blue-100 flex items-center justify-center">
                        {getIcon(device.type)}
                      </div>

                      <div>
                        <div className="font-medium text-stone-800">
                          {device.name}
                        </div>
                        <div className="text-xs text-stone-400">
                          ID #{device.id}
                        </div>
                      </div>
                    </div>
                  </td>

                  <td className="px-4 py-4 text-stone-600">
                    {device.type}
                  </td>

                  <td className="px-4 py-4">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                        isOnline
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {isOnline ? (
                        <Wifi className="w-3.5 h-3.5" />
                      ) : (
                        <WifiOff className="w-3.5 h-3.5" />
                      )}
                      {device.status}
                    </span>
                  </td>

                  <td className="px-4 py-4 text-stone-600">
                    {device.lastSeen}
                  </td>

                  <td className="px-4 py-4 text-right">
                    <button
                      type="button"
                      className="inline-flex items-center gap-2 rounded-md border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 transition"
                    >
                      <Power className="w-4 h-4" />
                      Disconnect
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};