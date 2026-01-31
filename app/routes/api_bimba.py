"""
API BIMBA - Endpoint para chat del agente BIMBA
"""
from flask import Blueprint, request, jsonify, current_app
from app.prompts.prompts_bimba import build_programacion_context, get_prompt_maestro_bimba
from app.application.services.programacion_service import ProgramacionService
from app.infrastructure.external.openai_client import OpenAIAPIClient
from app.infrastructure.external.dialogflow_client import DialogflowAPIClient
from app.helpers.simple_rate_limiter import check_rate_limit
import json

bp = Blueprint("api_bimba", __name__, url_prefix="/api")


@bp.post("/bimba/chat")
def bimba_chat():
    """
    Endpoint para chat con BIMBA.
    Recibe mensaje del usuario y devuelve respuesta generada por IA.
    """
    # Rate limiting: 30 requests / 5 minutos / IP
    client_ip = request.remote_addr or 'unknown'
    is_allowed, remaining = check_rate_limit(client_ip, max_requests=30, window_seconds=300)
    if not is_allowed:
        return jsonify({
            "error": "rate_limited",
            "detalle": "Demasiadas solicitudes. Intenta más tarde."
        }), 429
    
    try:
        data = request.get_json(force=True)
        user_message = data.get("message", "").strip()
        canal = data.get("canal", "publico").strip().lower()
        
        if not user_message:
            return jsonify({
                "error": "message_required",
                "detalle": "El campo 'message' es requerido"
            }), 400
        
        # Validar canal
        if canal not in ["publico", "admin"]:
            canal = "publico"  # Default a público si el canal no es válido
        
        # 1) Obtener programación desde el servicio local
        programacion_service = ProgramacionService()
        eventos = programacion_service.get_upcoming_events(limit=10)
        
        # 2) Convertir eventos a JSON string para el prompt maestro
        eventos_json = json.dumps(eventos) if eventos else "null"
        
        # 3) Obtener datos operativos solo si el canal es admin
        operacional_str = "None"
        if canal == "admin":
            from app.application.services.operational_insights_service import OperationalInsightsService
            try:
                operational = OperationalInsightsService.get_daily_summary()
                if operational:
                    operacional_str = json.dumps(operational, ensure_ascii=False, indent=2)
            except Exception as e:
                current_app.logger.warning(f"No se pudieron obtener datos operativos: {e}")
        
        # 4) Obtener el prompt maestro (incluye el contexto de programación formateado según el canal)
        system_prompt = get_prompt_maestro_bimba(eventos_json, operacional_str, canal)
        
        # 5) Llamar a OpenAI usando el cliente configurado
        openai_client = OpenAIAPIClient()
        
        # Usar el método del cliente que ya maneja errores y timeouts
        # Temperature reducida a 0.3 para respuestas más consistentes y cortas
        response = openai_client.generate_response(
            messages=[
                {"role": "user", "content": user_message}
            ],
            system_prompt=system_prompt,
            model="gpt-4o-mini",
            temperature=0.3,  # Reducido de 0.7 a 0.3 para respuestas más cortas y consistentes
            max_tokens=200  # Reducido de 400 a 200 para respuestas más cortas
        )
        
        if not response:
            # Fallback a Dialogflow si está configurado
            use_dialogflow = current_app.config.get('USE_DIALOGFLOW', False)
            if use_dialogflow:
                dialogflow_client = DialogflowAPIClient()
                session_id = f"bimba_{canal}_{request.remote_addr or 'unknown'}"
                response = dialogflow_client.generate_response(
                    messages=[{"role": "user", "content": user_message}],
                    system_prompt=system_prompt,
                    session_id=session_id
                )
                if response:
                    return jsonify({"reply": response}), 200
            
            # Fallback final si ambos servicios fallan
            return jsonify({
                "reply": "Hola! 💜 Soy BIMBA. Lo siento, estoy teniendo problemas técnicos en este momento. Por favor, intenta más tarde o revisa nuestras redes sociales @valdiviaesbimba 💜✨",
                "error": "openai_unavailable"
            }), 200
        
        return jsonify({"reply": response}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en /api/bimba/chat: {e}", exc_info=True)
        return jsonify({
            "error": "internal_error",
            "detalle": "Error al procesar mensaje. Intenta más tarde."
        }), 500

