"""
Prompts maestros para el agente de IA BIMBA
"""
from .bimba_system_knowledge import BIMBA_SYSTEM_KNOWLEDGE

def build_programacion_context(eventos_json):
    """
    Formatea eventos en un string corto y ordenado.
    
    Args:
        eventos_json: Lista de dicts con información de eventos, o un string JSON, o "null"
        
    Returns:
        String formateado con la programación
    """
    from datetime import datetime
    import json
    
    # Si es string, parsearlo
    if isinstance(eventos_json, str):
        if eventos_json == "null" or not eventos_json or eventos_json.strip() == "null":
            return "(no hay eventos cargados en el sistema para los próximos días)"
        try:
            eventos_json = json.loads(eventos_json)
        except (json.JSONDecodeError, AttributeError):
            return "(error al procesar programación)"
    
    # Si es un solo evento (dict), convertirlo a lista
    if isinstance(eventos_json, dict):
        eventos_json = [eventos_json]
    
    # Si no es lista, devolver mensaje de error
    if not isinstance(eventos_json, list):
        return "(formato de programación no válido)"
    
    if not eventos_json:
        return "(no hay eventos cargados en el sistema para los próximos días)"
    
    lineas = []
    for e in eventos_json:
        # Manejar fecha (puede venir como ISO string o Date object)
        fecha_raw = e.get("fecha") or e.get("fecha_evento")
        if not fecha_raw:
            continue
        
        try:
            if isinstance(fecha_raw, str):
                fecha_legible = datetime.fromisoformat(fecha_raw.replace('Z', '+00:00')).strftime("%d-%m-%Y")
            else:
                fecha_legible = fecha_raw.strftime("%d-%m-%Y") if hasattr(fecha_raw, 'strftime') else str(fecha_raw)
        except (ValueError, AttributeError):
            fecha_legible = str(fecha_raw)
        
        nombre = e.get("nombre_evento", "Evento sin nombre")
        
        # Manejar DJs - puede venir como lista o como strings separados
        djs_list = []
        if "djs" in e and isinstance(e["djs"], list):
            djs_list = e["djs"]
        else:
            # Construir lista desde dj_principal y otros_djs
            if e.get("dj_principal"):
                djs_list.append(e["dj_principal"])
            if e.get("otros_djs"):
                otros = e["otros_djs"]
                if isinstance(otros, str):
                    djs_list.extend([d.strip() for d in otros.split(",") if d.strip()])
                elif isinstance(otros, list):
                    djs_list.extend(otros)
        
        djs = ", ".join(djs_list) if djs_list else "DJs por confirmar"
        
        # Manejar cover/precios
        rango_cover = ""
        if "cover_desde" in e and "cover_hasta" in e:
            # Formato nuevo con cover_desde/hasta
            if e["cover_desde"] and e["cover_hasta"]:
                rango_cover = f"${e['cover_desde']:,} a ${e['cover_hasta']:,}".replace(",", ".")
            elif e["cover_desde"]:
                rango_cover = f"desde ${e['cover_desde']:,}".replace(",", ".")
            else:
                rango_cover = "por confirmar"
        elif "precios" in e and e["precios"]:
            # Formato antiguo con tiers de precios
            precios = e["precios"]
            if isinstance(precios, list) and len(precios) > 0:
                montos = []
                for p in precios:
                    if isinstance(p, dict):
                        monto = p.get("monto") or p.get("precio") or p.get("valor")
                        if monto:
                            try:
                                montos.append(float(monto))
                            except (ValueError, TypeError):
                                pass
                if montos:
                    min_precio = min(montos)
                    max_precio = max(montos)
                    if min_precio == max_precio:
                        rango_cover = f"${int(min_precio):,}".replace(",", ".")
                    else:
                        rango_cover = f"${int(min_precio):,} a ${int(max_precio):,}".replace(",", ".")
                else:
                    rango_cover = "por confirmar"
            else:
                rango_cover = "por confirmar"
        else:
            rango_cover = "por confirmar"
        
        # Manejar horario
        hora_apertura = ""
        hora_cierre = ""
        if "hora_apertura" in e:
            hora_apertura = e["hora_apertura"]
        elif "horario_apertura_publico" in e:
            hora_apertura = e["horario_apertura_publico"]
        elif "horario" in e:
            # Puede venir como "23:00 a 04:00"
            horario_str = e["horario"]
            if " a " in horario_str:
                partes = horario_str.split(" a ")
                hora_apertura = partes[0].strip()
                if len(partes) > 1:
                    hora_cierre = partes[1].strip()
        
        if not hora_cierre:
            if "hora_cierre" in e:
                hora_cierre = e["hora_cierre"]
            elif "horario_cierre_publico" in e:
                hora_cierre = e["horario_cierre_publico"]
            else:
                hora_cierre = "tarde"
        
        horario_str = f"{hora_apertura}–{hora_cierre}" if hora_apertura else "horario por confirmar"
        
        # Manejar lista
        lista_txt = ""
        if "lista_hasta_hora" in e and e["lista_hasta_hora"]:
            lista_txt = f"Lista hasta las {e['lista_hasta_hora']}"
        elif "lista" in e and e["lista"]:
            lista_txt = e["lista"]
        elif "info_lista" in e and e["info_lista"]:
            lista_txt = e["info_lista"]
        else:
            lista_txt = "Sin info de lista"
        
        linea = (
            f"- {fecha_legible} · {nombre} · "
            f"{horario_str} · "
            f"DJs: {djs} · Cover: {rango_cover} · {lista_txt}"
        )
        lineas.append(linea)
    
    if not lineas:
        return "(no hay eventos cargados en el sistema para los próximos días)"
    
    return "\n".join(lineas)


def _format_programacion_context(evento_str: str) -> str:
    """
    Formatea el contexto de programación usando build_programacion_context.
    Wrapper para mantener compatibilidad.
    
    Args:
        evento_str: JSON string con información del evento
        
    Returns:
        String formateado con la programación, incluyendo el header "PROGRAMACIÓN ACTUAL:"
    """
    resultado = build_programacion_context(evento_str)
    
    # Si el resultado ya incluye "PROGRAMACIÓN ACTUAL:", devolverlo tal cual
    if resultado.startswith("PROGRAMACIÓN ACTUAL:"):
        return resultado
    
    # Si no, agregarlo
    return f"PROGRAMACIÓN ACTUAL:\n{resultado}"


def get_prompt_maestro_bimba(evento_str: str = "null", operacional_str: str = "None", canal: str = "publico") -> str:
    """
    Obtiene el prompt maestro de BIMBA_NUCLEAR.
    
    Args:
        evento_str: JSON string con información de eventos (programación)
        operacional_str: JSON string con información operativa (ventas, métricas, etc.)
        canal: Canal de comunicación ("publico" o "admin")
    
    Returns:
        String con el prompt completo según el canal
    """
    programacion_formateada = _format_programacion_context(evento_str)
    
    # Construir contexto de datos operativos solo para canal admin
    contexto_operativo = ""
    if canal == "admin" and operacional_str and operacional_str != "None":
        try:
            import json
            datos_operativos = json.loads(operacional_str) if isinstance(operacional_str, str) else operacional_str
            contexto_operativo = f"\n\n═══════════════════════════════════════════════════════════════\nDATOS OPERATIVOS (Solo para análisis interno)\n═══════════════════════════════════════════════════════════════\n\n{operacional_str}\n"
        except:
            contexto_operativo = ""
    
    prompt_base = f"""Eres BIMBA, la voz digital oficial del Club BIMBA.

CANAL ACTUAL: {canal.upper()}

REGLAS DURAS:
- No te presentes (no digas "soy IA", "asistente", "bot").
- No repitas "puedo ayudarte con…".
- Responde corto: máx 2 líneas y 12 palabras total.
- No uses emojis (excepto opcional 👋 solo en el primer mensaje de la sesión).
- No hagas más de 1 pregunta (idealmente 0).
- No inventes información.
- No prometas cosas.
- No discutas ni justifiques.
- Si no sabes: di "Aún no está definido." y termina.

TONO:
- Sobrio, cercano, humano.
- Más silencio que relleno.
- Lenguaje del lugar, no administrativo.

PRINCIPIO:
Hablar menos es mejor que hablar bien.

═══════════════════════════════════════════════════════════════
"""
    
    if canal == "publico":
        prompt_canal = """MODO: CANAL PÚBLICO (RRSS/web/chat)

Responde preguntas sobre eventos, horarios, precios, DJs.
Usa la programación que viene en el contexto.
Si no hay datos, di "Aún no está definido."
Habla como persona del lugar, no como asistente.
"""
    elif canal == "admin":
        prompt_canal = """MODO 2: CANAL = "admin"
────────────────────────
- Estás hablando con Sebastián u otra persona del equipo de gestión de Bimba.
- Tu rol aquí es de ANALISTA y CONSEJERA de negocio.

Estilo:
- Directa, clara y honesta, pero manteniendo el tono Bimba (cercano).
- Puedes usar un poco de humor, pero cuidando que los números se expliquen bien.
- Aquí SÍ puedes hablar de ventas, gastos, márgenes, hot hours, eventos buenos y malos.

Temas que debes manejar:
- Análisis de eventos: ingresos, margen, asistencia relativa, ranking de "fiestas más efectivas".
- Hot hours: en qué horario se concentra la mayor parte de las ventas.
- Comparaciones: este finde vs finde pasado, Halloween vs Año Nuevo, etc.
- Alertas: detectar patrones raros, caídas de ventas, cambios en comportamiento del público.
- Sugerencias accionables: cambios de horario, precios, promos, refuerzo de preventas, etc.

Reglas:
- Usa SIEMPRE los datos que ven en el CONTEXTO (ventas, tickets, inventario) o las herramientas que te entreguen esa información.
- Si los datos son incompletos, dilo explícitamente y explica qué faltaría para un análisis mejor.
- Resume con foco: qué descubriste y qué harías tú para mejorar.
"""
    else:
        # Fallback si el canal no es reconocido
        prompt_canal = """MODO: CANAL DESCONOCIDO
────────────────────────
- Usa el modo público por defecto.
- Sé amable y ayuda con información general sobre Bimba.
"""
    
    prompt_programacion = f"""
═══════════════════════════════════════════════════════════════
PROGRAMACIÓN ACTUAL
═══════════════════════════════════════════════════════════════

{programacion_formateada}
"""
    
    prompt_final = """
═══════════════════════════════════════════════════════════════
INFORMACIÓN ADICIONAL
═══════════════════════════════════════════════════════════════

DIRECCIÓN: Independencia 543, Valdivia (Isla Teja).

Si no hay datos: di "Aún no está definido." y termina.
"""
    
    return prompt_base + prompt_canal + prompt_programacion + contexto_operativo + prompt_final


