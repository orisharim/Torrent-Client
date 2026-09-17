use serde::{Deserialize, Serialize};

// ── Data Types ───────────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct Torrent {
    id: u32,
    name: String,
    size: f64,
    progress: f64,
    speed: f64,
    status: String,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct TorrentDetail {
    id: u32,
    files: String,
    info: String,
    peers: String,
    trackers: String,
    speed: String,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TorrentPageStats {
    total_peers: u32,
    current_speed: String,
}

#[derive(Deserialize)]
#[serde(tag = "type", rename_all = "lowercase")]
enum AddTorrentPayload {
    Magnet { uri: String },
    File {
        #[serde(rename = "fileName")]
        file_name: String,
    },
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct AppSettings {
    max_connections: u32,
    download_speed_limit: f64,
    upload_speed_limit: f64,
    tracker_amount: u32,
    enable_receiving_peers: bool,
    enable_dht: bool,
    enable_port_forwarding: bool,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct HomeStats {
    download_speed: String,
    upload_speed: String,
    active_torrents: u32,
    seeding_torrents: u32,
}

// ── Helpers ──────────────────────────────────────────────────────────────────

fn default_settings() -> AppSettings {
    AppSettings {
        max_connections: 50,
        download_speed_limit: 0.0,
        upload_speed_limit: 0.0,
        tracker_amount: 4,
        enable_receiving_peers: true,
        enable_dht: true,
        enable_port_forwarding: true,
    }
}

// ── Torrent Commands ─────────────────────────────────────────────────────────

#[tauri::command]
fn get_torrents() -> Vec<Torrent> {
    // TODO: return torrent list from your torrent engine
    vec![]
}

#[tauri::command]
fn get_torrent_details() -> Vec<TorrentDetail> {
    // TODO: return per-torrent detail (peers, trackers, speed) from your engine
    vec![]
}

#[tauri::command]
fn get_torrent_page_stats() -> TorrentPageStats {
    // TODO: return aggregated stats from your engine
    TorrentPageStats {
        total_peers: 0,
        current_speed: "0 MB/s".to_string(),
    }
}

#[tauri::command]
fn add_torrent(payload: AddTorrentPayload) -> Torrent {
    // TODO: pass to your engine and return the created torrent with a real ID
    let name = match &payload {
        AddTorrentPayload::Magnet { uri } => uri.clone(),
        AddTorrentPayload::File { file_name } => file_name.clone(),
    };
    log::info!("add_torrent: {}", name);
    Torrent { id: 0, name, size: 0.0, progress: 0.0, speed: 0.0, status: "Downloading".to_string() }
}

#[tauri::command]
fn pause_torrent(id: u32) {
    log::info!("pause_torrent: {}", id);
    // TODO: pause torrent in your engine
}

#[tauri::command]
fn resume_torrent(id: u32) {
    log::info!("resume_torrent: {}", id);
    // TODO: resume torrent in your engine
}

#[tauri::command]
fn delete_torrents(ids: Vec<u32>) {
    log::info!("delete_torrents: {:?}", ids);
    // TODO: remove torrents from your engine
}

#[tauri::command]
fn update_torrent_status(id: u32, status: String) {
    log::info!("update_torrent_status: {} -> {}", id, status);
    // TODO: update torrent status in your engine
}

#[tauri::command]
fn clear_completed() {
    log::info!("clear_completed");
    // TODO: remove all completed torrents from your engine
}

// ── Settings Commands ────────────────────────────────────────────────────────

#[tauri::command]
fn get_settings() -> AppSettings {
    // TODO: load from a config file or database (e.g. with tauri-plugin-store)
    default_settings()
}

#[tauri::command]
fn save_settings(settings: AppSettings) {
    log::info!("save_settings: max_connections={}", settings.max_connections);
    // TODO: persist settings to disk
}

#[tauri::command]
fn reset_settings() -> AppSettings {
    // TODO: optionally clear persisted settings before returning defaults
    default_settings()
}

// ── Stats Commands ───────────────────────────────────────────────────────────

#[tauri::command]
fn get_home_stats() -> HomeStats {
    // TODO: return real-time stats from your torrent engine
    HomeStats {
        download_speed: "0 MB/s".to_string(),
        upload_speed: "0 MB/s".to_string(),
        active_torrents: 0,
        seeding_torrents: 0,
    }
}

// ── Entry Point ──────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_torrents,
            get_torrent_details,
            get_torrent_page_stats,
            add_torrent,
            pause_torrent,
            resume_torrent,
            delete_torrents,
            update_torrent_status,
            clear_completed,
            get_settings,
            save_settings,
            reset_settings,
            get_home_stats,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
