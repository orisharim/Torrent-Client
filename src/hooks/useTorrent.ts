import { API_BASE, encodePath } from "../services/backend";
import { useEffect, useRef, useState } from "react";
import { getStartDownloadingOnAdd } from "../services/preferences";

const POLL_INTERVAL_MS = 500; 

interface Torrent { 
    torrentFilePath: string;      
    info_hash: string;            
    download_path: string;        
    timestamp: number;
    download_speed: number;
    downloaded_pieces: number;
    total_pieces: number;
    total_size: number;
    is_downloading: boolean;
    is_seeding: boolean;
    connected_peers: number;
}


// backend doesn't report a torrent name/file path, so remember the .torrent path at add time
const NAMES_KEY = "app.torrentFilePaths";
const loadNames = (): Record<string, string> => {
    try { return JSON.parse(localStorage.getItem(NAMES_KEY) ?? "{}"); } catch { return {}; }
}
const saveName = (info_hash: string, torrentFilePath: string) => {
    try { localStorage.setItem(NAMES_KEY, JSON.stringify({ ...loadNames(), [info_hash]: torrentFilePath })); } catch { /* ignore */ }
}

const jsonHeaders = {"Content-Type" : "application/json"};


const parseJson = async <T>(response : Response) : Promise<T> => {
    if(!response.ok){
        const error = await response.json().catch(() => ({}));
        throw new Error(`Request failed: ${response.status} - ${error.message || ''}`);
    }
    return response.json();
}



const getTorrentStatus = async(info_hash : string, download_path : string) : Promise<Torrent> => {
    const response = await fetch(`${API_BASE}/torrents/${info_hash}/${encodePath(download_path)}`, {
        method : "GET",
        headers : jsonHeaders
    });

    const data = await parseJson<{
        message_status: string,
        timestamp: number,
        is_downloading: boolean,
        is_seeding: boolean,
        download_speed: number,
        downloaded_pieces: number,
        total_pieces: number,
        total_size: number,
        connected_peers: number
    }>(response);

   return {torrentFilePath: loadNames()[info_hash] ?? info_hash.slice(0, 8) , info_hash , download_path, ...data}
}


const getAllTorrents = async() : Promise<Torrent[]> => {
    const response = await fetch(`${API_BASE}/torrents`, {
        method : "GET",
        headers : jsonHeaders
    });

    const data = await parseJson<{
        message_status : string,
        timestamp : number,
        torrents : Array<{info_hash: string , download_path: string}>
    }>(response)

    const torrents = await Promise.all(
        data.torrents.map(t => getTorrentStatus(t.info_hash , t.download_path))
    );
    return torrents;
}


const postAddTorrent = async(
    torrentFilePath : string, 
    downloadPath : string,
    settings?: any) : Promise<{info_hash : string}> => {
        const response = await fetch(`${API_BASE}/torrents` , {
            method : "POST",
            headers : jsonHeaders,
            body : JSON.stringify({
                file_path: torrentFilePath,
                download_path : downloadPath,
                max_connections : settings?.max_connections,
                download_speed_limit: settings?.download_speed_limit,
                upload_speed_limit : settings?.upload_speed_limit,
                tracker_amount : settings?.tracker_amount 
            })
        });
        await parseJson<{status : string}>(response);
        
        const allTorrents = await getAllTorrents();
        const added = allTorrents.find(t => t.download_path === downloadPath)

        if(!added){
            throw new Error("Failed to find added torrent")
        }
        return{info_hash : added.info_hash};
}


const postDeleteTorrent = async(info_hash : string, download_path: string): Promise<boolean> => {
    const response = await fetch(`${API_BASE}/torrents/${info_hash}/${encodePath((download_path))}` , 
    {
        method : "DELETE",
        headers : jsonHeaders
    });
    return response.ok;
}


const changeTorrentStatus = async(
        info_hash : string,
        download_path : string,
        is_downloading: boolean,
        is_seeding : boolean,
        ) : Promise<boolean> => { 
    const response = await fetch(
        `${API_BASE}/torrents/status/${info_hash}/${encodePath(download_path)}`, {
            method : "PUT", 
            headers : jsonHeaders,
            body : JSON.stringify({
                is_downloading,
                is_seeding
            })
        }
    );
    return response.ok;
}


//hook useTorrent

export function useTorrent(){
    const[torrents , setTorrents] = useState<Torrent[]>([]);
    const[loading , setLoading] = useState(true);
    const torrentRef = useRef<Torrent[]>([]);

    useEffect(() => {
        torrentRef.current = torrents;
    }, [torrents]);


    //intial load
    useEffect(() => {
        getAllTorrents().then((list) => {
            setTorrents(list);
            setLoading(false);
        }).catch(err => {
            console.error("Faild to load torrent: " , err);
            setLoading(false);
        });
    } , []);

    // torrents with a status change in flight: the backend can take a long time to apply it
    // (resume re-validates every piece on disk), so polling must not overwrite the optimistic state
    const pendingRef = useRef<Set<string>>(new Set());
    // latest request made while one was in flight; sent once the current one finishes
    const queuedRef = useRef<Map<string, { download_path: string, is_downloading: boolean, is_seeding: boolean }>>(new Map());

    //pull for update on downloading torrent 
    useEffect(() => {
        const interval = setInterval(() => {
            torrentRef.current
            .filter((t) => t.is_downloading && !pendingRef.current.has(t.info_hash))
            .forEach((t) => {
                getTorrentStatus(t.info_hash ,t.download_path).then((updated) => {
                    if (pendingRef.current.has(updated.info_hash)) return;
                    setTorrents((prev) => 
                    prev.map((p) => p.info_hash === updated.info_hash ? updated : p));
                }).catch(() => {});
            });
        }, POLL_INTERVAL_MS);
        return () => clearInterval(interval); 
    }, []);


    const addTorrent = async(torrentFilePath : string , downloadPath : string) : Promise<void> => {
        const result = await postAddTorrent(torrentFilePath, downloadPath);
        saveName(result.info_hash, torrentFilePath);
        const status = await getTorrentStatus(result.info_hash, downloadPath);
        setTorrents((prev) => [status , ...prev.filter((t) => t.info_hash !== result.info_hash)]);
        if (getStartDownloadingOnAdd()) {
            void applyStatus(result.info_hash, downloadPath, true, false);
        }
    }

    // optimistic update, then sync with the backend's real state once the request settles
    const applyStatus = async(info_hash : string, download_path : string, is_downloading : boolean, is_seeding : boolean) : Promise<void> => {
        setTorrents((prev) => prev.map((t) =>
            t.info_hash === info_hash ? {...t, is_downloading, is_seeding} : t));
        if (pendingRef.current.has(info_hash)) {
            queuedRef.current.set(info_hash, { download_path, is_downloading, is_seeding });
            return;
        }
        pendingRef.current.add(info_hash);
        try {
            await changeTorrentStatus(info_hash, download_path, is_downloading, is_seeding);
        } catch (err) {
            console.error("Failed to change torrent status: ", err);
        } finally {
            pendingRef.current.delete(info_hash);
        }
        const next = queuedRef.current.get(info_hash);
        if (next) {
            queuedRef.current.delete(info_hash);
            return applyStatus(info_hash, next.download_path, next.is_downloading, next.is_seeding);
        }
        try {
            const fresh = await getTorrentStatus(info_hash, download_path);
            setTorrents((prev) => prev.map((t) => t.info_hash === info_hash ? fresh : t));
        } catch (err) {
            console.error("Failed to refresh torrent status: ", err);
        }
    }

    const currentSeeding = (info_hash : string) => torrentRef.current.find(t => t.info_hash === info_hash)?.is_seeding || false;

    const pauseTorrent = (info_hash : string, download_path : string) : Promise<void> =>
        applyStatus(info_hash, download_path, false, currentSeeding(info_hash));

    const resumeTorrent = (info_hash : string, download_path : string) : Promise<void> =>
        applyStatus(info_hash, download_path, true, currentSeeding(info_hash));

    const deleteTorrent = async(info_hash : string , download_path: string) : Promise<void> =>{
        const ok = await postDeleteTorrent(info_hash,download_path); 

        if(ok) {
            setTorrents((prev) => prev.filter((t) => t.info_hash !== info_hash));
        }
    }

    const setStatus = (info_hash : string ,download_path : string , is_downloading: boolean, is_seeding: boolean) : Promise<void> =>
        applyStatus(info_hash, download_path, is_downloading, is_seeding);

    return {
        torrents, 
        loading,
        addTorrent, 
        pauseTorrent, 
        resumeTorrent, 
        deleteTorrent, 
        setStatus,
        changeTorrentStatus, 
        getAllTorrents, 
        getTorrentStatus}

    

}


//TODO: is seeding define in code