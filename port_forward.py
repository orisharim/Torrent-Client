import asyncio
import socket
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.search import async_search
from async_upnp_client.aiohttp import AiohttpRequester

def _get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

async def forward_port(port: int, protocol: str = "TCP", description: str = "Torrent Client"):
    print("[*] Searching for Internet Gateway Device...")
    
    # target only the internet gateway device
    target_st = "urn:schemas-upnp-org:device:InternetGatewayDevice:1"
    
    igd_location = None
    async def on_response(data):
        nonlocal igd_location
        if "location" in data and not igd_location:
            igd_location = data["location"]

    await async_search(async_callback=on_response, search_target=target_st, timeout=4)

    if not igd_location:
        raise RuntimeError("No UPnP Internet Gateway Device responded.")

    print(f"Found gateway descriptor at: {igd_location}")

    requester = AiohttpRequester()
    factory = UpnpFactory(requester)
    device = await factory.async_create_device(igd_location)

    service = None
    for s_type in ("urn:schemas-upnp-org:service:WANIPConnection:1", 
                    "urn:schemas-upnp-org:service:WANPPPConnection:1"):
        service = device.find_service(s_type)
        if service:
            break

    if not service:
        for s in device.services.values():
            if "WANIPConnection" in s.service_type or "WANPPPConnection" in s.service_type:
                service = s
                break

    if not service:
        raise RuntimeError("Could not find WANIPConnection or WANPPPConnection service on router.")

    local_ip = _get_local_ip()

    action = service.action("AddPortMapping")
    await action.async_call(
        NewRemoteHost="",
        NewExternalPort=port,
        NewProtocol=protocol.upper(),
        NewInternalPort=port,
        NewInternalClient=local_ip,
        NewEnabled=True,
        NewPortMappingDescription=description,
        NewLeaseDuration=0,
    )
    print(f"Forwarded {protocol.upper()} {port} -> {local_ip}:{port}")
    return service

async def delete_port(service, port: int, protocol: str = "TCP"):
    action = service.action("DeletePortMapping")
    await action.async_call(
        NewRemoteHost="",
        NewExternalPort=port,
        NewProtocol=protocol.upper(),
    )
    print(f"[-] Deleted port mapping for {protocol.upper()} {port}")
