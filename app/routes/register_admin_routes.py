"""
Rutas de administración de cajas registradoras
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app.models import db
from app.models.pos_models import PosRegister
from app.models.product_models import Product
from datetime import datetime
from flask import current_app
from app.helpers.printer_helper import PrinterHelper
from app.helpers.seed_test_data import seed_test_register_and_product, seed_test_cashier_user  # TEST / QA ONLY – DO NOT USE IN PROD LOGIC
import json
import logging

logger = logging.getLogger(__name__)

register_admin_bp = Blueprint('register_admin', __name__, url_prefix='/admin/cajas')


@register_admin_bp.route('/')
def list_registers():
    """Lista todos los puntos de venta (TPV)"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        registers = PosRegister.query.order_by(PosRegister.created_at.desc()).all()
        # Preparar datos de categorías para cada caja
        for register in registers:
            if register.allowed_categories:
                try:
                    register._categories_list = json.loads(register.allowed_categories)
                except:
                    register._categories_list = []
            else:
                register._categories_list = None
        return render_template('admin/registers/list.html', registers=registers)
    except Exception as e:
        current_app.logger.error(f"Error al listar cajas: {e}", exc_info=True)
        flash(f'Error al cargar cajas: {str(e)}', 'error')
        return redirect(url_for('routes.admin_panel_control'))


def get_available_categories():
    """Helper para obtener categorías disponibles de productos activos"""
    try:
        categorias = db.session.query(Product.category).distinct().filter(
            Product.category.isnot(None),
            Product.category != '',
            Product.is_active == True
        ).order_by(Product.category).all()
        available_categories = [cat[0].strip() for cat in categorias if cat[0] and cat[0].strip()]
        # Eliminar duplicados (por si hay espacios)
        available_categories = list(dict.fromkeys(available_categories))
        current_app.logger.info(f"✅ Categorías encontradas para TPV: {len(available_categories)} - {available_categories}")
        return available_categories
    except Exception as e:
        current_app.logger.error(f"Error al obtener categorías: {e}", exc_info=True)
        return []


@register_admin_bp.route('/crear', methods=['GET', 'POST'])
def create_register():
    """Crear un nuevo punto de venta (TPV)"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    # Obtener categorías disponibles
    available_categories = get_available_categories()
    
    # Obtener impresoras disponibles
    try:
        available_printers = PrinterHelper.get_available_printers()
    except Exception as e:
        current_app.logger.warning(f"Error al obtener impresoras: {e}")
        available_printers = []
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            code = request.form.get('code', '').strip()
            is_active = request.form.get('is_active') == 'on'
            superadmin_only = request.form.get('superadmin_only') == 'on'
            location = request.form.get('location', '').strip() or None
            tpv_type = request.form.get('tpv_type', '').strip() or None
            default_location = request.form.get('default_location', '').strip() or None
            max_concurrent_sessions = int(request.form.get('max_concurrent_sessions', 1))
            requires_cash_count = request.form.get('requires_cash_count') == 'on'
            
            # Configuración de impresora
            printer_name = request.form.get('printer_name', '').strip() or None
            printer_type = request.form.get('printer_type', 'thermal')
            paper_width = int(request.form.get('paper_width', 80))
            auto_print = request.form.get('auto_print') == 'on'
            print_items = request.form.get('print_items') == 'on'
            print_total = request.form.get('print_total') == 'on'
            open_drawer = request.form.get('open_drawer') == 'on'
            
            # Crear configuración de impresora
            printer_config_json = PrinterHelper.create_printer_config(
                printer_name=printer_name,
                printer_type=printer_type,
                auto_print=auto_print,
                print_items=print_items,
                print_total=print_total,
                print_barcode=True,
                paper_width=paper_width,
                open_drawer=open_drawer,
                cut_paper=True
            )
            
            # Validar configuración
            import json as json_lib
            printer_config_dict = json_lib.loads(printer_config_json)
            is_valid, error_msg = PrinterHelper.validate_printer_config(printer_config_dict)
            if not is_valid:
                flash(f'Error en configuración de impresora: {error_msg}', 'error')
                return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            # Obtener categorías seleccionadas
            selected_categories = request.form.getlist('allowed_categories')
            
            # Validaciones
            if not name:
                flash('El nombre del TPV es requerido', 'error')
                return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            if not code:
                flash('El código del TPV es requerido', 'error')
                return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            # Verificar que el código no exista
            existing = PosRegister.query.filter_by(code=code).first()
            if existing:
                flash(f'Ya existe un TPV con el código "{code}"', 'error')
                return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            # Guardar categorías como JSON (null si no hay selección = todas las categorías)
            allowed_categories_json = None
            if selected_categories:
                allowed_categories_json = json.dumps(selected_categories)
            
            # MVP1: Procesar nuevos campos
            register_type = request.form.get('register_type', '').strip() or None
            operational_status = request.form.get('operational_status', 'active').strip()
            responsible_user_id = request.form.get('responsible_user_id', '').strip() or None
            responsible_role = request.form.get('responsible_role', '').strip() or None
            
            # Validar register_type si se proporciona
            if register_type and register_type not in ['TOTEM', 'HUMANA', 'OFICINA', 'VIRTUAL']:
                flash(f'Tipo de caja inválido: {register_type}', 'error')
                return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            # Procesar JSON fields con validación
            devices_json = None
            devices_raw = request.form.get('devices', '').strip()
            if devices_raw:
                try:
                    devices_dict = json.loads(devices_raw)
                    devices_json = json.dumps(devices_dict)
                except json.JSONDecodeError:
                    flash('Error: devices debe ser un JSON válido', 'error')
                    return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            operation_mode_json = None
            operation_mode_raw = request.form.get('operation_mode', '').strip()
            if operation_mode_raw:
                try:
                    operation_mode_dict = json.loads(operation_mode_raw)
                    operation_mode_json = json.dumps(operation_mode_dict)
                except json.JSONDecodeError:
                    flash('Error: operation_mode debe ser un JSON válido', 'error')
                    return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            # Payment methods como JSON array
            payment_methods_list = request.form.getlist('payment_methods')
            payment_methods_json = None
            if payment_methods_list:
                payment_methods_json = json.dumps(payment_methods_list)
            
            fallback_config_json = None
            fallback_config_raw = request.form.get('fallback_config', '').strip()
            if fallback_config_raw:
                try:
                    fallback_config_dict = json.loads(fallback_config_raw)
                    fallback_config_json = json.dumps(fallback_config_dict)
                except json.JSONDecodeError:
                    flash('Error: fallback_config debe ser un JSON válido', 'error')
                    return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            fast_lane_config_json = None
            fast_lane_config_raw = request.form.get('fast_lane_config', '').strip()
            if fast_lane_config_raw:
                try:
                    fast_lane_config_dict = json.loads(fast_lane_config_raw)
                    fast_lane_config_json = json.dumps(fast_lane_config_dict)
                except json.JSONDecodeError:
                    flash('Error: fast_lane_config debe ser un JSON válido', 'error')
                    return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            # Payment Stack BIMBA: Procesar campos de payment providers
            payment_provider_primary = request.form.get('payment_provider_primary', 'GETNET').strip()
            payment_provider_backup = request.form.get('payment_provider_backup', '').strip() or None
            
            # Validar providers
            valid_providers = ['GETNET', 'KLAP', 'SUMUP']
            if payment_provider_primary not in valid_providers:
                flash(f'Provider principal inválido: {payment_provider_primary}', 'error')
                return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            if payment_provider_backup and payment_provider_backup not in valid_providers:
                flash(f'Provider backup inválido: {payment_provider_backup}', 'error')
                return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            # Procesar provider_config
            provider_config_json = None
            provider_config_raw = request.form.get('provider_config', '').strip()
            if provider_config_raw:
                try:
                    provider_config_dict = json.loads(provider_config_raw)
                    
                    # Validar GETNET serial config si está habilitado
                    if current_app.config.get('ENABLE_GETNET_SERIAL', False):
                        getnet_config = provider_config_dict.get('GETNET', {})
                        if getnet_config.get('mode') == 'serial' and payment_provider_primary == 'GETNET':
                            # Validar que port esté presente para modo serial
                            if not getnet_config.get('port'):
                                flash('Error: GETNET en modo serial requiere campo "port" (ej: COM4)', 'error')
                                return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
                    
                    provider_config_json = json.dumps(provider_config_dict)
                except json.JSONDecodeError:
                    flash('Error: provider_config debe ser un JSON válido', 'error')
                    return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
            
            # Procesar fallback_policy (construir desde campos del formulario)
            fallback_enabled = request.form.get('fallback_enabled') == 'on'
            max_switch_time = int(request.form.get('max_switch_time', 60))
            backup_devices_required_raw = request.form.get('backup_devices_required', '2')
            
            # Defaults por tipo de caja
            if register_type == 'TOTEM':
                default_backup_devices = 2
                fallback_operational_mode = 'manual'  # No integrado aún
            elif register_type == 'HUMANA':
                default_backup_devices = 2
                fallback_operational_mode = 'automatic'
            elif register_type == 'OFICINA':
                default_backup_devices = 1  # Menor flujo
                fallback_operational_mode = 'automatic'
            elif register_type == 'VIRTUAL':
                default_backup_devices = 0  # No aplica
                fallback_operational_mode = 'not_applicable'
            else:
                default_backup_devices = 2
                fallback_operational_mode = 'automatic'
            
            backup_devices_required = int(backup_devices_required_raw) if backup_devices_required_raw else default_backup_devices
            
            # Validación: VIRTUAL no debe tener backup
            if register_type == 'VIRTUAL' and payment_provider_backup:
                flash('Las cajas VIRTUAL no deben tener provider backup. Integración real en fase posterior.', 'warning')
                payment_provider_backup = None
                fallback_enabled = False
            
            # Construir fallback_policy JSON
            fallback_policy_dict = {
                'enabled': fallback_enabled,
                'trigger_events': ['pos_offline', 'pos_error', 'printer_error_optional'],
                'max_switch_time_seconds': max_switch_time,
                'backup_devices_required': backup_devices_required,
                'operational_mode': fallback_operational_mode
            }
            fallback_policy_json = json.dumps(fallback_policy_dict)
            
            # Crear nuevo TPV
            new_register = PosRegister(
                name=name,
                code=code,
                is_active=is_active,
                superadmin_only=superadmin_only,
                allowed_categories=allowed_categories_json,
                location=location,
                tpv_type=tpv_type,
                default_location=default_location,
                printer_config=printer_config_json,
                max_concurrent_sessions=max_concurrent_sessions,
                requires_cash_count=requires_cash_count,
                # MVP1: Campos nuevos
                register_type=register_type,
                devices=devices_json,
                operation_mode=operation_mode_json,
                payment_methods=payment_methods_json,
                responsible_user_id=responsible_user_id,
                responsible_role=responsible_role,
                operational_status=operational_status,
                fallback_config=fallback_config_json,
                fast_lane_config=fast_lane_config_json,
                # Payment Stack BIMBA
                payment_provider_primary=payment_provider_primary,
                payment_provider_backup=payment_provider_backup,
                provider_config=provider_config_json,
                fallback_policy=fallback_policy_json,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(new_register)
            db.session.commit()
            
            flash(f'TPV "{name}" creado exitosamente', 'success')
            current_app.logger.info(f"✅ TPV creado: {name} ({code}) - Activo: {is_active}, Superadmin: {superadmin_only}, Categorías: {selected_categories or 'Todas'}")
            return redirect(url_for('register_admin.list_registers'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear TPV: {e}", exc_info=True)
            flash(f'Error al crear TPV: {str(e)}', 'error')
            return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)
    
    return render_template('admin/registers/form.html', register=None, available_categories=available_categories, available_printers=available_printers)


@register_admin_bp.route('/<int:register_id>/editar', methods=['GET', 'POST'])
def edit_register(register_id):
    """Editar un punto de venta (TPV) existente"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    register = PosRegister.query.get_or_404(register_id)
    
    # Obtener categorías disponibles
    available_categories = get_available_categories()
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            code = request.form.get('code', '').strip()
            is_active = request.form.get('is_active') == 'on'
            superadmin_only = request.form.get('superadmin_only') == 'on'
            location = request.form.get('location', '').strip() or None
            tpv_type = request.form.get('tpv_type', '').strip() or None
            default_location = request.form.get('default_location', '').strip() or None
            max_concurrent_sessions = int(request.form.get('max_concurrent_sessions', 1))
            requires_cash_count = request.form.get('requires_cash_count') == 'on'
            
            # Obtener categorías seleccionadas
            selected_categories = request.form.getlist('allowed_categories')
            
            # Validaciones
            if not name:
                flash('El nombre del TPV es requerido', 'error')
                return render_template('admin/registers/form.html', register=register, available_categories=available_categories)
            
            if not code:
                flash('El código del TPV es requerido', 'error')
                return render_template('admin/registers/form.html', register=register, available_categories=available_categories)
            
            # Verificar que el código no exista en otra caja
            existing = PosRegister.query.filter_by(code=code).filter(PosRegister.id != register_id).first()
            if existing:
                flash(f'Ya existe otro TPV con el código "{code}"', 'error')
                return render_template('admin/registers/form.html', register=register, available_categories=available_categories)
            
            # Guardar categorías como JSON (null si no hay selección = todas las categorías)
            allowed_categories_json = None
            if selected_categories:
                allowed_categories_json = json.dumps(selected_categories)
            
            # Configuración de impresora (mismo código que en create)
            printer_name = request.form.get('printer_name', '').strip() or None
            printer_type = request.form.get('printer_type', 'thermal')
            paper_width = int(request.form.get('paper_width', 80))
            auto_print = request.form.get('auto_print') == 'on'
            print_items = request.form.get('print_items') == 'on'
            print_total = request.form.get('print_total') == 'on'
            open_drawer = request.form.get('open_drawer') == 'on'
            
            # Crear configuración de impresora
            printer_config_json = PrinterHelper.create_printer_config(
                printer_name=printer_name,
                printer_type=printer_type,
                auto_print=auto_print,
                print_items=print_items,
                print_total=print_total,
                print_barcode=True,
                paper_width=paper_width,
                open_drawer=open_drawer,
                cut_paper=True
            )
            
            # Validar configuración
            import json as json_lib
            printer_config_dict = json_lib.loads(printer_config_json)
            is_valid, error_msg = PrinterHelper.validate_printer_config(printer_config_dict)
            if not is_valid:
                flash(f'Error en configuración de impresora: {error_msg}', 'error')
                return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
            
            # MVP1: Procesar nuevos campos
            register_type = request.form.get('register_type', '').strip() or None
            operational_status = request.form.get('operational_status', 'active').strip()
            responsible_user_id = request.form.get('responsible_user_id', '').strip() or None
            responsible_role = request.form.get('responsible_role', '').strip() or None
            
            # Validar register_type si se proporciona
            if register_type and register_type not in ['TOTEM', 'HUMANA', 'OFICINA', 'VIRTUAL']:
                flash(f'Tipo de caja inválido: {register_type}', 'error')
                return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
            
            # Procesar JSON fields con validación
            devices_json = None
            devices_raw = request.form.get('devices', '').strip()
            if devices_raw:
                try:
                    devices_dict = json.loads(devices_raw)
                    devices_json = json.dumps(devices_dict)
                except json.JSONDecodeError:
                    flash('Error: devices debe ser un JSON válido', 'error')
                    return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
            
            operation_mode_json = None
            operation_mode_raw = request.form.get('operation_mode', '').strip()
            if operation_mode_raw:
                try:
                    operation_mode_dict = json.loads(operation_mode_raw)
                    operation_mode_json = json.dumps(operation_mode_dict)
                except json.JSONDecodeError:
                    flash('Error: operation_mode debe ser un JSON válido', 'error')
                    return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
            
            # Payment methods como JSON array
            payment_methods_list = request.form.getlist('payment_methods')
            payment_methods_json = None
            if payment_methods_list:
                payment_methods_json = json.dumps(payment_methods_list)
            
            fallback_config_json = None
            fallback_config_raw = request.form.get('fallback_config', '').strip()
            if fallback_config_raw:
                try:
                    fallback_config_dict = json.loads(fallback_config_raw)
                    fallback_config_json = json.dumps(fallback_config_dict)
                except json.JSONDecodeError:
                    flash('Error: fallback_config debe ser un JSON válido', 'error')
                    return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
            
            fast_lane_config_json = None
            fast_lane_config_raw = request.form.get('fast_lane_config', '').strip()
            if fast_lane_config_raw:
                try:
                    fast_lane_config_dict = json.loads(fast_lane_config_raw)
                    fast_lane_config_json = json.dumps(fast_lane_config_dict)
                except json.JSONDecodeError:
                    flash('Error: fast_lane_config debe ser un JSON válido', 'error')
                    return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
            
            # Payment Stack BIMBA: Procesar campos de payment providers
            payment_provider_primary = request.form.get('payment_provider_primary', 'GETNET').strip()
            payment_provider_backup = request.form.get('payment_provider_backup', '').strip() or None
            
            # Validar providers
            valid_providers = ['GETNET', 'KLAP', 'SUMUP']
            if payment_provider_primary not in valid_providers:
                flash(f'Provider principal inválido: {payment_provider_primary}', 'error')
                return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
            
            if payment_provider_backup and payment_provider_backup not in valid_providers:
                flash(f'Provider backup inválido: {payment_provider_backup}', 'error')
                return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
            
            # Procesar provider_config
            provider_config_json = None
            provider_config_raw = request.form.get('provider_config', '').strip()
            if provider_config_raw:
                try:
                    provider_config_dict = json.loads(provider_config_raw)
                    
                    # Validar GETNET serial config si está habilitado
                    if current_app.config.get('ENABLE_GETNET_SERIAL', False):
                        getnet_config = provider_config_dict.get('GETNET', {})
                        if getnet_config.get('mode') == 'serial' and payment_provider_primary == 'GETNET':
                            # Validar que port esté presente para modo serial
                            if not getnet_config.get('port'):
                                flash('Error: GETNET en modo serial requiere campo "port" (ej: COM4)', 'error')
                                return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
                    
                    provider_config_json = json.dumps(provider_config_dict)
                except json.JSONDecodeError:
                    flash('Error: provider_config debe ser un JSON válido', 'error')
                    return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
            
            # Procesar fallback_policy (construir desde campos del formulario)
            fallback_enabled = request.form.get('fallback_enabled') == 'on'
            max_switch_time = int(request.form.get('max_switch_time', 60))
            backup_devices_required_raw = request.form.get('backup_devices_required', '2')
            
            # Defaults por tipo de caja
            if register_type == 'TOTEM':
                default_backup_devices = 2
                fallback_operational_mode = 'manual'  # No integrado aún
            elif register_type == 'HUMANA':
                default_backup_devices = 2
                fallback_operational_mode = 'automatic'
            elif register_type == 'OFICINA':
                default_backup_devices = 1  # Menor flujo
                fallback_operational_mode = 'automatic'
            elif register_type == 'VIRTUAL':
                default_backup_devices = 0  # No aplica
                fallback_operational_mode = 'not_applicable'
            else:
                default_backup_devices = 2
                fallback_operational_mode = 'automatic'
            
            backup_devices_required = int(backup_devices_required_raw) if backup_devices_required_raw else default_backup_devices
            
            # Validación: VIRTUAL no debe tener backup
            if register_type == 'VIRTUAL' and payment_provider_backup:
                flash('Las cajas VIRTUAL no deben tener provider backup. Integración real en fase posterior.', 'warning')
                payment_provider_backup = None
                fallback_enabled = False
            
            # Construir fallback_policy JSON
            fallback_policy_dict = {
                'enabled': fallback_enabled,
                'trigger_events': ['pos_offline', 'pos_error', 'printer_error_optional'],
                'max_switch_time_seconds': max_switch_time,
                'backup_devices_required': backup_devices_required,
                'operational_mode': fallback_operational_mode
            }
            fallback_policy_json = json.dumps(fallback_policy_dict)
            
            # Actualizar TPV
            register.name = name
            register.code = code
            register.is_active = is_active
            register.superadmin_only = superadmin_only
            register.allowed_categories = allowed_categories_json
            register.location = location
            register.tpv_type = tpv_type
            register.default_location = default_location
            register.printer_config = printer_config_json
            register.max_concurrent_sessions = max_concurrent_sessions
            register.requires_cash_count = requires_cash_count
            # MVP1: Campos nuevos
            register.register_type = register_type
            register.devices = devices_json
            register.operation_mode = operation_mode_json
            register.payment_methods = payment_methods_json
            register.responsible_user_id = responsible_user_id
            register.responsible_role = responsible_role
            register.operational_status = operational_status
            register.fallback_config = fallback_config_json
            register.fast_lane_config = fast_lane_config_json
            # Payment Stack BIMBA
            register.payment_provider_primary = payment_provider_primary
            register.payment_provider_backup = payment_provider_backup
            register.provider_config = provider_config_json
            register.fallback_policy = fallback_policy_json
            register.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'TPV "{name}" actualizado exitosamente', 'success')
            current_app.logger.info(f"✅ TPV actualizado: {name} ({code}) - Activo: {is_active}, Superadmin: {superadmin_only}, Categorías: {selected_categories or 'Todas'}")
            return redirect(url_for('register_admin.list_registers'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al actualizar TPV: {e}", exc_info=True)
            flash(f'Error al actualizar TPV: {str(e)}', 'error')
            return render_template('admin/registers/form.html', register=register, available_categories=available_categories, available_printers=available_printers)
    
    # Obtener impresoras disponibles
    try:
        available_printers = PrinterHelper.get_available_printers()
    except Exception as e:
        current_app.logger.warning(f"Error al obtener impresoras: {e}")
        available_printers = []
    
    # Obtener categorías seleccionadas de la caja actual
    selected_categories = []
    if register.allowed_categories:
        try:
            selected_categories = json.loads(register.allowed_categories)
        except:
            selected_categories = []
    
    # MVP1: Parsear payment_methods para el template
    payment_methods_list = []
    if register.payment_methods:
        try:
            payment_methods_list = json.loads(register.payment_methods)
        except:
            payment_methods_list = []
    
    return render_template('admin/registers/form.html', register=register, available_categories=available_categories, selected_categories=selected_categories, available_printers=available_printers, payment_methods_list=payment_methods_list)


@register_admin_bp.route('/<int:register_id>/toggle', methods=['POST'])
def toggle_register(register_id):
    """Activar/desactivar un TPV"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        register = PosRegister.query.get_or_404(register_id)
        register.is_active = not register.is_active
        db.session.commit()
        
        status = 'activado' if register.is_active else 'desactivado'
        current_app.logger.info(f"✅ TPV {register.name} {status}")
        
        return jsonify({
            'success': True,
            'is_active': register.is_active,
            'message': f'TPV {status} exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al cambiar estado de TPV: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@register_admin_bp.route('/<int:register_id>/eliminar', methods=['POST'])
def delete_register(register_id):
    """Eliminar un TPV (solo si no tiene ventas asociadas)"""
    if not session.get('admin_logged_in'):
        flash('No autorizado', 'error')
        return redirect(url_for('register_admin.list_registers'))
    
    try:
        register = PosRegister.query.get_or_404(register_id)
        
        # Verificar si tiene ventas asociadas
        from app.models.pos_models import PosSale
        sales_count = PosSale.query.filter_by(register_id=str(register_id)).count()
        
        if sales_count > 0:
            flash(f'No se puede eliminar el TPV "{register.name}" porque tiene {sales_count} venta(s) asociada(s). Puedes desactivarlo en su lugar.', 'error')
            return redirect(url_for('register_admin.list_registers'))
        
        # Eliminar TPV
        register_name = register.name
        db.session.delete(register)
        db.session.commit()
        
        flash(f'TPV "{register_name}" eliminado exitosamente', 'success')
        current_app.logger.info(f"✅ TPV eliminado: {register_name}")
        return redirect(url_for('register_admin.list_registers'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar TPV: {e}", exc_info=True)
        flash(f'Error al eliminar TPV: {str(e)}', 'error')
        return redirect(url_for('register_admin.list_registers'))


@register_admin_bp.route('/api/categories')
def api_categories():
    """API: Obtener categorías disponibles"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        categories = get_available_categories()
        return jsonify({
            'success': True,
            'categories': categories,
            'count': len(categories)
        })
    except Exception as e:
        current_app.logger.error(f"Error en API categorías: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@register_admin_bp.route('/api/printers')
def api_printers():
    """API: Obtener impresoras disponibles del sistema"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        printers = PrinterHelper.get_available_printers()
        default_printer = PrinterHelper.get_default_printer()
        
        return jsonify({
            'success': True,
            'printers': printers,
            'default_printer': default_printer,
            'count': len(printers)
        })
    except Exception as e:
        current_app.logger.error(f"Error en API impresoras: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@register_admin_bp.route('/reportes')
def reportes():
    """MVP1: Reportes básicos de cajas y sesiones"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        from app.models.pos_models import RegisterSession
        from app.models.jornada_models import Jornada
        from sqlalchemy import func, desc
        
        # Obtener todas las cajas
        registers = PosRegister.query.order_by(PosRegister.name).all()
        
        # Obtener última sesión por caja
        registers_data = []
        for register in registers:
            # Última sesión de esta caja
            last_session = RegisterSession.query.filter_by(
                register_id=str(register.id)
            ).order_by(desc(RegisterSession.opened_at)).first()
            
            # Totales de ventas por método de pago (última sesión cerrada)
            payment_totals = {'cash': 0.0, 'debit': 0.0, 'credit': 0.0}
            ticket_count = 0
            cash_difference = None
            
            if last_session and last_session.payment_totals:
                try:
                    payment_totals = json.loads(last_session.payment_totals)
                except:
                    pass
            
            if last_session:
                ticket_count = last_session.ticket_count or 0
                cash_difference = float(last_session.cash_difference) if last_session.cash_difference else None
            
            registers_data.append({
                'register': register,
                'last_session': last_session,
                'payment_totals': payment_totals,
                'ticket_count': ticket_count,
                'cash_difference': cash_difference
            })
        
        return render_template('admin/cajas/reportes.html', registers_data=registers_data)
        
    except Exception as e:
        current_app.logger.error(f"Error al generar reportes: {e}", exc_info=True)
        flash(f'Error al generar reportes: {str(e)}', 'error')
        return redirect(url_for('register_admin.list_registers'))


@register_admin_bp.route('/seed-test', methods=['POST'])
def seed_test():
    """
    TEST / QA ONLY – DO NOT USE IN PROD LOGIC
    
    Endpoint protegido para crear/actualizar caja de prueba + producto de prueba
    """
    if not session.get('admin_logged_in'):
        flash('No autorizado', 'error')
        return redirect(url_for('auth.login_admin'))
    
    try:
        # TEST / QA ONLY – DO NOT USE IN PROD LOGIC
        success, message, register, product = seed_test_register_and_product(db)
        success_emp, message_emp, employee = seed_test_cashier_user(db)
        
        if success and success_emp:
            db.session.commit()
            flash(f'✅ {message}. {message_emp}', 'success')
            logger.info(f"✅ Seed completo: {message}. {message_emp}")
        else:
            db.session.rollback()
            combined = f"{message} | {message_emp}"
            flash(f'❌ {combined}', 'error')
            logger.error(f"❌ Error en seed: {combined}")
        
        return redirect(url_for('register_admin.list_registers'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error en seed_test: {e}", exc_info=True)
        flash(f'Error al crear datos de prueba: {str(e)}', 'error')
        return redirect(url_for('register_admin.list_registers'))
