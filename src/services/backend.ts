
const baseUrl = ((import.meta.env.VITE_APP_BASE_URL as string | undefined) ?? "http://localhost:5000").replace(/\/$/, "");

//API endpoint
export const BASE_URL = baseUrl; 
export const API_BASE = `${baseUrl}/api`;

//helper for path encoding 
export const encodePath = (path : string) : string => {
    return encodeURIComponent(encodeURIComponent(path))
}

// The backend runs in WSL, so Windows paths (C:\foo\bar) must become /mnt/c/foo/bar
export const toBackendPath = (path : string) : string => {
    const m = /^([a-zA-Z]):[\\/](.*)$/.exec(path);
    if (!m) return path;
    return `/mnt/${m[1].toLowerCase()}/${m[2].replaceAll("\\", "/")}`;
}
