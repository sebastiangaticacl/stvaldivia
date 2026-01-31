"""
Bot Rule Engine - Genera respuestas basadas en reglas duras
"""
from typing import Optional, Dict, Any
from app.application.services.programacion_service import ProgramacionService
from app.application.services.operational_insights_service import OperationalInsightsService
from app.application.services.intent_router import IntentRouter


class BotRuleEngine:
    """
    Motor de reglas para el bot BimbaBot.
    Genera respuestas basadas en reglas duras según la intención detectada.
    """
    
    @staticmethod
    def generar_respuesta(intent: str, evento_info: Optional[Dict[str, Any]] = None,
                         operational: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Genera una respuesta basada en reglas duras según la intención.
        
        Args:
            intent: Intención detectada (de IntentRouter)
            evento_info: Información del evento de hoy (opcional)
            operational: Información operativa del día (opcional)
            
        Returns:
            str: Respuesta generada o None si no hay regla para esta intención
        """
        if intent == IntentRouter.INTENT_UNKNOWN:
            return None
        
        if intent == IntentRouter.INTENT_EVENTO_HOY:
            return BotRuleEngine._respuesta_evento_hoy(evento_info)
        
        elif intent == IntentRouter.INTENT_ESTADO_NOCHE:
            return BotRuleEngine._respuesta_estado_noche(evento_info, operational)
        
        elif intent == IntentRouter.INTENT_PROXIMOS_EVENTOS:
            return BotRuleEngine._respuesta_proximos_eventos()
        
        elif intent == IntentRouter.INTENT_PRECIOS:
            return BotRuleEngine._respuesta_precios(evento_info)
        
        elif intent == IntentRouter.INTENT_HORARIO:
            return BotRuleEngine._respuesta_horario(evento_info)
        
        elif intent == IntentRouter.INTENT_LISTA:
            return BotRuleEngine._respuesta_lista(evento_info)
        
        elif intent == IntentRouter.INTENT_DJS:
            return BotRuleEngine._respuesta_djs(evento_info)
        
        elif intent == IntentRouter.INTENT_COMO_FUNCIONA:
            return BotRuleEngine._respuesta_como_funciona(evento_info)
        
        elif intent == IntentRouter.INTENT_SALUDO:
            # Los saludos NO usan reglas hardcodeadas para permitir respuestas variadas y naturales
            # Deben pasar a OpenAI para generar respuestas humanas según el prompt
            return None
        
        return None
    
    @staticmethod
    def _respuesta_evento_hoy(evento_info: Optional[Dict[str, Any]]) -> str:
        """Genera respuesta para consulta sobre evento de hoy (versión minimalista)"""
        if not evento_info:
            return "Hoy no hay evento."
        
        # Versión minimalista: solo lo esencial
        nombre_evento = evento_info.get('nombre_evento', 'Evento')
        horario = evento_info.get('horario', '')
        
        # Obtener precio mínimo
        precio_min = None
        precios = evento_info.get('precios', [])
        if precios and isinstance(precios, list):
            montos = []
            for precio in precios:
                if isinstance(precio, dict):
                    monto = precio.get('monto') or precio.get('precio') or precio.get('valor', 0)
                    try:
                        montos.append(float(monto))
                    except (ValueError, TypeError):
                        pass
            if montos:
                precio_min = min(montos)
        
        # Respuesta corta: máximo 2 líneas, 12 palabras
        respuesta = nombre_evento
        if horario:
            respuesta += f". {horario}"
        if precio_min:
            respuesta += f" Desde ${int(precio_min):,}."
        
        return respuesta
    
    @staticmethod
    def _respuesta_estado_noche(evento_info: Optional[Dict[str, Any]], 
                               operational: Optional[Dict[str, Any]]) -> str:
        """Genera respuesta para consulta sobre estado de la noche (versión minimalista)"""
        if not evento_info:
            return "Hoy está tranquilo."
        
        # Usar contexto operativo para dar feeling (sin emojis, corto)
        feeling = "Hoy está tranquilo."
        if operational:
            sales = operational.get('sales', {})
            total_sales = sales.get('total_sales', 0)
            
            if total_sales > 50:
                feeling = "Hoy está movido."
            elif total_sales > 20:
                feeling = "Hoy está bien."
            elif total_sales > 0:
                feeling = "Hoy está empezando."
        
        return feeling
    
    @staticmethod
    def _respuesta_proximos_eventos() -> str:
        """Genera respuesta para consulta sobre próximos eventos (versión minimalista)"""
        programacion_service = ProgramacionService()
        eventos = programacion_service.get_upcoming_events(limit=3)
        
        if not eventos or len(eventos) == 0:
            return "Aún no hay anuncio."
        
        # Versión corta: solo el próximo
        if len(eventos) > 0:
            evento = eventos[0]
            fecha = evento.get('fecha', '')
            nombre = evento.get('nombre_evento', 'Evento')
            return f"{fecha}: {nombre}"
        
        return "Aún no hay anuncio."
    
    @staticmethod
    def _respuesta_precios(evento_info: Optional[Dict[str, Any]]) -> str:
        """Genera respuesta para consulta sobre precios (versión minimalista)"""
        if not evento_info:
            return "Aún no está definido."
        
        precios = evento_info.get('precios', [])
        if not precios or (isinstance(precios, list) and len(precios) == 0):
            return "Aún no está definido."
        
        # Obtener precio mínimo
        montos = []
        for precio in precios:
            if isinstance(precio, dict):
                monto = precio.get('monto') or precio.get('precio') or precio.get('valor', 0)
                try:
                    montos.append(float(monto))
                except (ValueError, TypeError):
                    pass
        
        if montos:
            precio_min = min(montos)
            return f"Entrada desde ${int(precio_min):,}."
        
        return "Aún no está definido."
    
    @staticmethod
    def _respuesta_horario(evento_info: Optional[Dict[str, Any]]) -> str:
        """Genera respuesta para consulta sobre horario (versión minimalista)"""
        if not evento_info:
            return "Abrimos a las 23:00."
        
        horario = evento_info.get('horario', '')
        hora_apertura = evento_info.get('hora_apertura', '23:00')
        
        if horario:
            # Extraer solo la hora de apertura si viene como "23:00 a 04:00"
            if " a " in horario:
                hora_apertura = horario.split(" a ")[0].strip()
            else:
                hora_apertura = horario
        elif hora_apertura:
            hora_apertura = hora_apertura
        
        return f"Abrimos a las {hora_apertura}."
    
    @staticmethod
    def _respuesta_lista(evento_info: Optional[Dict[str, Any]]) -> str:
        """Genera respuesta para consulta sobre lista/reservas (versión minimalista)"""
        if not evento_info:
            return "Se anuncia el mismo día."
        
        info_lista = evento_info.get('lista', '')
        lista_hasta = evento_info.get('lista_hasta_hora', '')
        
        if lista_hasta:
            return f"Lista hasta las {lista_hasta}."
        elif info_lista:
            return info_lista[:50]  # Máximo 50 caracteres
        else:
            return "Se anuncia el mismo día."
    
    @staticmethod
    def _respuesta_djs(evento_info: Optional[Dict[str, Any]]) -> str:
        """Genera respuesta para consulta sobre DJs (versión minimalista)"""
        if not evento_info:
            return "Se anuncia el mismo día."
        
        dj_principal = evento_info.get('dj_principal', '')
        otros_djs = evento_info.get('otros_djs', '')
        
        if dj_principal:
            if otros_djs:
                return f"{dj_principal}, {otros_djs}"
            return dj_principal
        elif otros_djs:
            return otros_djs
        
        return "Se anuncia el mismo día."
    
    @staticmethod
    def _respuesta_como_funciona(evento_info: Optional[Dict[str, Any]] = None) -> str:
        """Genera respuesta para preguntas sobre cómo funciona el sistema (versión minimalista)"""
        return "Llegas, entras, y listo."
    
    @staticmethod
    def _respuesta_saludo(evento_info: Optional[Dict[str, Any]]) -> str:
        """
        DEPRECATED: Los saludos ahora pasan a OpenAI para respuestas variadas y naturales.
        Este método se mantiene solo por compatibilidad pero nunca debería ser llamado.
        """
        # No usar respuestas hardcodeadas para saludos
        # Deben pasar a OpenAI para generar respuestas humanas y variadas
        return None


