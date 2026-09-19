import { useEffect, useState } from "react";


//TODO put real url (temp)
const URL = "http://localhost:8080"

interface Settings{
    max_connection : number;
    download_speed : number;
    upload_speed_limit : number;
    tracker_amount : number;
    enable_receiving : boolean;
    enable_dht : boolean;
    enable_port_downloading : boolean;
}

export function useSettings() {
    const [settings , setSettings] = useState<Settings>();

    const sendSettings = async() : Promise<Settings> => {
        const response = await fetch(URL , {
            method : "GET",
            headers :{
                "Content-Type" : "application/json"
            }
        });

        return response.json();
    }

    useEffect(() => {
        sendSettings().then(setSettings);
    }, []);

    return { settings, sendSettings };
}
