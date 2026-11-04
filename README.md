# Torrent Client — Desktop GUI

Desktop front end for the Torrent Client. Built with **React 19 + TypeScript + Vite + Tailwind**, wrapped as a native app with **Tauri 2**.

All torrent logic lives in the separate **Flask backend**. The GUI talks to it over HTTP. The Rust/Tauri layer only provides the native window and the file/folder picker dialogs.

```
┌──────────────────────────┐   HTTP (fetch)   ┌──────────────────┐
│  React GUI (Tauri window)│ ───────────────▶ │  Flask API :5000 │ ──▶ torrent engine
└──────────────────────────┘                  └──────────────────┘
```

---

## Running

**Requirements:** Node 22+, Rust toolchain (for Tauri), and the Flask backend running on `localhost:5000`.

```bash
npm install
cp .env.example .env        # sets VITE_APP_BASE_URL (default http://localhost:5000/)
npm run tauri dev           # desktop app with hot reload
npm run dev                 # browser only (native file pickers won't work)
npm run tauri build         # production desktop bundle (see Known issues first)
```

Start the Flask backend before launching the GUI, otherwise the torrent list will stay empty.

---

## Project structure

```
src/
├── main.tsx                 Mounts the app inside Theme → Torrent → UI providers
├── App.tsx                  Root layout
├── services/
│   ├── backend.ts           API base URL + encodePath helper
│   ├── preferences.ts       Frontend-only prefs in localStorage ("start downloading on add")
│   └── types.ts             Shared types (TorrentStatus, settings)
├── hooks/
│   ├── useTorrent.ts        All torrent API calls, polling, optimistic status updates
│   └── useSettings.ts       Load/save global settings
├── context/
│   ├── ThemeContext.tsx     Light / Dark / System theme, saved in localStorage
│   ├── TorrentContext.tsx   Maps raw API data to UI rows + batch actions
│   └── UIContext.tsx        Current page, search filter, add dialog, toasts
└── components/
    ├── layout/              Dashboard, Toolbar
    ├── pages/               HomePage (stats), SettingsPage
    ├── torrents/            TorrentTable, AddTorrentDialog
    └── ui/                  Reusable pieces (Button, Modal, Toast, Toggle, DataTable…)
src-tauri/                   Tauri shell (window config, dialog plugin)
```

---

## How it works

### Data flow
1. **Startup:** `useTorrent` calls `GET /api/torrents` for the list of `{info_hash, download_path}`, then fetches each torrent's full status.
2. **Polling:** every **500 ms** it refreshes only the torrents that are currently downloading.
3. **Mapping:** `TorrentContext` turns raw backend data into table rows:
   - `progress = downloaded_pieces / total_pieces × 100`
   - `size` = `total_size` converted to GB
   - `status` is derived from the flags in this order: downloading → seeding → completed (all pieces) → paused
4. **Components** read everything through `useTorrents()` and `useUI()`.

### Status changes (pause / resume / seed)
- The UI updates **immediately** (optimistic), then sends `PUT /api/torrents/status/...`.
- While that request is in flight, the torrent is marked *pending* so polling can't overwrite the new state. This matters because resuming re-validates every piece on disk and can take a while.
- Clicks made during a pending request are **queued**, and the latest one is sent when the current request finishes.
- When everything settles, the real state is fetched from the backend.

### Torrent names
The backend doesn't return a name, so the `.torrent` file path is saved in localStorage (`app.torrentFilePaths`) when you add a torrent. The display name is that file name without `.torrent`.

### Adding a torrent
`AddTorrentDialog` uses Tauri's native dialogs to pick a `.torrent` file and a download folder, then calls `POST /api/torrents`. If "start downloading on add" is enabled (the default), it then resumes the torrent automatically.

---

## Backend API used

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/torrents` | List torrents (`info_hash`, `download_path`) |
| GET | `/api/torrents/{info_hash}/{download_path}` | Status of one torrent |
| POST | `/api/torrents` | Add torrent (`file_path`, `download_path`, optional limits) |
| PUT | `/api/torrents/status/{info_hash}/{download_path}` | Set `is_downloading` / `is_seeding` |
| DELETE | `/api/torrents/{info_hash}/{download_path}` | Remove torrent |
| GET / PUT | `/api/global_settings` | Receiving peers, DHT, port forwarding |

`download_path` is URL-encoded **twice** (`encodePath`), so the backend has to decode it twice.

---

## Known issues / TODO

- **The production build likely fails.** `tauri.conf.json` expects the built frontend in `../build`, but Vite outputs to `dist`. Change it to `"frontendDist": "../dist"`.
- **`src-tauri/src/lib.rs` is unused.** It defines 13 placeholder commands (`get_torrents`, `add_torrent`, …), but the frontend never calls `invoke`. Remove them or move the API into Rust.
- **Magnet links don't work.** The tab exists, but Submit only works for `.torrent` files because the backend has no magnet endpoint.
- **Finding a newly added torrent is fragile.** After `POST /api/torrents`, the GUI finds the new torrent by matching its `download_path`, so two torrents in the same folder can get mixed up. Have the POST return the `info_hash` instead.
- **Browser-only mode can't add torrents.** `npm run dev` runs without Tauri, so the native file pickers fail. Use `npm run tauri dev` for the full app.
- **Leftovers.** `services/types.ts` is out of date (types are redefined in `useTorrent.ts` and `TorrentContext.tsx`), and the Tauri product name has a typo ("bitTurrent").