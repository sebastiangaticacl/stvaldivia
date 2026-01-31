"""
Motor de respuestas del Bot de IA BimbaBot
Sistema de 3 capas de inteligencia:
1. Reglas duras (rule-based) para respuestas típicas
2. Contexto operativo para feeling real
3. OpenAI para respuestas creativas o abiertas
"""
from typing import Optional, Dict, Any, Tuple
from app.application.services.programacion_service import ProgramacionService
from app.application.services.operational_insights_service import OperationalInsightsService
import re


class BimbaBotEngine:
    """
    Motor de respuestas del bot BimbaBot.
    Sistema de 3 capas: reglas duras → contexto operativo → OpenAI
    """
    
    @staticmethod
    def _normalize_message(mensaje: str) -> str:
        """Normaliza el mensaje para comparación (lowercase, sin acentos básicos)"""
        mensaje = mensaje.lower().strip()
        # Reemplazos básicos de acentos
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', '¿': '', '?': '', '¡': '', '!': ''
        }
        for old, new in replacements.items():
            mensaje = mensaje.replace(old, new)
        return mensaje
    
    @staticmethod
    def _detect_intent(mensaje: str) -> Optional[str]:
        """
        Detecta la intención del mensaje para aplicar reglas duras.
        
        Returns:
            str: Tipo de intención detectada o None si no hay match
        """
        normalized = BimbaBotEngine._normalize_message(mensaje)
        
        # Patrones para "qué hay hoy" / "evento de hoy"
        if re.search(r'\b(que|q)\s*(hay|tiene|pasa|sucede|ocurre)\s*(hoy|esta noche|esta nochecita)\b', normalized) or \
           re.search(r'\bevento\s*(de|del|hoy|esta noche)\b', normalized) or \
           re.search(r'\b(hay|tiene|tendran)\s*(algo|evento|fiesta|noche)\s*(hoy|esta noche)\b', normalized):
            return "evento_hoy"
        
        # Patrones para "cómo va la noche"
        if re.search(r'\b(como|como va|como esta|como andamos|como andan)\s*(la noche|la nochecita|la fiesta|el ambiente|todo)\b', normalized) or \
           re.search(r'\b(como va|como esta|como andamos)\s*(hoy|esta noche|esta nochecita)\b', normalized):
            return "estado_noche"
        
        # Patrones para "próximos eventos"
        if re.search(r'\b(proximos|siguientes|que viene|que vienen|futuros)\s*(eventos|evento|fiestas|fiesta|noches|noche)\b', normalized) or \
           re.search(r'\b(que|q)\s*(viene|vienen|sigue|siguen|hay despues)\b', normalized):
            return "proximos_eventos"
        
        # Patrones para "precios"
        if re.search(r'\b(precio|precios|cuanto|cuanto cuesta|cuanto vale|tarifa|tarifas|entrada|entradas)\b', normalized):
            return "precios"
        
        # Patrones para "horario"
        if re.search(r'\b(horario|hora|a que hora|desde que hora|hasta que hora|cuando|que hora)\b', normalized):
            return "horario"
        
        # Patrones para "lista"
        if re.search(r'\b(lista|lista de espera|reserva|reservas|mesa|mesas)\b', normalized):
            return "lista"
        
        # Patrones para "DJ" / "música"
        if re.search(r'\b(dj|djs|disc jockey|musica|musical|quien toca|quienes tocan)\b', normalized):
            return "djs"
        
        # Patrones para preguntas sobre "cómo funciona"
        if re.search(r'\b(como funciona|como se|explicame|explica|que es|que significa)\s*(el sistema|un pedido|pedidos|una venta|ventas|ticket|qr|jornada|barra|bartender)\b', normalized):
            return "como_funciona"
        
        # Patrones para saludo genérico
        if re.search(r'\b(hola|holi|buenas|buenos|saludos|hey|hi|hello)\b', normalized):
            return "saludo"
        
        return None
    
    @staticmethod
    def _generate_rule_based_response(intent: str, evento_info: Optional[Dict[str, Any]], 
                                     operational: Optional[Dict[str, Any]] = None) -> str:
        """
        Genera respuesta basada en reglas duras según la intención detectada.
        
        Args:
            intent: Tipo de intención detectada
            evento_info: Información del evento de hoy
            operational: Información operativa del día (opcional)
            
        Returns:
            str: Respuesta generada
        """
        if intent == "evento_hoy":
            if not evento_info:
                return "Hoy no tenemos un evento cargado en la programación 💜. Revisa nuestras redes para más información."
            
            respuesta_partes = []
            nombre_evento = evento_info.get('nombre_evento', 'Evento especial')
            respuesta_partes.append(f"🎉 **{nombre_evento}**")
            
            horario = evento_info.get('horario', '')
            if horario:
                respuesta_partes.append(f"\n🕐 Horario: {horario}")
            
            dj_principal = evento_info.get('dj_principal', '')
            if dj_principal:
                respuesta_partes.append(f"\n🎧 DJ Principal: {dj_principal}")
            
            otros_djs = evento_info.get('otros_djs', '')
            if otros_djs:
                respuesta_partes.append(f"\n🎵 También: {otros_djs}")
            
            descripcion_corta = evento_info.get('descripcion_corta', '')
            if descripcion_corta:
                respuesta_partes.append(f"\n📝 {descripcion_corta}")
            
            info_lista = evento_info.get('lista', '')
            if info_lista:
                respuesta_partes.append(f"\n📋 {info_lista}")
            
            precios = evento_info.get('precios', [])
            if precios and isinstance(precios, list) and len(precios) > 0:
                respuesta_partes.append("\n💰 Precios:")
                for precio in precios:
                    if isinstance(precio, dict):
                        nombre_tier = precio.get('nombre', precio.get('tier', 'General'))
                        monto = precio.get('monto', precio.get('precio', precio.get('valor', 0)))
                        hora_limite = precio.get('hora_limite', precio.get('hasta', ''))
                        try:
                            monto_int = int(float(monto))
                        except (ValueError, TypeError):
                            monto_int = 0
                        if monto_int > 0:
                            if hora_limite:
                                respuesta_partes.append(f"   • {nombre_tier}: ${monto_int:,} hasta {hora_limite}")
                            else:
                                respuesta_partes.append(f"   • {nombre_tier}: ${monto_int:,}")
            
            respuesta_partes.append("\n\nNos vemos en la noche 💜✨")
            return "\n".join(respuesta_partes)
        
        elif intent == "estado_noche":
            if not evento_info:
                return "Hoy no tenemos evento programado 💜. Revisa nuestras redes para ver qué viene."
            
            # Usar contexto operativo para dar feeling
            feeling = "La noche está empezando 💜"
            if operational:
                sales = operational.get('sales', {})
                total_sales = sales.get('total_sales', 0)
                total_revenue = sales.get('total_revenue', 0)
                
                if total_sales > 50:
                    feeling = "La noche está súper movida 💜✨"
                elif total_sales > 20:
                    feeling = "La noche está movida 💜"
                elif total_sales > 0:
                    feeling = "La noche está empezando bien 💜"
                else:
                    feeling = "La noche está recién empezando 💜"
            
            nombre_evento = evento_info.get('nombre_evento', 'La noche')
            return f"{feeling}. {nombre_evento} está en curso. ¡Ven a disfrutar! 💜✨"
        
        elif intent == "proximos_eventos":
            programacion_service = ProgramacionService()
            eventos = programacion_service.get_upcoming_events(limit=5)
            
            if not eventos or len(eventos) == 0:
                return "No tenemos eventos próximos cargados aún 💜. Revisa nuestras redes para estar al día."
            
            respuesta_partes = ["📅 **Próximos eventos:**\n"]
            for evento in eventos[:5]:
                fecha = evento.get('fecha', '')
                nombre = evento.get('nombre_evento', 'Evento')
                respuesta_partes.append(f"• {fecha}: {nombre}")
            
            respuesta_partes.append("\n💜 ¡Te esperamos!")
            return "\n".join(respuesta_partes)
        
        elif intent == "precios":
            if not evento_info:
                return "No hay evento programado para hoy 💜. Revisa nuestras redes para ver precios de próximos eventos."
            
            precios = evento_info.get('precios', [])
            if not precios or (isinstance(precios, list) and len(precios) == 0):
                return "No tenemos información de precios cargada para hoy 💜. Contacta directamente para más info."
            
            respuesta_partes = ["💰 **Precios de hoy:**\n"]
            if isinstance(precios, list):
                for precio in precios:
                    if isinstance(precio, dict):
                        nombre_tier = precio.get('nombre', precio.get('tier', 'General'))
                        monto = precio.get('monto', precio.get('precio', precio.get('valor', 0)))
                        hora_limite = precio.get('hora_limite', precio.get('hasta', ''))
                        try:
                            monto_int = int(float(monto))
                        except (ValueError, TypeError):
                            monto_int = 0
                        if monto_int > 0:
                            if hora_limite:
                                respuesta_partes.append(f"• {nombre_tier}: ${monto_int:,} hasta {hora_limite}")
                            else:
                                respuesta_partes.append(f"• {nombre_tier}: ${monto_int:,}")
            
            respuesta_partes.append("\n💜 ¡Nos vemos!")
            return "\n".join(respuesta_partes)
        
        elif intent == "horario":
            if not evento_info:
                return "No hay evento programado para hoy 💜."
            
            horario = evento_info.get('horario', '')
            if horario:
                return f"🕐 **Horario de hoy:** {horario}\n\n💜 ¡Te esperamos!"
            else:
                return "No tenemos el horario cargado para hoy 💜. Revisa nuestras redes para más info."
        
        elif intent == "lista":
            if not evento_info:
                return "No hay evento programado para hoy 💜."
            
            info_lista = evento_info.get('lista', '')
            if info_lista:
                return f"📋 {info_lista}\n\n💜 ¡Nos vemos!"
            else:
                return "No tenemos información de lista para hoy 💜. Contacta directamente para reservas."
        
        elif intent == "djs":
            if not evento_info:
                return "No hay evento programado para hoy 💜."
            
            respuesta_partes = []
            dj_principal = evento_info.get('dj_principal', '')
            otros_djs = evento_info.get('otros_djs', '')
            
            if dj_principal:
                respuesta_partes.append(f"🎧 **DJ Principal:** {dj_principal}")
            if otros_djs:
                respuesta_partes.append(f"🎵 **También:** {otros_djs}")
            
            if not respuesta_partes:
                return "No tenemos información de DJs cargada para hoy 💜."
            
            respuesta_partes.append("\n💜 ¡Ven a disfrutar la música!")
            return "\n".join(respuesta_partes)
        
        return ""
    
    @staticmethod
    def generar_respuesta_simple(mensaje_usuario: str, canal: str = "interno") -> str:
        """
        DEPRECATED: Usar generar_respuesta() en su lugar.
        Mantenido por compatibilidad.
        """
        resultado = BimbaBotEngine.generar_respuesta(mensaje_usuario, canal)
        return resultado[0] if isinstance(resultado, tuple) else resultado
    
    @staticmethod
    def generar_respuesta(mensaje_usuario: str, canal: str = "interno") -> Tuple[str, str]:
        """
        Genera una respuesta usando el sistema de 3 capas:
        1. Reglas duras (rule-based)
        2. Contexto operativo (para feeling)
        3. OpenAI (si no hay match en reglas)
        
        Args:
            mensaje_usuario: Mensaje del usuario
            canal: Canal de comunicación (interno, web, instagram, whatsapp)
            
        Returns:
            Tuple[str, str]: (respuesta, source) donde source es "rule_based" o None
            Si source es None, significa que debe usar OpenAI
        """
        # Obtener información del evento de hoy
        programacion_service = ProgramacionService()
        evento_info = programacion_service.get_public_info_for_today()
        
        # Obtener contexto operativo (para feeling en reglas)
        operational = OperationalInsightsService.get_daily_summary()
        
        # Detectar intención
        intent = BimbaBotEngine._detect_intent(mensaje_usuario)
        
        if intent:
            # Generar respuesta basada en reglas
            respuesta = BimbaBotEngine._generate_rule_based_response(
                intent, evento_info, operational
            )
            if respuesta:
                return (respuesta, "rule_based")
        
        # Si no hay match en reglas, retornar None para usar OpenAI
        return (None, None)


