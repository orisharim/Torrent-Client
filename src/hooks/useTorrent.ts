import {useEffect, useRef, useState} from "react";
import { BASE_URL } from "../services/backend";

const POLL_INTERVAL_MS = 500;

interface Torrent {
    torrentFilePath : string;
    timestamp : number;
    download_speed : number;
    downloaded_pieces : number;
    total_pieces : number;
    is_downloading : boolean;
    is_seeding : boolean;
    connected_peers : number;
}

const jsonHeaders = {"Content-Type" : "application/json"};

const parseJson = async <T>(response : Response) : Promise<T> => {
    if (!response.ok) throw new Error(`Request failed: ${response.status}`);
    return response.json();
}

const getAllTorrentPaths = async() : Promise<string[]> => {
    const response = await fetch(`${BASE_URL}/torrents` , {
        method : "GET",
        headers : jsonHeaders
    });
    const list = await parseJson<{torrentFilePath : string}[]>(response);
    return list.map((t) => t.torrentFilePath);
}

const getTorrentStatus = async(torrentFilePath : string) : Promise<Torrent> => {
    const response = await fetch(`${BASE_URL}/torrents/status?${new URLSearchParams({torrentFilePath})}` , {
        method : "GET",
        headers : jsonHeaders
    });
    const status = await parseJson<Omit<Torrent, "torrentFilePath">>(response);
    return {torrentFilePath , ...status};
}

const getAllTorrents = async() : Promise<Torrent[]> => {
    const paths = await getAllTorrentPaths();
    return Promise.all(paths.map((path) => getTorrentStatus(path)));
}

const postAddTorrent = async(torrentFilePath : string, downloadPath : string) : Promise<boolean> => {
    const response = await fetch(`${BASE_URL}/torrents/add` , {
        method : "POST",
        headers : jsonHeaders,
        body : JSON.stringify({torrentFilePath , downloadPath})
    });
    return response.ok;
}

// assumes "id" == torrentFilePath, the only identifier the status endpoints use
const postPauseTorrent = async(torrentFilePath : string) : Promise<boolean> => {
    const response = await fetch(`${BASE_URL}/torrents/pause` , {
        method : "POST",
        headers : jsonHeaders,
        body : JSON.stringify({id : torrentFilePath})
    });
    return response.ok;
}

const postResumeTorrent = async(torrentFilePath : string) : Promise<boolean> => {
    const response = await fetch(`${BASE_URL}/torrents/resume` , {
        method : "POST",
        headers : jsonHeaders,
        body : JSON.stringify({id : torrentFilePath})
    });
    return response.ok;
}

const postDeleteTorrent = async(torrentFilePath : string) : Promise<boolean> => {
    const response = await fetch(`${BASE_URL}/torrents/delete` , {
        method : "POST",
        headers : jsonHeaders,
        body : JSON.stringify({id : torrentFilePath})
    });
    return response.ok;
}

const changeTorrentStatus = async(torrentFilePath : string, is_downloading : boolean, is_seeding : boolean) : Promise<boolean> => {
    const response = await fetch(`${BASE_URL}/torrents/change-status` , {
        method : "POST",
        headers : jsonHeaders,
        body : JSON.stringify({torrentFilePath , is_downloading , is_seeding})
    });
    return response.ok;
}

export function useTorrent() {
    const [torrents , setTorrents] = useState<Torrent[]>([]);
    const [loading , setLoading] = useState(true);
    const torrentsRef = useRef<Torrent[]>([]);

    useEffect(() => {
        torrentsRef.current = torrents;
    }, [torrents]);

    // initial load, most-recently-added-on-top order starts as whatever the server returns
    useEffect(() => {
        getAllTorrents().then((list) => {
            setTorrents(list);
            setLoading(false);
        });
    }, []);

    // every 0.5s, refresh progress for torrents that are actively downloading
    useEffect(() => {
        const interval = setInterval(() => {
            torrentsRef.current
                .filter((t) => t.is_downloading)
                .forEach((t) => {
                    getTorrentStatus(t.torrentFilePath).then((updated) => {
                        setTorrents((prev) => prev.map((p) => p.torrentFilePath === updated.torrentFilePath ? updated : p));
                    });
                });
        }, POLL_INTERVAL_MS);
        return () => clearInterval(interval);
    }, []);

    const addTorrent = async(torrentFilePath : string, downloadPath : string) : Promise<void> => {
        const ok = await postAddTorrent(torrentFilePath, downloadPath);
        if (!ok) return;
        const status = await getTorrentStatus(torrentFilePath);
        setTorrents((prev) => [status , ...prev.filter((t) => t.torrentFilePath !== torrentFilePath)]);
    }

    // optimistic: flips is_downloading immediately, reverts if the server doesn't confirm
    const pauseTorrent = async(torrentFilePath : string) : Promise<void> => {
        setTorrents((prev) => prev.map((t) => t.torrentFilePath === torrentFilePath ? {...t , is_downloading : false} : t));
        const ok = await postPauseTorrent(torrentFilePath);
        if (!ok) {
            setTorrents((prev) => prev.map((t) => t.torrentFilePath === torrentFilePath ? {...t , is_downloading : true} : t));
        }
    }

    const resumeTorrent = async(torrentFilePath : string) : Promise<void> => {
        setTorrents((prev) => prev.map((t) => t.torrentFilePath === torrentFilePath ? {...t , is_downloading : true} : t));
        const ok = await postResumeTorrent(torrentFilePath);
        if (!ok) {
            setTorrents((prev) => prev.map((t) => t.torrentFilePath === torrentFilePath ? {...t , is_downloading : false} : t));
        }
    }

    const deleteTorrent = async(torrentFilePath : string) : Promise<void> => {
        const ok = await postDeleteTorrent(torrentFilePath);
        if (ok) {
            setTorrents((prev) => prev.filter((t) => t.torrentFilePath !== torrentFilePath));
        }
    }

    // optimistic: same as pause/resume, but for setting is_downloading + is_seeding together
    const setStatus = async(torrentFilePath : string, is_downloading : boolean, is_seeding : boolean) : Promise<void> => {
        setTorrents((prev) => prev.map((t) => t.torrentFilePath === torrentFilePath ? {...t , is_downloading , is_seeding} : t));
        const ok = await changeTorrentStatus(torrentFilePath, is_downloading, is_seeding);
        if (!ok) {
            getTorrentStatus(torrentFilePath).then((fresh) => {
                setTorrents((prev) => prev.map((t) => t.torrentFilePath === torrentFilePath ? fresh : t));
            });
        }
    }

    return {
        torrents, loading,
        addTorrent, pauseTorrent, resumeTorrent, deleteTorrent, setStatus,
        changeTorrentStatus, getAllTorrentPaths, getTorrentStatus, getAllTorrents
    }
}
