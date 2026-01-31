"""
API V1 - Endpoints públicos y del bot
"""
from flask import Blueprint, jsonify, request, current_app
from app.application.services.programacion_service import ProgramacionService
from app.infrastructure.external.openai_client import OpenAIAPIClient
from app.infrastructure.external.dialogflow_client import DialogflowAPIClient
from app.helpers.simple_rate_limiter import check_rate_limit

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')


@api_v1.route('/public/evento/hoy', methods=['GET'])
def public_evento_hoy():
    """
    Endpoint público: Obtiene información del evento de hoy
    """
    # Rate limiting: 120 requests / 5 minutos / IP
    client_ip = request.remote_addr or 'unknown'
    is_allowed, remaining = check_rate_limit(client_ip, max_requests=120, window_seconds=300)
    if not is_allowed:
        return jsonify({
            "status": "error",
            "error": "rate_limited",
            "detalle": "Demasiadas solicitudes. Intenta más tarde."
        }), 429
    
    try:
        service = ProgramacionService()
        evento_info = service.get_public_info_for_today()
        
        if not evento_info:
            return jsonify({
                "status": "no_event",
                "evento": None
            }), 200
        
        return jsonify({
            "status": "ok",
            "evento": evento_info
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en /api/v1/public/evento/hoy: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "detalle": "Error al obtener información del evento"
        }), 500


@api_v1.route('/public/eventos/proximos', methods=['GET'])
def public_eventos_proximos():
    """
    Endpoint público: Obtiene lista de eventos próximos
    """
    # Rate limiting: 120 requests / 5 minutos / IP
    client_ip = request.remote_addr or 'unknown'
    is_allowed, remaining = check_rate_limit(client_ip, max_requests=120, window_seconds=300)
    if not is_allowed:
        return jsonify({
            "status": "error",
            "error": "rate_limited",
            "detalle": "Demasiadas solicitudes. Intenta más tarde."
        }), 429
    
    try:
        limit = request.args.get('limit', type=int) or 10
        
        service = ProgramacionService()
        eventos = service.get_upcoming_events(limit=limit)
        
        return jsonify({
            "status": "ok",
            "eventos": eventos
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en /api/v1/public/eventos/proximos: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "detalle": "Error al obtener eventos próximos"
        }), 500


@api_v1.route('/bot/responder', methods=['POST'])
def bot_responder():
    """
    Endpoint del bot: Genera respuesta usando OpenAI basada en programación del día
    """
    # Rate limiting: 30 requests / 5 minutos / IP
    client_ip = request.remote_addr or 'unknown'
    is_allowed, remaining = check_rate_limit(client_ip, max_requests=30, window_seconds=300)
    if not is_allowed:
        return jsonify({
            "status": "error",
            "error": "rate_limited",
            "detalle": "Demasiadas solicitudes. Intenta más tarde."
        }), 429
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "status": "error",
                "detalle": "JSON requerido"
            }), 400
        
        mensaje = data.get('mensaje', '').strip()
        canal = data.get('canal', 'interno').strip()
        
        if not mensaje:
            return jsonify({
                "status": "error",
                "detalle": "El campo 'mensaje' es requerido"
            }), 400
        
        programacion_service = ProgramacionService()
        evento_info = programacion_service.get_public_info_for_today()
        
        # Obtener datos operativos del día (contexto privado para el bot)
        # Esto es opcional y no debe retrasar la respuesta
        from app.application.services.operational_insights_service import OperationalInsightsService
        try:
            operational = OperationalInsightsService.get_daily_summary()
        except Exception:
            # Si falla, continuar sin datos operativos (no es crítico)
            operational = None
        
        # CAPA 1: Intent Router - Detectar intención
        from app.application.services.intent_router import IntentRouter
        intent = IntentRouter.detectar_intent(mensaje)
        
        # CAPA 2: Bot Rule Engine - Intentar generar respuesta con reglas
        from app.application.services.bot_rule_engine import BotRuleEngine
        respuesta_rule_based = BotRuleEngine.generar_respuesta(intent, evento_info, operational)
        
        if respuesta_rule_based:
            # Respuesta generada por reglas duras
            return jsonify({
                "status": "ok",
                "respuesta": respuesta_rule_based,
                "source": "rule_based",
                "intent": intent,
                "modelo": None,
                "tokens": None
            }), 200
        
        # CAPA 2 y 3: Si no hay match en reglas, intentar OpenAI con contexto operativo
        # PERO: Si el intent es "unknown", intentar primero con OpenAI para respuestas creativas
        # Si OpenAI falla, usar fallback contextual (no genérico)
        try:
            from app.prompts.prompts_bimba import get_prompt_maestro_bimba
            
            if evento_info:
                import json
                evento_str = json.dumps(evento_info, ensure_ascii=False, indent=2)
            else:
                evento_str = "null"
            
            # Formatear datos operativos para el prompt
            if operational:
                import json
                operational_str = json.dumps(operational, ensure_ascii=False, indent=2)
            else:
                operational_str = "None"
            
            # Obtener prompt completo con conocimiento del sistema
            system_prompt = get_prompt_maestro_bimba(evento_str, operational_str)
        except ImportError:
            current_app.logger.warning("PROMPT_MAESTRO_BIMBA no encontrado, usando prompt por defecto")
            if evento_info:
                evento_str = f"Evento de hoy: {evento_info.get('nombre_evento', 'N/A')}"
            else:
                evento_str = "No hay evento programado para hoy"
            system_prompt = f"""Eres BIMBA, el agente de inteligencia artificial oficial del Club BIMBA. Tu primera y principal labor es atender las redes sociales del club.
            
            BIMBA es un espacio seguro, inclusivo y vibrante que celebra la diversidad, la música y la libertad de expresión.
            
            Información del evento: {evento_str}
            
            Responde de forma cercana, cálida, queer-friendly y entusiasta, reflejando los valores de inclusividad y acogida de BIMBA. Tu función es atender mensajes en redes sociales de forma rápida y acogedora."""
        
        # Usar OpenAI como servicio principal
        client = OpenAIAPIClient()
        openai_client = client._get_client()
        
        if not openai_client:
            # OpenAI no disponible - intentar Dialogflow como fallback opcional
            use_dialogflow = current_app.config.get('USE_DIALOGFLOW', False)
            if use_dialogflow:
                dialogflow_client = DialogflowAPIClient()
                session_id = f"web_{client_ip.replace('.', '_')}"
                dialogflow_response = dialogflow_client.generate_response(
                    messages=[{"role": "user", "content": mensaje}],
                    system_prompt=system_prompt,
                    session_id=session_id
                )
                if dialogflow_response:
                    return jsonify({
                        "status": "ok",
                        "respuesta": dialogflow_response,
                        "source": "dialogflow",
                        "intent": intent,
                        "modelo": "dialogflow",
                        "tokens": None
                    }), 200
            
            # Si no hay OpenAI ni Dialogflow, usar fallback basado en reglas
            current_app.logger.warning("OpenAI no disponible, generando respuesta basada en reglas y conocimiento")
            
            # Intentar generar respuesta más útil según la intención detectada
            if intent and intent != "unknown":
                # Si detectamos una intención conocida, usar las reglas para generar respuesta más útil
                respuesta_util = BotRuleEngine.generar_respuesta(intent, evento_info, operational)
                if respuesta_util:
                    return jsonify({
                        "status": "ok",
                        "respuesta": respuesta_util,
                        "source": "rule_based_fallback",
                        "intent": intent,
                        "modelo": None,
                        "tokens": None
                    }), 200
            
            # Si no hay intención o no se generó respuesta, usar fallback contextual
            respuesta_segura = "Hola! 💜 Soy BIMBA, el agente de IA de BIMBA. "
            if evento_info:
                nombre_evento = evento_info.get('nombre_evento', '')
                if nombre_evento:
                    respuesta_segura += f"Hoy tenemos **{nombre_evento}**. "
                horario = evento_info.get('horario', '')
                if horario:
                    respuesta_segura += f"Horario: {horario}. "
            respuesta_segura += "\n\nPuedo ayudarte con información sobre eventos, horarios, precios, DJs y más. ¿Qué te gustaría saber? 💜"
            respuesta_segura += "\n\nTambién puedes revisar nuestras redes sociales o contactarnos directamente para más información. ¡Nos vemos! ✨"
            
            return jsonify({
                "status": "ok",
                "respuesta": respuesta_segura,
                "source": "fallback_contextual",
                "intent": intent,
                "modelo": None,
                "tokens": None
            }), 200
        
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        formatted_messages.append({
            "role": "user",
            "content": mensaje
        })
        
        try:
            import openai
            # Timeout de 5 segundos - más agresivo, si OpenAI no responde rápido usa fallback
            # Temperature reducida a 0.3 para respuestas más cortas y consistentes
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=formatted_messages,
                temperature=0.3,  # Reducido de 0.7 a 0.3 para respuestas más cortas
                max_tokens=200,  # Reducido de 500 a 200 para respuestas más cortas (máx 12 palabras, 2 líneas)
                timeout=5.0
            )
            
            if not response.choices or len(response.choices) == 0:
                return jsonify({
                    "status": "error",
                    "detalle": "No se recibió respuesta de OpenAI"
                }), 500
            
            respuesta_texto = response.choices[0].message.content.strip()
            
            tokens_info = {
                "input": 0,
                "output": 0,
                "total": 0
            }
            
            if response.usage:
                tokens_info = {
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                }
            
        except openai.AuthenticationError as e:
            current_app.logger.error(f"Error de autenticación en OpenAI: {e}")
            # Fallback usando reglas si tenemos intención detectada
            if intent and intent != "unknown":
                respuesta_util = BotRuleEngine.generar_respuesta(intent, evento_info, operational)
                if respuesta_util:
                    return jsonify({
                        "status": "ok",
                        "respuesta": respuesta_util,
                        "source": "rule_based_fallback",
                        "intent": intent,
                        "modelo": None,
                        "tokens": None
                    }), 200
            
            # Fallback contextual
            respuesta_segura = "Hola! 💜 Soy BIMBA. "
            if evento_info:
                nombre_evento = evento_info.get('nombre_evento', '')
                if nombre_evento:
                    respuesta_segura += f"Hoy tenemos {nombre_evento}. "
            respuesta_segura += "Puedo ayudarte con información sobre eventos, horarios, precios y más. ¿Qué te gustaría saber? 💜✨"
            return jsonify({
                "status": "ok",
                "respuesta": respuesta_segura,
                "source": "fallback",
                "intent": intent,
                "modelo": None,
                "tokens": None
            }), 200
        except openai.RateLimitError as e:
            current_app.logger.error(f"Rate limit excedido en OpenAI: {e}")
            # Fallback seguro
            respuesta_segura = "Hola! 💜 Estoy recibiendo muchas consultas ahora. "
            if evento_info:
                nombre_evento = evento_info.get('nombre_evento', '')
                if nombre_evento:
                    respuesta_segura += f"Hoy tenemos {nombre_evento}. "
            respuesta_segura += "Intenta más tarde o revisa nuestras redes. 💜✨"
            return jsonify({
                "status": "ok",
                "respuesta": respuesta_segura,
                "source": "fallback",
                "intent": intent,
                "modelo": None,
                "tokens": None
            }), 200
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            current_app.logger.error(f"Error de conexión/timeout en OpenAI: {e}")
            # Fallback usando reglas si tenemos intención detectada
            if intent and intent != "unknown":
                respuesta_util = BotRuleEngine.generar_respuesta(intent, evento_info, operational)
                if respuesta_util:
                    return jsonify({
                        "status": "ok",
                        "respuesta": respuesta_util,
                        "source": "rule_based_fallback",
                        "intent": intent,
                        "modelo": None,
                        "tokens": None
                    }), 200
            
            # Fallback contextual
            respuesta_segura = "Hola! 💜 Soy BIMBA. "
            if evento_info:
                nombre_evento = evento_info.get('nombre_evento', '')
                if nombre_evento:
                    respuesta_segura += f"Hoy tenemos {nombre_evento}. "
            respuesta_segura += "Puedo ayudarte con información sobre eventos, horarios, precios y más. ¿Qué te gustaría saber? 💜✨"
            return jsonify({
                "status": "ok",
                "respuesta": respuesta_segura,
                "source": "fallback",
                "intent": intent,
                "modelo": None,
                "tokens": None
            }), 200
        except openai.APIError as e:
            current_app.logger.error(f"Error en API de OpenAI: {e}")
            # Fallback usando reglas si tenemos intención detectada
            if intent and intent != "unknown":
                respuesta_util = BotRuleEngine.generar_respuesta(intent, evento_info, operational)
                if respuesta_util:
                    return jsonify({
                        "status": "ok",
                        "respuesta": respuesta_util,
                        "source": "rule_based_fallback",
                        "intent": intent,
                        "modelo": None,
                        "tokens": None
                    }), 200
            
            # Fallback contextual
            respuesta_segura = "Hola! 💜 Soy BIMBA. "
            if evento_info:
                nombre_evento = evento_info.get('nombre_evento', '')
                if nombre_evento:
                    respuesta_segura += f"Hoy tenemos {nombre_evento}. "
            respuesta_segura += "Puedo ayudarte con información sobre eventos, horarios, precios y más. ¿Qué te gustaría saber? 💜✨"
            return jsonify({
                "status": "ok",
                "respuesta": respuesta_segura,
                "source": "fallback",
                "intent": intent,
                "modelo": None,
                "tokens": None
            }), 200
        except Exception as e:
            current_app.logger.error(f"Error inesperado al generar respuesta: {e}", exc_info=True)
            # Fallback usando reglas si tenemos intención detectada
            if intent and intent != "unknown":
                respuesta_util = BotRuleEngine.generar_respuesta(intent, evento_info, operational)
                if respuesta_util:
                    return jsonify({
                        "status": "ok",
                        "respuesta": respuesta_util,
                        "source": "rule_based_fallback",
                        "intent": intent,
                        "modelo": None,
                        "tokens": None
                    }), 200
            
            # Fallback seguro - NUNCA exponer stacktrace
            respuesta_segura = "Hola! 💜 Soy BIMBA, el agente de IA. "
            if evento_info:
                nombre_evento = evento_info.get('nombre_evento', '')
                if nombre_evento:
                    respuesta_segura += f"Hoy tenemos {nombre_evento}. "
            respuesta_segura += "Puedo ayudarte con información sobre eventos, horarios, precios y más. ¿Qué te gustaría saber? 💜✨"
            return jsonify({
                "status": "ok",
                "respuesta": respuesta_segura,
                "source": "fallback",
                "intent": intent,
                "modelo": None,
                "tokens": None
            }), 200
        
        return jsonify({
            "status": "ok",
            "respuesta": respuesta_texto,
            "source": "openai",
            "intent": intent,
            "modelo": "gpt-4o-mini",
            "tokens": tokens_info
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en /api/v1/bot/responder: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "detalle": str(e)
        }), 500


