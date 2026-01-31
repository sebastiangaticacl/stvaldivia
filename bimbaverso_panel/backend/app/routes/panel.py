from flask import Blueprint, jsonify, request
from app.services.agentes import get_estado, set_estado
from app.services.config_prompts import set_prompt_agente, get_prompt_activo

panel_bp = Blueprint("panel_bp", __name__)

@panel_bp.get("/api/panel/status")
def status():
    estado = get_estado()
    # Convertir True/False a "activo"/"inactivo"
    agentes_estado = {
        "rrss": "activo" if estado.get("rrss", True) else "inactivo",
        "optimizacion": "activo" if estado.get("optimizacion", True) else "inactivo",
        "mixologia": "activo" if estado.get("mixologia", True) else "inactivo"
    }
    return jsonify({
        "bimbaverso": "OK",
        "agentes": agentes_estado
    })

@panel_bp.post("/api/panel/agente/<agente>")
def toggle_agente(agente):
    data = request.get_json() or {}
    nuevo_estado = data.get("estado", True)
    
    if agente not in ["rrss", "optimizacion", "mixologia"]:
        return jsonify({"error": "Agente no válido"}), 400
    
    set_estado(agente, nuevo_estado)
    return jsonify({
        "agente": agente,
        "estado": "activo" if nuevo_estado else "inactivo"
    })

@panel_bp.post("/api/panel/agente/toggle")
def toggle_agente_post():
    data = request.json
    agente = data.get("agente")
    estado = data.get("estado")

    set_estado(agente, estado)
    return jsonify({"ok":True,"agente":agente,"estado":estado})

@panel_bp.get("/api/panel/agentes")
def agentes_estado():
    return jsonify(get_estado())

@panel_bp.get("/api/panel/metricas")
def metricas():
    return jsonify({
        "ventas_hoy": 1458000,
        "barra_promedio": 10800,
        "ticket_promedio": 5300,
        "hot_hour": "01:00 - 02:00",
        "satisfaccion": {
            "excelente": 40,
            "buena": 30,
            "regular": 20,
            "mala": 10
        }
    })

@panel_bp.post("/api/prompt/activar")
def activar_prompt():
    data = request.json
    agente = data.get("agente")
    prompt_id = data.get("prompt_id")

    if agente not in ["rrss","optimizacion","mixologia","cerebro"]:
        return jsonify({"ok":False,"error":"agente_invalido"}),400

    cfg = set_prompt_agente(agente, prompt_id)
    return jsonify({"ok":True,"config":cfg})

@panel_bp.get("/api/prompt/activo")
def activo_prompt():
    agente = request.args.get("agente")
    return jsonify(get_prompt_activo(agente))
