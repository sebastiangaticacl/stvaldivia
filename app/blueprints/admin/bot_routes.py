"""
Rutas del Bot de IA (BimbaBot) para el Panel de Control
"""
import uuid
import os
import subprocess
import tempfile
import shutil
import re
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, current_app, jsonify
from app.models import db
from app.models.bot_log_models import BotLog
from app.application.services.bot_log_service import BotLogService

# Importar el blueprint desde __init__.py
from . import admin_bp


@admin_bp.route('/bot/logs', methods=['GET'])
def bot_logs():
    """
    Vista de logs del bot de IA.
    Renderiza admin/bot_logs.html con los logs filtrados.
    """
    # Verificar autenticación
    if not session.get('admin_logged_in'):
        flash("Debes iniciar sesión como administrador.", "error")
        return redirect(url_for('auth.login_admin'))
    
    try:
        service = BotLogService()
        
        # Leer filtros desde request.args con valores por defecto
        canal = request.args.get('canal', 'todos')
        direccion = request.args.get('direccion', 'todas')
        estado = request.args.get('estado', 'todos')
        limite = request.args.get('limite', type=int) or 100
        
        # Validar límite
        if limite < 1 or limite > 500:
            limite = 100
        
        # Traducir "todos"/"todas" -> None para pasar al servicio
        canal_filter = None if canal == 'todos' else canal
        direction_filter = None if direccion == 'todas' else direccion
        status_filter = None if estado == 'todos' else estado
        
        # Obtener logs usando el servicio
        logs = service.get_recent_logs(
            limit=limite,
            canal=canal_filter,
            direction=direction_filter,
            status=status_filter
        )
        
        # Obtener canales únicos para el selector de filtro
        canales_unicos = db.session.query(BotLog.canal).distinct().all()
        canales = [c[0] for c in canales_unicos if c[0]]
        
        # Verificar si es superadmin
        username = session.get('admin_username', '').lower()
        is_superadmin = (username == 'sebagatica')
        
        # Pasar logs y valores de filtro actuales al template
        return render_template(
            'admin/bot_logs.html',
            logs=logs,
            canales=canales,
            filtro_canal=canal,
            filtro_direction=direccion,
            filtro_status=estado,
            limit=limite,
            is_superadmin=is_superadmin
        )
        
    except Exception as e:
        current_app.logger.error(f"Error al cargar logs del bot: {e}", exc_info=True)
        flash(f'Error al cargar logs: {str(e)}', 'error')
        # Verificar si es superadmin incluso en caso de error
        username = session.get('admin_username', '').lower()
        is_superadmin = (username == 'sebagatica')
        return render_template('admin/bot_logs.html', logs=[], canales=[], 
                             filtro_canal='todos', filtro_direction='todas', 
                             filtro_status='todos', limit=100,
                             is_superadmin=is_superadmin)


@admin_bp.route('/bot/test', methods=['POST'])
def bot_test():
    """
    Endpoint para probar el bot y registrar logs.
    Se activa cuando el usuario presiona "Probar Respuesta" en la consola de prueba.
    """
    # Verificar autenticación
    if not session.get('admin_logged_in'):
        flash("Debes iniciar sesión como administrador.", "error")
        return redirect(url_for('auth.login_admin'))
    
    try:
        service = BotLogService()
        
        # Leer desde request.form
        canal = request.form.get('canal', 'interno').strip()
        mensaje_usuario = request.form.get('mensaje_usuario', '').strip()
        
        # Si mensaje_usuario viene vacío → redirigir a /admin/bot/logs
        if not mensaje_usuario:
            flash('El mensaje no puede estar vacío.', 'error')
            return redirect(url_for('admin.bot_logs'))
        
        # Generar un conversation_id usando uuid4()
        conversation_id = str(uuid.uuid4())
        
        # Registrar el mensaje del usuario
        service.log_user_message(
            canal=canal,
            conversation_id=conversation_id,
            message=mensaje_usuario,
            meta={"origin": "admin_test_console"}
        )
        
        # Verificar si es superadmin para obtener información detallada
        username = session.get('admin_username', '').lower()
        is_superadmin = (username == 'sebagatica')
        
        # Usar el mismo sistema que la API para obtener respuesta completa
        from app.application.services.programacion_service import ProgramacionService
        from app.application.services.operational_insights_service import OperationalInsightsService
        from app.application.services.intent_router import IntentRouter
        from app.application.services.bot_rule_engine import BotRuleEngine
        from app.infrastructure.external.openai_client import OpenAIAPIClient
        from app.prompts.prompts_bimba import get_prompt_maestro_bimba
        import json
        
        # Obtener contexto
        evento_info = ProgramacionService().get_public_info_for_today()
        operational = OperationalInsightsService.get_daily_summary()
        intent = IntentRouter.detectar_intent(mensaje_usuario)
        
        # Intentar generar respuesta con reglas primero
        respuesta = None
        source = None
        modelo_usado = None
        tokens_info = None
        
        respuesta_rule = BotRuleEngine.generar_respuesta(intent, evento_info, operational)
        if respuesta_rule:
            respuesta = respuesta_rule
            source = "rule_based"
            modelo_usado = "rule_based"
        else:
            # Si no hay respuesta por reglas, intentar con OpenAI
            try:
                # Formatear contexto para el prompt
                evento_str = json.dumps(evento_info, ensure_ascii=False, indent=2) if evento_info else "null"
                operational_str = json.dumps(operational, ensure_ascii=False, indent=2) if operational else "None"
                
                system_prompt = get_prompt_maestro_bimba(evento_str, operational_str)
                
                client = OpenAIAPIClient()
                openai_client = client._get_client()
                
                if openai_client:
                    formatted_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": mensaje_usuario}
                    ]
                    
                    import openai
                    response = openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=formatted_messages,
                        temperature=0.7,
                        max_tokens=500
                    )
                    
                    if response.choices and len(response.choices) > 0:
                        respuesta = response.choices[0].message.content.strip()
                        source = "openai"
                        modelo_usado = "gpt-4o-mini"
                        
                        if response.usage:
                            tokens_info = {
                                "input": response.usage.prompt_tokens,
                                "output": response.usage.completion_tokens,
                                "total": response.usage.total_tokens
                            }
                else:
                    # OpenAI no disponible - usar fallback con reglas
                    if is_superadmin:
                        respuesta = f"Hola! 💜 Soy BIMBA. (Superadmin: Intent={intent or 'unknown'}, OpenAI no disponible)"
                        source = "superadmin_fallback"
                    else:
                        respuesta = "Hola! 💜 Soy BIMBA. Puedo ayudarte con información sobre eventos, horarios, precios y más. ¿Qué te gustaría saber? 💜✨"
                        source = "fallback_contextual"
                    modelo_usado = None
            except Exception as e:
                current_app.logger.error(f"Error al generar respuesta con OpenAI: {e}", exc_info=True)
                if is_superadmin:
                    respuesta = f"Hola! 💜 Soy BIMBA. (Superadmin: Error={str(e)[:50]})"
                    source = "error"
                else:
                    respuesta = "Hola! 💜 Soy BIMBA. No pude generar una respuesta en este momento. 💜✨"
                    source = "error"
                modelo_usado = None
        
        # Asegurar que respuesta no sea None
        if not respuesta:
            respuesta = "Lo siento, no pude generar una respuesta."
            source = source or "fallback"
        
        # Meta información adicional para superadmin
        meta_data = {"origin": "admin_test_console"}
        if is_superadmin:
            meta_data["is_superadmin"] = True
            meta_data["source"] = source or "unknown"
            meta_data["intent"] = intent or "unknown"
            if tokens_info:
                meta_data["tokens"] = tokens_info
        
        # Registrar la respuesta del bot
        service.log_bot_response(
            canal=canal,
            conversation_id=conversation_id,
            message=respuesta,
            model=modelo_usado or "fallback",
            status="success",
            meta=meta_data
        )
        
        # Redirigir nuevamente a /admin/bot/logs para que los logs aparezcan en pantalla
        flash('Mensaje de prueba registrado correctamente. El agente BIMBA ha respondido.', 'success')
        return redirect(url_for('admin.bot_logs'))
        
    except Exception as e:
        current_app.logger.error(f"Error en test del bot: {e}", exc_info=True)
        flash(f'Error al procesar mensaje: {str(e)}', 'error')
        return redirect(url_for('admin.bot_logs'))


@admin_bp.route('/bot/config', methods=['GET'])
def bot_config():
    """
    Vista de configuración del bot BIMBA.
    Muestra la configuración del agente oficial encargado de redes sociales.
    """
    # Verificar autenticación
    if not session.get('admin_logged_in'):
        flash("Debes iniciar sesión como administrador.", "error")
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Verificar si es superadmin
        username = session.get('admin_username', '').lower()
        is_superadmin = (username == 'sebagatica')
        
        # Obtener configuración actual
        from app.infrastructure.external.openai_client import OpenAIAPIClient
        import os
        
        # Información de OpenAI
        openai_api_key = current_app.config.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY')
        openai_org_id = current_app.config.get('OPENAI_ORGANIZATION_ID') or os.environ.get('OPENAI_ORGANIZATION_ID')
        openai_project_id = current_app.config.get('OPENAI_PROJECT_ID') or os.environ.get('OPENAI_PROJECT_ID')
        openai_model = current_app.config.get('OPENAI_DEFAULT_MODEL', 'gpt-4o-mini')
        openai_temperature = float(current_app.config.get('OPENAI_DEFAULT_TEMPERATURE', 0.7))
        
        # Verificar si OpenAI está disponible
        openai_available = False
        openai_status = "No configurado"
        if openai_api_key:
            client = OpenAIAPIClient()
            openai_client = client._get_client()
            if openai_client:
                openai_available = True
                openai_status = "✅ Configurado y disponible"
            else:
                openai_status = "⚠️ API Key presente pero no se pudo inicializar"
        else:
            openai_status = "❌ API Key no configurada"
        
        # Información operacional
        operational_api_base = os.environ.get('BIMBA_INTERNAL_API_BASE_URL')
        operational_api_key = os.environ.get('BIMBA_INTERNAL_API_KEY')
        operational_enabled = bool(operational_api_base and operational_api_key)
        
        # Timeouts configurados
        openai_timeout = 5.0  # Definido en el código
        operational_timeout = 2.0  # Definido en operational_insights_service
        
        # Información de reglas e intents
        from app.application.services.intent_router import IntentRouter
        intents_available = [
            IntentRouter.INTENT_EVENTO_HOY,
            IntentRouter.INTENT_ESTADO_NOCHE,
            IntentRouter.INTENT_PROXIMOS_EVENTOS,
            IntentRouter.INTENT_PRECIOS,
            IntentRouter.INTENT_HORARIO,
            IntentRouter.INTENT_LISTA,
            IntentRouter.INTENT_DJS,
            IntentRouter.INTENT_COMO_FUNCIONA,
            IntentRouter.INTENT_SALUDO,
        ]
        
        config_info = {
            'openai': {
                'available': openai_available,
                'status': openai_status,
                'api_key_configured': bool(openai_api_key),
                'api_key_preview': f"{openai_api_key[:10]}..." if openai_api_key and is_superadmin else "***",
                'org_id': openai_org_id if is_superadmin else None,
                'project_id': openai_project_id if is_superadmin else None,
                'model': openai_model,
                'temperature': openai_temperature,
                'timeout': openai_timeout,
            },
            'operational': {
                'enabled': operational_enabled,
                'api_base': operational_api_base if is_superadmin else None,
                'api_key_configured': bool(operational_api_key),
                'timeout': operational_timeout,
            },
            'intents': {
                'available': intents_available,
                'count': len(intents_available),
            },
            'system': {
                'rules_enabled': True,
                'openai_enabled': openai_available,
                'fallback_enabled': True,
            }
        }
        
        return render_template(
            'admin/bot_config.html',
            config=config_info,
            is_superadmin=is_superadmin
        )
        
    except Exception as e:
        current_app.logger.error(f"Error al cargar configuración del bot: {e}", exc_info=True)
        flash(f'Error al cargar configuración: {str(e)}', 'error')
        return redirect(url_for('admin.bot_logs'))


@admin_bp.route('/bot/env-vars', methods=['GET'])
def bot_env_vars():
    """
    Vista para gestionar variables de entorno del bot (solo superadmin).
    Permite ver y modificar variables del servicio systemd.
    """
    # Verificar autenticación
    if not session.get('admin_logged_in'):
        flash("Debes iniciar sesión como administrador.", "error")
        return redirect(url_for('auth.login_admin'))
    
    # Verificar si es superadmin
    username = session.get('admin_username', '').lower()
    is_superadmin = (username == 'sebagatica')
    
    if not is_superadmin:
        flash("Solo el superadministrador puede gestionar variables de entorno.", "error")
        return redirect(url_for('admin.bot_config'))
    
    try:
        import os
        import subprocess
        
        # Variables que se pueden gestionar
        manageable_vars = {
            'OPENAI_API_KEY': {
                'label': 'OpenAI API Key',
                'description': 'Clave de API de OpenAI para IA generativa',
                'required': True,
                'type': 'password',
                'current': os.environ.get('OPENAI_API_KEY', '')
            },
            'OPENAI_ORGANIZATION_ID': {
                'label': 'OpenAI Organization ID',
                'description': 'ID de organización de OpenAI (opcional)',
                'required': False,
                'type': 'text',
                'current': os.environ.get('OPENAI_ORGANIZATION_ID', '')
            },
            'OPENAI_PROJECT_ID': {
                'label': 'OpenAI Project ID',
                'description': 'ID de proyecto de OpenAI (opcional, requerido para Admin Keys)',
                'required': False,
                'type': 'text',
                'current': os.environ.get('OPENAI_PROJECT_ID', '')
            },
            'BIMBA_INTERNAL_API_KEY': {
                'label': 'API Operacional - API Key',
                'description': 'Clave de API para la API operacional interna',
                'required': False,
                'type': 'password',
                'current': os.environ.get('BIMBA_INTERNAL_API_KEY', '')
            },
            'BIMBA_INTERNAL_API_BASE_URL': {
                'label': 'API Operacional - Base URL',
                'description': 'URL base de la API operacional (normalmente http://127.0.0.1:5001)',
                'required': False,
                'type': 'text',
                'current': os.environ.get('BIMBA_INTERNAL_API_BASE_URL', '')
            },
            'SMTP_SERVER': {
                'label': 'SMTP Server',
                'description': 'Servidor SMTP para envío de emails',
                'required': False,
                'type': 'text',
                'current': os.environ.get('SMTP_SERVER', '')
            },
            'SMTP_PORT': {
                'label': 'SMTP Port',
                'description': 'Puerto SMTP (587 para TLS, 465 para SSL)',
                'required': False,
                'type': 'text',
                'current': os.environ.get('SMTP_PORT', '')
            },
            'SMTP_USER': {
                'label': 'SMTP User',
                'description': 'Usuario SMTP',
                'required': False,
                'type': 'text',
                'current': os.environ.get('SMTP_USER', '')
            },
            'SMTP_PASSWORD': {
                'label': 'SMTP Password',
                'description': 'Contraseña SMTP',
                'required': False,
                'type': 'password',
                'current': os.environ.get('SMTP_PASSWORD', '')
            },
            'SMTP_FROM': {
                'label': 'SMTP From',
                'description': 'Email remitente',
                'required': False,
                'type': 'text',
                'current': os.environ.get('SMTP_FROM', '')
            }
        }
        
        # Intentar leer variables del servicio systemd
        service_file = '/etc/systemd/system/stvaldivia.service'
        systemd_vars = {}
        
        try:
            if os.path.exists(service_file):
                with open(service_file, 'r') as f:
                    content = f.read()
                    # Buscar líneas Environment="VAR=value"
                    import re
                    for line in content.split('\n'):
                        match = re.match(r'Environment="([^=]+)=(.*)"', line)
                        if match:
                            var_name = match.group(1)
                            var_value = match.group(2)
                            systemd_vars[var_name] = var_value
                            
                            # Actualizar valores actuales si están en systemd
                            if var_name in manageable_vars:
                                manageable_vars[var_name]['current'] = var_value
        except Exception as e:
            current_app.logger.warning(f"No se pudo leer archivo systemd: {e}")
        
        return render_template(
            'admin/bot_env_vars.html',
            vars=manageable_vars,
            systemd_vars=systemd_vars,
            service_file=service_file,
            is_superadmin=is_superadmin
        )
        
    except Exception as e:
        current_app.logger.error(f"Error al cargar variables de entorno: {e}", exc_info=True)
        flash(f'Error al cargar variables: {str(e)}', 'error')
        return redirect(url_for('admin.bot_config'))


@admin_bp.route('/bot/env-vars/update', methods=['POST'])
def bot_env_vars_update():
    """
    Actualiza variables de entorno en el servicio systemd (solo superadmin).
    """
    # Verificar autenticación
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    # Verificar si es superadmin
    username = session.get('admin_username', '').lower()
    is_superadmin = (username == 'sebagatica')
    
    if not is_superadmin:
        return jsonify({'success': False, 'message': 'Solo el superadministrador puede modificar variables'}), 403
    
    try:
        import subprocess
        import tempfile
        import shutil
        from datetime import datetime
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Datos requeridos'}), 400
        
        # Variables permitidas para modificar
        allowed_vars = [
            'OPENAI_API_KEY', 'OPENAI_ORGANIZATION_ID', 'OPENAI_PROJECT_ID',
            'BIMBA_INTERNAL_API_KEY', 'BIMBA_INTERNAL_API_BASE_URL',
            'SMTP_SERVER', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM'
        ]
        
        service_file = '/etc/systemd/system/stvaldivia.service'
        
        if not os.path.exists(service_file):
            return jsonify({'success': False, 'message': 'Archivo de servicio no encontrado'}), 404
        
        # Leer archivo actual
        with open(service_file, 'r') as f:
            content = f.read()
        
        # Crear backup
        backup_file = f"{service_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(service_file, backup_file)
        
        # Procesar cada variable
        lines = content.split('\n')
        new_lines = []
        vars_to_add = {}
        
        for var_name in allowed_vars:
            if var_name in data:
                var_value = data[var_name].strip()
                vars_to_add[var_name] = var_value
        
        # Eliminar líneas Environment existentes de variables que vamos a actualizar
        for line in lines:
            should_skip = False
            for var_name in vars_to_add.keys():
                if line.strip().startswith(f'Environment="{var_name}='):
                    should_skip = True
                    break
            if not should_skip:
                new_lines.append(line)
        
        # Encontrar posición de ExecStart para insertar antes
        exec_start_idx = None
        for i, line in enumerate(new_lines):
            if line.strip().startswith('ExecStart='):
                exec_start_idx = i
                break
        
        if exec_start_idx is None:
            return jsonify({'success': False, 'message': 'No se encontró ExecStart en el servicio'}), 500
        
        # Insertar nuevas variables antes de ExecStart
        env_lines = []
        for var_name, var_value in vars_to_add.items():
            if var_value:  # Solo agregar si tiene valor
                env_lines.append(f'Environment="{var_name}={var_value}"')
        
        # Insertar líneas
        new_lines[exec_start_idx:exec_start_idx] = env_lines
        
        # Escribir archivo temporal
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.service')
        temp_file.write('\n'.join(new_lines))
        temp_file.close()
        
        # Intentar copiar archivo temporal al destino con sudo
        # Nota: Esto requiere que el usuario que ejecuta la app tenga permisos sudo sin contraseña
        # O que se configure apropiadamente en el servidor
        try:
            result = subprocess.run(
                ['sudo', 'cp', temp_file.name, service_file],
                capture_output=True,
                text=True,
                timeout=10
            )
        except subprocess.TimeoutExpired:
            os.unlink(temp_file.name)
            return jsonify({
                'success': False,
                'message': 'Timeout al ejecutar comando sudo. Verifica permisos del servidor.'
            }), 500
        except Exception as e:
            os.unlink(temp_file.name)
            return jsonify({
                'success': False,
                'message': f'Error al ejecutar sudo: {str(e)}. Verifica que la aplicación tenga permisos sudo configurados.'
            }), 500
        
        # Limpiar archivo temporal
        os.unlink(temp_file.name)
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'message': f'Error al escribir archivo: {result.stderr}. Verifica permisos sudo.'
            }), 500
        
        # Recargar systemd
        try:
            reload_result = subprocess.run(
                ['sudo', 'systemctl', 'daemon-reload'],
                capture_output=True,
                text=True,
                timeout=10
            )
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error al recargar systemd: {str(e)}'
            }), 500
        
        if reload_result.returncode != 0:
            return jsonify({
                'success': False,
                'message': f'Error al recargar systemd: {reload_result.stderr}'
            }), 500
        
        # Reiniciar servicio
        try:
            restart_result = subprocess.run(
                ['sudo', 'systemctl', 'restart', 'stvaldivia.service'],
                capture_output=True,
                text=True,
                timeout=30
            )
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error al reiniciar servicio: {str(e)}'
            }), 500
        
        if restart_result.returncode != 0:
            return jsonify({
                'success': False,
                'message': f'Error al reiniciar servicio: {restart_result.stderr}'
            }), 500
        
        current_app.logger.info(f"Variables de entorno actualizadas por {username}: {list(vars_to_add.keys())}")
        
        return jsonify({
            'success': True,
            'message': 'Variables actualizadas correctamente. Servicio reiniciado.',
            'backup': backup_file
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al actualizar variables: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


