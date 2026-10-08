import { API_BASE, encodePath } from "../services/backend";
import { useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 500; 

interface Torrent { 
    torrentFilePath: string;      
    info_hash: string;            
    download_path: string;        
    timestamp: number;
    download_speed: number;
    downloaded_pieces: number;
    total_pieces: number;
    is_downloading: boolean;
    is_seeding: boolean;
    connected_peers: number;
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
        connected_peers: number
    }>(response);

   return {torrentFilePath: download_path , info_hash , download_path, ...data}
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
        });
    } , []);

    //pull for update on downloading torrent 
    useEffect(() => {
        const interval = setInterval(() => {
            torrentRef.current
            .filter((t) => t.is_downloading)
            .forEach((t) => {
                getTorrentStatus(t.info_hash ,t.download_path).then((updated) => {
                    setTorrents((prev) => 
                    prev.map((p) => p.info_hash === updated.info_hash ? updated : p));
                });
            });
        }, POLL_INTERVAL_MS);
        return () => clearInterval(interval); 
    }, []);


    const addTorrent = async(torrentFilePath : string , downloadPath : string) : Promise<void> => {
        const result = await postAddTorrent(torrentFilePath, downloadPath);
        const status = await getTorrentStatus(result.info_hash, downloadPath);
        setTorrents((prev) => [status , ...prev.filter((t) => t.info_hash !== result.info_hash)]);
    }

    const pauseTorrent = async(info_hash :string,download_path :string) : Promise<void> => {
        setTorrents((prev) => prev.map((t) => 
        t.info_hash === info_hash ? {...t , is_downloading : false} : t ));

        const torrent = torrents.find(t => t.info_hash === info_hash);
        const ok = await changeTorrentStatus(info_hash, download_path, false,torrent?.is_seeding || false);
        
        if(!ok){
            setTorrents((prev) => prev.map((t) => 
            t.info_hash === info_hash ? {...t , is_downloading : true} : t));
        }
    }

    const resumeTorrent = async(info_hash : string , download_path : string) : Promise<void> =>{
        setTorrents((prev) => prev.map((t) => 
        t.info_hash === info_hash ? {...t, is_downloading : true} : t));

        const torrent = torrents.find(t => t.info_hash === info_hash);
        const ok = await changeTorrentStatus(info_hash,download_path,true,torrent?.is_seeding || false);

        if(!ok){
            setTorrents((prev) => prev.map((t) => t.info_hash === info_hash ? {...t , is_downloading : false} : t));
        }
    }

    const deleteTorrent = async(info_hash : string , download_path: string) : Promise<void> =>{
        const ok = await postDeleteTorrent(info_hash,download_path); 

        if(ok) {
            setTorrents((prev) => prev.filter((t) => t.info_hash !== info_hash));
        }
    }

    const setStatus = async(info_hash : string ,download_path : string , is_downloading: boolean, is_seeding: boolean) : Promise<void> => {
        setTorrents((prev) => prev.map((t) =>
        t.info_hash === info_hash ? {...t , is_downloading, is_seeding} : t));

        const ok = await changeTorrentStatus(info_hash, download_path , is_downloading, is_seeding);
        if (!ok) {
             getTorrentStatus(info_hash, download_path).then((fresh) => {
                setTorrents((prev) => prev.map((t) => 
                    t.info_hash === info_hash ? fresh : t
                ));
            });
        }
    }

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