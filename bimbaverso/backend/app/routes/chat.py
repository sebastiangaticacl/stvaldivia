from flask import Blueprint, request, jsonify

chat_bp = Blueprint("chat", __name__)

@chat_bp.post("/api/chat")
def chat():
    data = request.json
    mensaje = data.get("mensaje","")
    # Aquí llamarías al agente RRSS
    respuesta = f"Bimba responde a: {mensaje}"
    return jsonify({"respuesta": respuesta})
