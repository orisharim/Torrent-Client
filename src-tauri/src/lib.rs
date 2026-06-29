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
    health: String,
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
struct FeedItem {
    id: u32,
    source: String,
    name: String,
    size: String,
    date: String,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct FeedStats {
    new_today: u32,
    downloads_ready: u32,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct Device {
    id: u32,
    name: String,
    #[serde(rename = "type")]
    device_type: String,
    status: String,
    last_seen: String,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct AppSettings {
    start_on_startup: bool,
    minimize_to_tray: bool,
    language: String,
    save_path: String,
    download_limit: u32,
    upload_limit: u32,
    auto_start: bool,
    notify_on_complete: bool,
    listening_port: u32,
    #[serde(rename = "enableUPnP")]
    enable_upnp: bool,
    #[serde(rename = "enableDHT")]
    enable_dht: bool,
    proxy: String,
    enable_encryption: bool,
    anonymous_mode: bool,
    max_connections: u32,
    max_peers_per_torrent: u32,
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
        start_on_startup: true,
        minimize_to_tray: true,
        language: "English".to_string(),
        save_path: "/Users/user/Downloads".to_string(),
        download_limit: 0,
        upload_limit: 50,
        auto_start: true,
        notify_on_complete: true,
        listening_port: 6881,
        enable_upnp: true,
        enable_dht: true,
        proxy: "None".to_string(),
        enable_encryption: true,
        anonymous_mode: false,
        max_connections: 200,
        max_peers_per_torrent: 50,
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
    Torrent { id: 0, name, size: 0.0, progress: 0.0, speed: 0.0, status: "Downloading".to_string(), health: "Good".to_string() }
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

// ── Feed Commands ─────────────────────────────────────────────────────────────

#[tauri::command]
fn get_feeds() -> Vec<FeedItem> {
    // TODO: return feed items from your RSS manager
    vec![]
}

#[tauri::command]
fn get_feed_stats() -> FeedStats {
    // TODO: return feed statistics from your RSS manager
    FeedStats { new_today: 0, downloads_ready: 0 }
}

#[tauri::command]
fn add_feed(url: String) {
    log::info!("add_feed: {}", url);
    // TODO: register feed URL in your RSS manager
}

#[tauri::command]
fn refresh_feeds() -> Vec<FeedItem> {
    log::info!("refresh_feeds");
    // TODO: fetch all feeds and return updated items
    vec![]
}

#[tauri::command]
fn download_feed_item(id: u32) {
    log::info!("download_feed_item: {}", id);
    // TODO: trigger download for the feed item
}

// ── Device Commands ──────────────────────────────────────────────────────────

#[tauri::command]
fn get_devices() -> Vec<Device> {
    // TODO: return connected devices from your device manager
    vec![]
}

#[tauri::command]
fn disconnect_device(id: u32) {
    log::info!("disconnect_device: {}", id);
    // TODO: disconnect the device
}

// ── Settings Commands ────────────────────────────────────────────────────────

#[tauri::command]
fn get_settings() -> AppSettings {
    // TODO: load from a config file or database (e.g. with tauri-plugin-store)
    default_settings()
}

#[tauri::command]
fn save_settings(settings: AppSettings) {
    log::info!("save_settings: language={}", settings.language);
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
            get_feeds,
            get_feed_stats,
            add_feed,
            refresh_feeds,
            download_feed_item,
            get_devices,
            disconnect_device,
            get_settings,
            save_settings,
            reset_settings,
            get_home_stats,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
