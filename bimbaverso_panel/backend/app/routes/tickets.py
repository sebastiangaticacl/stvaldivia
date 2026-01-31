from flask import Blueprint, request, jsonify
from datetime import datetime
from app.services.inventario import descontar

tickets_bp = Blueprint("tickets_bp", __name__)

tickets_store = {}

@tickets_bp.get("/api/ticket/lista")
def lista_tickets():
    return jsonify(tickets_store)

@tickets_bp.post("/api/ticket/nuevo")
def nuevo_ticket():
    data = request.json
    
    ticket_id = data.get("ticket_id")
    productos = data.get("productos")
    total = data.get("total")
    evento = data.get("evento")
    hora = datetime.now().isoformat()

    tickets_store[ticket_id] = {
        "estado":"pendiente",
        "productos":productos,
        "total":total,
        "evento":evento,
        "hora":hora
    }

    return jsonify({"ok":True,"ticket":ticket_id})

@tickets_bp.post("/api/ticket/validar")
def validar_ticket():
    data = request.json
    ticket_id = data.get("ticket_id")
    bartender = data.get("bartender")

    ticket = tickets_store.get(ticket_id)

    if not ticket:
        return jsonify({"ok":False,"error":"ticket_inexistente"}),400

    if ticket["estado"] == "validado":
        return jsonify({"ok":False,"error":"ticket_ya_validado"}),400

    ticket["estado"] = "validado"
    ticket["bartender"] = bartender
    
    return jsonify({"ok":True,"ticket":ticket_id,"estado":"validado"})

@tickets_bp.post("/api/ticket/entregar")
def entregar():
    data = request.json
    ticket_id = data.get("ticket_id")
    producto = data.get("producto")
    cantidad = data.get("cantidad",1)

    if descontar(producto, cantidad):
        return jsonify({"ok":True,"producto":producto,"cantidad":cantidad})
    return jsonify({"ok":False,"error":"receta_no_definida"})
