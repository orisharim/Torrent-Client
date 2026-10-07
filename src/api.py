import torrents_manager
import asyncio
import threading
from urllib.parse import unquote
from flask import Flask, jsonify, request
from flask_cors import CORS
from flasgger import Swagger
import time
import torrent_settings

app = Flask(__name__)
CORS(app) 
Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "Torrent Client API",
        "description": "API for managing torrents and client settings.",
        "version": "1.0.0"
    },
    "basePath": "/",
    "paths": {
        "/api/torrents": {
            "get": {
                "tags": ["Torrents"],
                "summary": "List all torrents",
                "responses": {
                    "200": {"description": "List of torrents"},
                    "500": {"description": "Failed to retrieve torrents"}
                }
            },
            "post": {
                "tags": ["Torrents"],
                "summary": "Add a torrent",
                "consumes": ["application/json"],
                "parameters": [{
                    "in": "body",
                    "name": "torrent",
                    "required": True,
                    "schema": {
                        "type": "object",
                        "required": ["download_path", "file_path"],
                        "properties": {
                            "download_path": {"type": "string"},
                            "file_path": {"type": "string"},
                            "max_connections": {"type": "integer"},
                            "download_speed_limit": {"type": "integer"},
                            "upload_speed_limit": {"type": "integer"},
                            "tracker_amount": {"type": "integer"}
                        }
                    }
                }],
                "responses": {
                    "200": {"description": "Torrent accepted"},
                    "400": {"description": "Invalid request body"},
                    "409": {"description": "Torrent already exists"},
                    "500": {"description": "Failed to add torrent"}
                }
            }
        },
        "/api/torrents/{info_hash}/{download_path}": {
            "get": {
                "tags": ["Torrents"],
                "summary": "Get torrent status",
                "parameters": [{"$ref": "#/parameters/InfoHash"}, {"$ref": "#/parameters/DownloadPath"}],
                "responses": {
                    "200": {"description": "Torrent status"},
                    "404": {"description": "Torrent not found"}
                }
            },
            "delete": {
                "tags": ["Torrents"],
                "summary": "Delete a torrent",
                "parameters": [{"$ref": "#/parameters/InfoHash"}, {"$ref": "#/parameters/DownloadPath"}],
                "responses": {
                    "200": {"description": "Torrent deleted"},
                    "404": {"description": "Torrent not found"},
                    "500": {"description": "Failed to delete torrent"}
                }
            }
        },
        "/api/torrents/status/{info_hash}/{download_path}": {
            "get": {
                "tags": ["Torrents"],
                "summary": "Get torrent status",
                "parameters": [{"$ref": "#/parameters/InfoHash"}, {"$ref": "#/parameters/DownloadPath"}],
                "responses": {
                    "200": {"description": "Torrent status"},
                    "404": {"description": "Torrent not found"}
                }
            },
            "put": {
                "tags": ["Torrents"],
                "summary": "Change torrent status",
                "parameters": [
                    {"$ref": "#/parameters/InfoHash"},
                    {"$ref": "#/parameters/DownloadPath"},
                    {"$ref": "#/parameters/TorrentStatus"}
                ],
                "responses": {
                    "200": {"description": "Status updated"},
                    "400": {"description": "Invalid request body"},
                    "404": {"description": "Torrent not found"},
                    "500": {"description": "Failed to change status"}
                }
            }
        },
        "/api/torrents/settings/{info_hash}/{download_path}": {
            "get": {
                "tags": ["Torrent settings"],
                "summary": "Get torrent settings",
                "parameters": [{"$ref": "#/parameters/InfoHash"}, {"$ref": "#/parameters/DownloadPath"}],
                "responses": {
                    "200": {"description": "Torrent settings"},
                    "404": {"description": "Torrent not found"}
                }
            },
            "put": {
                "tags": ["Torrent settings"],
                "summary": "Change torrent settings",
                "parameters": [
                    {"$ref": "#/parameters/InfoHash"},
                    {"$ref": "#/parameters/DownloadPath"},
                    {"$ref": "#/parameters/TorrentSettings"}
                ],
                "responses": {
                    "200": {"description": "Settings updated"},
                    "400": {"description": "Invalid request body"},
                    "404": {"description": "Torrent not found"},
                    "500": {"description": "Failed to change settings"}
                }
            }
        },
        "/api/global_settings": {
            "get": {
                "tags": ["Global settings"],
                "summary": "Get global settings",
                "responses": {
                    "200": {"description": "Global settings"},
                    "500": {"description": "Failed to retrieve global settings"}
                }
            },
            "put": {
                "tags": ["Global settings"],
                "summary": "Change global settings",
                "parameters": [{"$ref": "#/parameters/GlobalSettings"}],
                "responses": {
                    "200": {"description": "Settings updated"},
                    "400": {"description": "Invalid request body"},
                    "500": {"description": "Failed to change global settings"}
                }
            }
        }
    },
    "parameters": {
        "InfoHash": {
            "name": "info_hash",
            "in": "path",
            "required": True,
            "type": "string"
        },
        "DownloadPath": {
            "name": "download_path",
            "in": "path",
            "required": True,
            "type": "string"
        },
        "TorrentSettings": {
            "name": "settings",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "max_connections": {"type": "integer", "minimum": 0, "example": 50},
                    "download_speed_limit": {"type": "number", "minimum": 0, "example": 0},
                    "upload_speed_limit": {"type": "number", "minimum": 0, "example": 0},
                    "tracker_amount": {"type": "integer", "minimum": 0, "example": 4}
                },
                "example": {
                    "max_connections": 50,
                    "download_speed_limit": 0,
                    "upload_speed_limit": 0,
                    "tracker_amount": 4
                }
            }
        },
        "TorrentStatus": {
            "name": "status",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["is_downloading", "is_seeding"],
                "properties": {
                    "is_downloading": {"type": "boolean", "example": True},
                    "is_seeding": {"type": "boolean", "example": False}
                },
                "example": {"is_downloading": True, "is_seeding": False}
            }
        },
        "GlobalSettings": {
            "name": "settings",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "enable_dht": {"type": "boolean", "example": True},
                    "enable_port_forwarding": {"type": "boolean", "example": True},
                    "enable_receiving_peers": {"type": "boolean", "example": True}
                },
                "example": {
                    "enable_dht": True,
                    "enable_port_forwarding": True,
                    "enable_receiving_peers": True
                }
            }
        }
    }
})

class AsyncRunner:
    #we generate and run a new even loop in a separate thread so we can run async 
    # functions inside of it while the main thread is running the flask server
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait()

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    def run(self, coroutine):
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        return future.result()


async_runner = AsyncRunner()
client_started = False


def run_manager(operation):
    global client_started
    if not client_started:
        async_runner.run(torrents_manager.start_torrent_client())
        client_started = True
    return async_runner.run(operation())


#http status codes
OK = 200 
CREATED = 201 
NO_CONTENT = 204
BAD_REQUEST = 400
NOT_FOUND = 404
CONFLICT = 409
UNPROCESSABLE_ENTITY = 422
GENERAL_ERROR = 500


def _get_json_object():
    if not request.is_json:
        return None, "Request body must be JSON"
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        return None, "Request body must be a non-empty JSON object"
    return payload, None



def _validate_torrent_settings(payload):
    allowed_fields = {
        "max_connections",
        "download_speed_limit",
        "upload_speed_limit",
        "tracker_amount",
    }
    unknown_fields = set(payload) - allowed_fields
    if unknown_fields:
        return f"Unknown field: {sorted(unknown_fields)[0]}"

    integer_fields = {"max_connections", "tracker_amount"}
    for field in integer_fields:
        if field in payload and (
            type(payload[field]) is not int or payload[field] < 0
        ):
            return f"{field} must be a non-negative integer"

    numeric_fields = {"download_speed_limit", "upload_speed_limit"}
    for field in numeric_fields:
        if field in payload and (
            isinstance(payload[field], bool)
            or not isinstance(payload[field], (int, float))
            or payload[field] < 0
        ):
            return f"{field} must be a non-negative number"
    return None


def _validate_global_settings(payload):
    allowed_fields = {
        "enable_dht",
        "enable_port_forwarding",
        "enable_receiving_peers",
    }
    unknown_fields = set(payload) - allowed_fields
    if unknown_fields:
        return f"Unknown field: {sorted(unknown_fields)[0]}"
    for field in allowed_fields:
        if field in payload and type(payload[field]) is not bool:
            return f"{field} must be a boolean"
    return None


def _validate_torrent_status(payload):
    for field in ("is_downloading", "is_seeding"):
        if field not in payload:
            return f"Missing {field} field"
        if type(payload[field]) is not bool:
            return f"{field} must be a boolean"
    unknown_fields = set(payload) - {"is_downloading", "is_seeding"}
    if unknown_fields:
        return f"Unknown field: {sorted(unknown_fields)[0]}"
    return None


def _validate_path_field(payload, field):
    if field not in payload:
        return f"Missing {field} field"
    if not isinstance(payload[field], str) or not payload[field].strip():
        return f"{field} must be a non-empty string"
    return None


def _normalize_download_path(download_path):
    download_path = unquote(download_path)
    if len(download_path) >= 2 and download_path[0] == download_path[-1] == '"':
        download_path = download_path[1:-1]
    return download_path

def _parse_torrent_key(info_hash, download_path):
    try:
        info_hash_bytes = bytes.fromhex(info_hash)
    except ValueError:
        return None
    if len(info_hash_bytes) != 20:
        return None
    return info_hash_bytes, _normalize_download_path(download_path)

@app.route('/api/torrents', methods=['GET'])
def get_torrents():
    """List all torrents.
        tags:
            - Torrents
        responses:
            200:
                description: List of torrents.
        """
    timestamp = time.time()
    torrents = run_manager(torrents_manager.get_torrents)
    data = {
        "message_status": "success",
        "timestamp": timestamp,
        "torrents": torrents
    }
    return jsonify(data), OK

@app.route('/api/torrents/<string:info_hash>/<path:download_path>', methods=['GET'])
@app.route('/api/torrents/status/<string:info_hash>/<path:download_path>', methods=['GET'])
def get_torrent_status(info_hash, download_path):
    """Get the status of a torrent.
        tags:
            - Torrents
        parameters:
                    - in: path
                        name: torrent_download_path
                        required: true
                        type: string
        responses:
            200:
                description: Torrent status.
            404:
                description: Torrent not found.
    """
    torrent_key = _parse_torrent_key(info_hash, download_path)
    if torrent_key is None:
        return jsonify({"message_status": "error", "message": "Invalid info hash"}), BAD_REQUEST
    timestamp = time.time()
    torrent_status = run_manager(lambda: torrents_manager.get_torrent_status(*torrent_key))
    
    if torrent_status is None:
        return jsonify({"message_status": "error", "timestamp": timestamp}), NOT_FOUND

    data = {
        "message_status": "success",
        "timestamp": timestamp,
    }
    return jsonify({**data, **torrent_status}), OK

@app.route('/api/torrents/settings/<string:info_hash>/<path:download_path>', methods=['GET'])
def get_torrent_settings(info_hash, download_path):
    """Get settings for a torrent.
        tags:
            - Torrent settings
        parameters:
            - in: path
                name: torrent_download_path
                required: true
                type: string
        responses:
            200:
                description: Torrent settings.
            404:
                description: Torrent not found.
    """
    torrent_key = _parse_torrent_key(info_hash, download_path)
    if torrent_key is None:
        return jsonify({"message_status": "error", "message": "Invalid info hash"}), BAD_REQUEST
    timestamp = time.time()
    torrent_status = run_manager(lambda: torrents_manager.get_torrent_settings(*torrent_key))
    
    if torrent_status is None:
        return jsonify({"message_status": "error", "timestamp": timestamp}), NOT_FOUND

    data = {
        "message_status": "success",
        "timestamp": timestamp,
    }
    return jsonify({**data, **torrent_status}), OK

@app.route('/api/torrents', methods=['POST'])
def add_new_torrent():
    """Add a torrent.
        tags:
            - Torrents
        consumes:
            - application/json
        parameters:
            - in: body
                name: torrent
                required: true
                schema:
                    type: object
                    required:
                        - download_path
                        - file_path
                    properties:
                        download_path:
                            type: string
                        file_path:
                            type: string
                        max_connections:
                            type: integer
                        download_speed_limit:
                            type: integer
                        upload_speed_limit:
                            type: integer
                        tracker_amount:
                            type: integer
        responses:
            200:
                description: Torrent accepted.
            400:
                description: Invalid request body.
            409:
                description: Torrent already exists.
    """
    user_input, validation_error = _get_json_object()
    if validation_error:
        return jsonify({"status": "error", "message": validation_error}), BAD_REQUEST
    for field in ("download_path", "file_path"):
        validation_error = _validate_path_field(user_input, field)
        if validation_error:
            return jsonify({"status": "error", "message": validation_error}), BAD_REQUEST
    validation_error = _validate_torrent_settings({
        field: user_input[field]
        for field in (
            "max_connections",
            "download_speed_limit",
            "upload_speed_limit",
            "tracker_amount",
        )
        if field in user_input
    })
    if validation_error:
        return jsonify({"status": "error", "message": validation_error}), BAD_REQUEST

    torrent_settings = torrents_manager.TorrentSettings()
    if "max_connections" in user_input:
        torrent_settings.max_connections = user_input["max_connections"]
    if "download_speed_limit" in user_input:
        torrent_settings.download_speed_limit = user_input["download_speed_limit"]
    if "upload_speed_limit" in user_input:
        torrent_settings.upload_speed_limit = user_input["upload_speed_limit"]
    if "tracker_amount" in user_input:
        torrent_settings.tracker_amount = user_input["tracker_amount"]

    try:
        info_hash = torrents_manager.TorrentFile(user_input["file_path"]).info_hash
    except (OSError, ValueError, KeyError, TypeError):
        info_hash = None
    if info_hash is not None and run_manager(lambda: torrents_manager.get_torrent(
        info_hash, user_input["download_path"]
    )) is not None:
        return jsonify({"status": "error", "message": "Torrent already exists"}), CONFLICT

    if not run_manager(lambda: torrents_manager.add_new_torrent(
        user_input["file_path"], user_input["download_path"], torrent_settings
    )):
        return jsonify({"status": "error", "message": "Failed to add torrent"}),  GENERAL_ERROR    
    # Send a response back confirming receipt
    return jsonify({
        "status": "received", 
    }), OK

@app.route('/api/torrents/settings/<string:info_hash>/<path:download_path>', methods=['PUT'])
def change_torrent_settings(info_hash, download_path):
    """Change settings for a torrent.
        tags:
            - Torrent settings
        parameters:
            - in: path
                name: torrent_download_path
                required: true
                type: string
            - in: body
                name: settings
                required: true
                schema:
                    type: object
                    properties:
                        max_connections:
                            type: integer
                        download_speed_limit:
                            type: integer
                        upload_speed_limit:
                            type: integer
                        tracker_amount:
                            type: integer
        responses:
            200:
                description: Settings updated.
            400:
                description: Invalid request body.
    """
    torrent_key = _parse_torrent_key(info_hash, download_path)
    if torrent_key is None:
        return jsonify({"message_status": "error", "message": "Invalid info hash"}), BAD_REQUEST
    user_input, validation_error = _get_json_object()
    if validation_error:
        return jsonify({"status": "error", "message": validation_error}), BAD_REQUEST
    validation_error = _validate_torrent_settings(user_input)
    if validation_error:
        return jsonify({"status": "error", "message": validation_error}), BAD_REQUEST
    
    torrent_settings = torrents_manager.TorrentSettings()
    if "max_connections" in user_input:
        torrent_settings.max_connections = user_input["max_connections"]
    if "download_speed_limit" in user_input:
        torrent_settings.download_speed_limit = user_input["download_speed_limit"]
    if "upload_speed_limit" in user_input:
        torrent_settings.upload_speed_limit = user_input["upload_speed_limit"]
    if "tracker_amount" in user_input:
        torrent_settings.tracker_amount = user_input["tracker_amount"]

    if not run_manager(lambda: torrents_manager.change_torrent_settings(
        *torrent_key, torrent_settings
    )):
        return jsonify({"status": "error", "message": "Failed to change torrent settings"}), GENERAL_ERROR    
    # Send a response back confirming receipt
    return jsonify({
        "status": "received", 
    }), OK

@app.route('/api/torrents/status/<string:info_hash>/<path:download_path>', methods=['PUT'])
def change_torrent_status(info_hash, download_path):
    """Change the downloading and seeding status of a torrent.
        tags:
            - Torrents
        parameters:
            - in: path
                name: torrent_download_path
                required: true
                type: string
            - in: body
                name: status
                required: true
                schema:
                    type: object
                    required:
                        - is_downloading
                        - is_seeding
                    properties:
                        is_downloading:
                            type: boolean
                        is_seeding:
                            type: boolean
        responses:
            200:
                description: Status updated.
            400:
                description: Invalid request body.
    """
    torrent_key = _parse_torrent_key(info_hash, download_path)
    if torrent_key is None:
        return jsonify({"message_status": "error", "message": "Invalid info hash"}), BAD_REQUEST
    user_input, validation_error = _get_json_object()
    if validation_error:
        return jsonify({"status": "error", "message": validation_error}), BAD_REQUEST
    validation_error = _validate_torrent_status(user_input)
    if validation_error:
        return jsonify({"status": "error", "message": validation_error}), BAD_REQUEST

    if not run_manager(lambda: torrents_manager.change_torrent_status(
        *torrent_key, user_input["is_downloading"], user_input["is_seeding"]
    )):
        return jsonify({"status": "error", "message": "Failed to change torrent status"}), GENERAL_ERROR    
    # Send a response back confirming receipt
    return jsonify({
        "status": "received", 
    }), OK

@app.route('/api/torrents/<string:info_hash>/<path:download_path>', methods=['DELETE'])
def delete_torrent(info_hash, download_path):
    """Delete a torrent.
        tags:
            - Torrents
        parameters:
            - in: path
                name: torrent_download_path
                required: true
                type: string
        responses:
            200:
                description: Torrent deleted.
            500:
                description: Torrent could not be deleted.
    """
    torrent_key = _parse_torrent_key(info_hash, download_path)
    if torrent_key is None:
        return jsonify({"message_status": "error", "message": "Invalid info hash"}), BAD_REQUEST
    if not run_manager(lambda: torrents_manager.remove_torrent(*torrent_key)):
        return jsonify({"status": "error", "message": "Failed to delete torrent"}), GENERAL_ERROR    
    # Send a response back confirming receipt
    return jsonify({
        "status": "received", 
    }), OK


@app.route('/api/global_settings', methods=['GET'])
def get_global_settings() -> torrent_settings.GlobalTorrentSettings:
    """Get global client settings.
        tags:
            - Global settings
        responses:
            200:
                description: Global settings.
    """
    timestamp = time.time()
    run_manager(lambda: asyncio.sleep(0))
    global_settings = torrents_manager.global_settings
    if global_settings is None:
        return jsonify({"message_status": "error", "timestamp": timestamp}), GENERAL_ERROR
    data = {
        "message_status": "success",
        "timestamp": timestamp,
        "global_settings": vars(global_settings)
    }
    return jsonify(data), OK

@app.route('/api/global_settings', methods=['PUT'])
def change_global_settings() -> None:
    """Change global client settings.
        tags:
            - Global settings
        consumes:
            - application/json
        parameters:
            - in: body
                name: settings
                required: true
                schema:
                    type: object
                    properties:
                        enable_dht:
                            type: boolean
                        enable_port_forwarding:
                            type: boolean
                        enable_receiving_peers:
                            type: boolean
        responses:
            200:
                description: Settings updated.
            400:
                description: Invalid request body.
    """
    user_input, validation_error = _get_json_object()
    if validation_error:
        return jsonify({"status": "error", "message": validation_error}), BAD_REQUEST
    validation_error = _validate_global_settings(user_input)
    if validation_error:
        return jsonify({"status": "error", "message": validation_error}), BAD_REQUEST

    run_manager(lambda: asyncio.sleep(0))
    current_settings = torrents_manager.global_settings
    settings = torrent_settings.GlobalTorrentSettings(
        enable_dht=current_settings.enable_dht,
        enable_port_forwarding=current_settings.enable_port_forwarding,
        enable_receiving_peers=current_settings.enable_receiving_peers,
    )
    for field, value in user_input.items():
        setattr(settings, field, value)

    run_manager(lambda: torrents_manager.change_global_settings(settings))
    return jsonify({"status": "received"}), OK

if __name__ == '__main__':
    app.run(debug=True, port=5000)
