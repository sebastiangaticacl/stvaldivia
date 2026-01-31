from flask import Blueprint, jsonify

programacion_bp = Blueprint("programacion", __name__)

@programacion_bp.get("/api/programacion")
def programacion():
    # mock inicial
    return jsonify({
        "programacion": [
            {
                "evento": "Perreo en la Neblina",
                "fecha": "2025-12-23",
                "hora": "23:00",
                "djs": ["Krys", "Nachito Leal"],
                "cover_desde": 5000
            }
        ]
    })
