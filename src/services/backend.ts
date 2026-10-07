
const baseUrl = (import.meta.env.VITE_APP_BASE_URL as string).replace(/\/$/, "");

//API endpoint
export const BASE_URL = baseUrl; 
export const API_BASE = `${baseUrl}/api`;

//helper for path encoding 
export const encodePath = (path : string) : string => {
    return encodeURIComponent(path)
}