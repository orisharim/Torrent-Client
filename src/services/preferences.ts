// frontend-only preferences (the backend has no field for these), kept in localStorage
const START_ON_ADD_KEY = "app.startDownloadingOnAdd";

export const getStartDownloadingOnAdd = (): boolean => {
  try { return localStorage.getItem(START_ON_ADD_KEY) !== "false"; } catch { return true; }
};

export const setStartDownloadingOnAdd = (value: boolean): void => {
  try { localStorage.setItem(START_ON_ADD_KEY, String(value)); } catch { /* ignore */ }
};
