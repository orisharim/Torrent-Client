// Vite only exposes env vars prefixed with VITE_ to client code — see .env / .env.example
export const BASE_URL = (import.meta.env.VITE_APP_BASE_URL as string).replace(/\/$/, "");
