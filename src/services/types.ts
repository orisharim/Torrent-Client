export type TorrentStatus = "Downloading" | "Paused" | "Completed" | "Seeding";

export type SearchResult = {
  id: number;
  name: string;
  size: number; 
  seeds: number;
  peers: number;
  source: string;
  magnet: string;
};


// golbal setting only (flask has 3 fields)
export type GlobalSettings = {
  enable_receiving : boolean;
  enable_dht : boolean;
  enable_port_downloading : boolean;
};

//per torrent settings (flask has 4 fields)
export type TorrentSettings = {
  max_connections : number;
  download_speed_limit : number;
  upload_speed_limit : number;
  tracker_amount : number; 
}

//torrent type with parameters
export type Torrent = {
  torrent_file_path : string;
  info_hash : string;
  download_path : string;
  timestamp : number;
  download_speed : number;
  downloaded_pieces : number;
  total_pieces : number;
  is_downloading : boolean;
  is_seeding : boolean; 
  connected_peers : number;
}


