from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .auth import Auth
from .tuya import TuyaClient

api = Blueprint('api', __name__)
auth_handler = Auth()
tuya_client = TuyaClient()

@api.route("/", methods=["GET"])
def index():
    return 'yesssssssssss'

@api.route("/connexion", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    country_code = data.get("countryCode", "221")
    app_type = data.get("appType", "Smartlife")

    token, error = auth_handler.login(username, password, country_code, app_type)
    if error:
        return jsonify({"success": False, "error": error}), 401

    return jsonify({"success": True, "jwt": token})

@api.route('/command', methods=['POST'])
def send_command():
    data = request.get_json()
    code = data.get("code")     
    value = data.get("value")   

    if not code or value is None:
        return jsonify({'success': False, 'error': 'code et value sont requis'}), 400

    commands = {
        "commands": [
            {
                "code": code,
                "value": value
            }
        ]
    }

    try:
        response = tuya_client.send_device_command(device_id, commands)
        return jsonify({'success': True, 'response': response})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api.route("/toggle-device", methods=["POST"])
@jwt_required()
def toggle_device():
    current_user = get_jwt_identity()
    data = request.json
    device_id = data.get("mydevice_id")
    code = data.get("code")
    value = data.get("value")

    try:
        commands = {"commands": [{"code": code, "value": value}]}
        response = tuya_client.send_device_command(device_id, commands)

        if response.get("success"):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": response.get("msg")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@api.route("/get_devices", methods=["GET"])
@jwt_required()
def get_devices():
    try:
        response = tuya_client.get_devices()
        return jsonify({
            "success": True,
            "devices": response.get("result", [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@api.route('/device-status/<device_id>', methods=['GET'])
@jwt_required()
def get_device_status(device_id):
    try:
        response = tuya_client.get_device_status(device_id)
        return jsonify({
            "success": True,
            "devices": response.get("result", [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@api.route('/space-list', methods=['GET'])
def get_space_list():
    try:
        response = tuya_client.get_spaces()
        return jsonify({
            "success": True,
            "spaces": response.get("result", [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@api.route('/asset-name/<asset_id>', methods=['GET'])
def get_asset_name(asset_id):
    try:
        response = tuya_client.openapi.get(f"/v1.0/iot-02/assets/{asset_id}")
        return jsonify({
            "success": True,
            "asset": response.get("result", [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@api.route('/get_graphique_voltage/', methods=['GET'])
@jwt_required()
def get_voltage():
    try:
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        device_id = request.args.get("id")

        if not start_time or not end_time:
            return jsonify({
                "success": False,
                "message": "start_time et end_time sont requis"
            }), 400

        response = tuya_client.get_device_logs(device_id, "cur_voltage", start_time, end_time)
        return jsonify({
            "success": True,
            "donnees3": response.get("result", [])
        })
    except Exception as e:
        return jsonify({"success": False, "donnees3": str(e)})

@api.route('/get_graphique_current/', methods=['GET'])
def get_current():
    try:
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        device_id = request.args.get("id")

        if not start_time or not end_time:
            return jsonify({
                "success": False,
                "message": "start_time et end_time sont requis"
            }), 400

        response = tuya_client.get_device_logs(device_id, "cur_current", start_time, end_time)
        return jsonify({
            "success": True,
            "donnees_current": response.get("result", [])
        })
    except Exception as e:
        return jsonify({"success": False, "donnees_current": str(e)})

@api.route('/get_graphique_power/', methods=['GET'])
def get_power():
    try:
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        device_id = request.args.get("id")

        if not start_time or not end_time:
            return jsonify({
                "success": False,
                "message": "start_time et end_time sont requis"
            }), 400

        response = tuya_client.get_device_logs(device_id, "cur_power", start_time, end_time)
        return jsonify({
            "success": True,
            "donnees_power": response.get("result", [])
        })
    except Exception as e:
        return jsonify({"success": False, "donnees_power": str(e)})

@api.route('/get_logs_name/<id>', methods=['GET'])
def logs_name(id):
    try:
        response = tuya_client.get_device_status(id)
        return jsonify({
            "success": True,
            "datacode": response.get("result", [])
        })
    except Exception as e:
        return jsonify({"success": False, "datacode": str(e)})

@api.route('/get-device-name/<device_id>', methods=['GET'])
@jwt_required()
def get_device_name(device_id):
    try:
        response = tuya_client.openapi.get(f"/v2.0/cloud/thing/batch?device_ids={device_id}")
        return jsonify({
            "success": True,
            "device_name": response.get("result", [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@api.route('/device-status-socket/<device_id>', methods=['GET'])
@jwt_required()
def get_device_status_socket(device_id):
    try:
        response = tuya_client.get_device_status(device_id)
        return jsonify({
            "success": True,
            "devices": response.get("result", [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})