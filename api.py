import torrents_manager
from flask import Flask, jsonify, request
from flask_cors import CORS
import time
import torrent_settings

app = Flask(__name__)
CORS(app) 

torrents_manager = torrents_manager.start_torrent_client()

OK = 200 
CREATED = 201 
NO_CONTENT = 204
BAD_REQUEST = 400
NOT_FOUND = 404
CONFLICT = 409
UNPROCESSABLE_ENTITY = 422
GENERAL_ERROR = 500

@app.route('/api/torrents', methods=['GET'])
def get_torrents():
    timestamp = time.time()
    torrents = torrents_manager.get_torrents()
    data = {
        "message_status": "success",
        "timestamp": timestamp,
        "torrents": torrents
    }
    return jsonify(data), OK

@app.route('/api/torrents/<string:torrent_download_path>', methods=['GET'])
@app.route('/api/torrents/status/<string:torrent_download_path>', methods=['GET'])
def get_torrent_status(torrent_download_path):
    timestamp = time.time()
    torrent_status = torrents_manager.get_torrent_status(torrent_download_path)
    
    if torrent_status is None:
        return jsonify({"message_status": "error", "timestamp": timestamp}), NOT_FOUND

    data = {
        "message_status": "success",
        "timestamp": timestamp,
    }
    return jsonify(data + torrent_status), OK

@app.route('/api/torrents/settings/<string:torrent_download_path>', methods=['GET'])
def get_torrent_settings(torrent_download_path):
    timestamp = time.time()
    torrent_status = torrents_manager.get_torrent_settings(torrent_download_path)
    
    if torrent_status is None:
        return jsonify({"message_status": "error", "timestamp": timestamp}), NOT_FOUND

    data = {
        "message_status": "success",
        "timestamp": timestamp,
    }
    return jsonify(data + torrent_status), OK

@app.route('/api/torrents', methods=['POST'])
def add_new_torrent():
    user_input = request.json

    if not user_input:
        return jsonify({"status": "error", "message": "No data received"}), BAD_REQUEST
    if "download_path" not in user_input:
        return jsonify({"status": "error", "message": "Missing torrent download path field"}), BAD_REQUEST
    if "file_path" not in user_input:
        return jsonify({"status": "error", "message": "Missing torrent file path field"}), BAD_REQUEST

    torrent_settings = torrents_manager.TorrentSettings()
    if "max_connections" in user_input:
        torrent_settings.max_connections = user_input["max_connections"]
    if "download_speed_limit" in user_input:
        torrent_settings.download_speed_limit = user_input["download_speed_limit"]
    if "upload_speed_limit" in user_input:
        torrent_settings.upload_speed_limit = user_input["upload_speed_limit"]
    if "tracker_amount" in user_input:
        torrent_settings.tracker_amount = user_input["tracker_amount"]

    if torrents_manager.get_torrent(user_input["download_path"]) is not None:
        return jsonify({"status": "error", "message": "Torrent already exists"}), CONFLICT
    if not torrents_manager.add_new_torrent(user_input["file_path"], user_input["download_path"], torrent_settings):
        return jsonify({"status": "error", "message": "Failed to add torrent"}),  GENERAL_ERROR    
    # Send a response back confirming receipt
    return jsonify({
        "status": "received", 
    }), OK

@app.route('/api/torrents/settings/<string:torrent_download_path>', methods=['PUT'])
def change_torrent_settings(torrent_download_path):
    user_input = request.json

    if not user_input:
        return jsonify({"status": "error", "message": "No data received"}), BAD_REQUEST
    
    torrent_settings = torrents_manager.TorrentSettings()
    if "max_connections" in user_input:
        torrent_settings.max_connections = user_input["max_connections"]
    if "download_speed_limit" in user_input:
        torrent_settings.download_speed_limit = user_input["download_speed_limit"]
    if "upload_speed_limit" in user_input:
        torrent_settings.upload_speed_limit = user_input["upload_speed_limit"]
    if "tracker_amount" in user_input:
        torrent_settings.tracker_amount = user_input["tracker_amount"]

    if not torrents_manager.change_torrent_settings(torrent_download_path, torrent_settings):
        return jsonify({"status": "error", "message": "Failed to change torrent settings"}), GENERAL_ERROR    
    # Send a response back confirming receipt
    return jsonify({
        "status": "received", 
    }), OK

@app.route('/api/torrents/status/<string:torrent_download_path>', methods=['PUT'])
def change_torrent_status(torrent_download_path):
    user_input = request.json

    if not user_input:
        return jsonify({"status": "error", "message": "No data received"}), BAD_REQUEST
    if "is_downloading" not in user_input:
        return jsonify({"status": "error", "message": "Missing is_downloading field"}), BAD_REQUEST
    if "is_seeding" not in user_input:
        return jsonify({"status": "error", "message": "Missing is_seeding field"}), BAD_REQUEST

    if not torrents_manager.change_torrent_status(torrent_download_path, user_input["is_downloading"], user_input["is_seeding"]):
        return jsonify({"status": "error", "message": "Failed to change torrent status"}), GENERAL_ERROR    
    # Send a response back confirming receipt
    return jsonify({
        "status": "received", 
    }), OK

@app.route('/api/torrents/<string:torrent_download_path>', methods=['DELETE'])
def delete_torrent(torrent_download_path):
    if not torrents_manager.remove_torrent(torrent_download_path):
        return jsonify({"status": "error", "message": "Failed to delete torrent"}), GENERAL_ERROR    
    # Send a response back confirming receipt
    return jsonify({
        "status": "received", 
    }), OK


@app.route('/api/global_settings', methods=['GET'])
def get_global_settings() -> torrent_settings.GlobalTorrentSettings:
    timestamp = time.time()
    global_settings = torrents_manager.get_global_settings()
    data = {
        "message_status": "success",
        "timestamp": timestamp,
        "global_settings": global_settings
    }
    return jsonify(data), OK

@app.route('/api/global_settings', methods=['PUT'])
def change_global_settings() -> None:
    settings = torrent_settings.GlobalTorrentSettings()
    user_input = request.json

    if not user_input:
        return jsonify({"status": "error", "message": "No data received"}), BAD_REQUEST

    if "enable_dht" in user_input:
        settings.enable_dht = user_input["enable_dht"]
    if "enable_port_forwarding" in user_input:
        settings.enable_port_forwarding = user_input["enable_port_forwarding"]
    if "enable_receiving_peers" in user_input:
        settings.enable_receiving_peers = user_input["enable_receiving_peers"]

    torrents_manager.change_global_settings(settings)
if __name__ == '__main__':
    # Runs the backend server locally on http://127.0.0.1:5000
    app.run(debug=True, port=5000)
