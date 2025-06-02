from dotenv import load_dotenv
import os
load_dotenv()
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask import Flask, request, jsonify
from flask_cors import CORS
from tuya_iot import TuyaOpenAPI, TUYA_LOGGER
from datetime import  timedelta
import logging


app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = "super-secret-key"  # ⚠️ à changer par une clé sécurisée
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=20)
jwt = JWTManager(app)

# Identifiants Tuya
ACCESS_ID = os.getenv("ACCESS_ID")
ACCESS_KEY = os.getenv("ACCESS_KEY")
ENDPOINT = "https://openapi.tuyaeu.com"

USERNAME = "ibrahman1970@gmail.com"
PASSWORD = "SmartLife@@@2025"
DEVICE_ID = 'vdevo174456632030882'

#ACCESS_TOKEN="2cb02a13bf2f0c0be28714c64491dfa7"

openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
openapi.connect(USERNAME, PASSWORD, "221", "Smartlife")

TOKENS = {}

TUYA_LOGGER.setLevel(logging.DEBUG)

@app.route("/", methods=["GET"])
def index():
    return 'yesssssssssss'

@app.route("/connexion", methods=["POST"])
def get_token():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    country_code = data.get("countryCode", "221")
    app_type = data.get("appType", "Smartlife")

    openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
    connected = openapi.connect(username, password, country_code, app_type)
    if not connected:
        return jsonify({"success": False, "error": "Échec de la connexion à Tuya."}), 401

    token_info = openapi.token_info

    #  On stocke le access_token dans une variable globale
    TOKENS[token_info.uid] = token_info.access_token

    #  On génère un JWT avec juste le UID
    jwt_token = create_access_token(identity=token_info.uid)

    return jsonify({
        "success": True,
        "jwt": jwt_token,
       
    })

@app.route('/command', methods=['POST'])
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
        response = openapi.post(f"/v1.0/devices/{DEVICE_ID}/commands", commands)
        return jsonify({'success': True, 'response': response})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route("/toggle-device", methods=["POST"])
@jwt_required()
def toggle_device():
    current_user=get_jwt_identity()
    data = request.json
    mydevice_id = data.get("mydevice_id")
    code = data.get("code")
    value = data.get("value")

    try:
        commands = {"commands": [{"code": code, "value": value}]}
        response = openapi.post(f"/v1.0/devices/{mydevice_id}/commands", commands)

        if response.get("success"):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": response.get("msg")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
@app.route("/get_devices", methods=["GET"])
@jwt_required()
def get_devices():
    try:
        current_user = get_jwt_identity()
        # Appel API Tuya pour récupérer les devices
        response = openapi.get("/v2.0/cloud/thing/device?page_size=20")
        return jsonify({
            "success": True,
            "devices": response.get("result", [])
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "errors": str(e)
        })
    
@app.route('/device-status/<device_id>', methods=['GET'])
@jwt_required()
def get_device_status(device_id):
    try:
        current_user = get_jwt_identity()
       
        response = openapi.get(f"/v1.0/iot-03/devices/status?device_ids={device_id}")
        return jsonify({
            "success": True,
            "devices": response.get("result", [])
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/space-list', methods=['GET'])
def get_space_list():
    try:
        response=openapi.get("/v2.0/cloud/space/child?only_sub=false&page_size=10") 
        return jsonify({
            "sucess":True,
            "spaces":response.get("result", [])
        })  
    except Exception as e:
        return jsonify({
          "success":False, 
          "error":str(e)
        }) 
 
@app.route('/asset-name/<asset_id>', methods=['GET'])
def get_asset_name(asset_id):
    try:
        response = openapi.get(f"/v1.0/iot-02/assets/{asset_id}")
        return jsonify({
            "sucess":True,
            "asset":response.get("result", [])
        })  
    except Exception as e:
        return jsonify({
          "success":False, 
          "error":str(e)
        })  
 


  


@app.route('/get_graphique_voltage/', methods=['GET'])
@jwt_required()
def get_voltage():
    try:
        current_user = get_jwt_identity()
        # Récupérer les paramètres dynamiques depuis l'URL
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        id = request.args.get("id")
        

        if not start_time or not end_time:
            return jsonify({
                "success": False,
                "message": "start_time et end_time sont requis"
            }), 400

        # Utiliser les valeurs dynamiques dans la requête OpenAPI
        url = f"/v2.0/cloud/thing/{id}/report-logs?codes=cur_voltage&end_time={end_time}&size=100&start_time={start_time}"
        response = openapi.get(url)

        return jsonify({
            "success": True,
            "donnees3": response.get("result", [])
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "donnees3": str(e)
        }) 
    

@app.route('/get_graphique_current/', methods=['GET'])
def get_current():
    try:
        # Récupérer les paramètres dynamiques depuis l'URL
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        id = request.args.get("id")
        

        if not start_time or not end_time:
            return jsonify({
                "success": False,
                "message": "start_time et end_time sont requis"
            }), 400

        # Utiliser les valeurs dynamiques dans la requête OpenAPI
        url = f"/v2.0/cloud/thing/{id}/report-logs?codes=cur_current&end_time={end_time}&size=100&start_time={start_time}"
        response = openapi.get(url)

        return jsonify({
            "success": True,
            "donnees_current": response.get("result", [])
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "donnees_current": str(e)
        })


@app.route('/get_graphique_power/', methods=['GET'])
def get_power():
    try:
       
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        id = request.args.get("id")
        

        if not start_time or not end_time:
            return jsonify({
                "success": False,
                "message": "start_time et end_time sont requis"
            }), 400

        # Utiliser les valeurs dynamiques dans la requête OpenAPI
        url = f"/v2.0/cloud/thing/{id}/report-logs?codes=cur_power&end_time={end_time}&size=100&start_time={start_time}"
        response = openapi.get(url)

        return jsonify({
            "success": True,
            "donnees_power": response.get("result", [])
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "donnees_power": str(e)
        })



@app.route('/get_logs_name/<id>', methods=['GET'])
def logs_name(id):
        try:
            response=openapi.get(f"/v1.0/iot-03/devices/{id}/status")
            return jsonify({
            "success":True,
            "datacode":response.get("result", [])

        })
        except Exception as e:
          return jsonify({
          "success":False,
          "datacode":str(e)
        }) 


@app.route('/get-device-name/<device_id>', methods=['GET'])
@jwt_required()
def get_device_name(device_id):
    try:
        current_user = get_jwt_identity()
        # Appel API Tuya pour récupérer les devices
        response = openapi.get(f"/v2.0/cloud/thing/batch?device_ids={device_id}")
        return jsonify({
            "success": True,
            "device_name": response.get("result", [])
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })
    

@app.route('/device-status-socket/<device_id>', methods=['GET'])
@jwt_required()
def get_device_status_socket(device_id):
    try:
        current_user = get_jwt_identity()
        # Appel API Tuya pour récupérer les devices
        response = openapi.get(f"/v1.0/iot-03/devices/status?device_ids={device_id}")
        return jsonify({
            "success": True,
            "devices": response.get("result", [])
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })
    
      


if __name__ == '__main__':
    app.run(debug=True)
