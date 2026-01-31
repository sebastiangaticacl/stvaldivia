"""
Helper para monitoreo de ventas por caja en tiempo real
Obtiene datos desde nuestra base de datos local (PosSale)
PHP POS solo se usa para inventario y empleados, NO para ventas
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import current_app
# NO importamos PhpPosApiClient - solo usamos nuestra BD local para ventas
from app.helpers.cache import cached
import logging

logger = logging.getLogger(__name__)


# Cache deshabilitado para monitoreo en tiempo real (se actualiza cada 3 segundos)
# @cached('register_sales', ttl=60)  # Cache de 1 minuto para monitoreo
def get_sales_by_register(register_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene ventas del turno actual agrupadas por caja
    Retorna toda la información que PHP POS API proporciona
    
    Args:
        register_id: ID de caja específica (opcional, si None retorna todas)
        
    Returns:
        Dict con estructura:
        {
            'registers': {
                '1': {
                    'register_id': '1',
                    'register_name': 'Caja 1',
                    'sales': [...],
                    'total_sales': 10,
                    'total_amount': 500000,
                    'total_cash': 200000,
                    'total_debit': 150000,
                    'total_credit': 150000,
                    'last_sale_at': '2024-01-15T22:30:00',
                    'employee_id': '123',
                    'employee_name': 'Cajero 1'
                },
                ...
            },
            'summary': {
                'total_registers': 4,
                'total_sales': 50,
                'total_amount': 2000000,
                ...
            }
        }
    """
    try:
        # Obtener turno actual desde Jornada (sistema único)
        from app.models.jornada_models import Jornada
        from datetime import datetime
        from app.utils.timezone import CHILE_TZ
        fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
        
        jornada_actual = Jornada.query.filter_by(
            fecha_jornada=fecha_hoy,
            estado_apertura='abierto'
        ).first()
        
        # Si no hay turno abierto, usar fecha_hoy como shift_date para procesar cierres
        if not jornada_actual or not jornada_actual.abierto_en:
            logger.warning(f"⚠️ No hay turno abierto para hoy ({fecha_hoy}), pero procesaremos cierres de guardarropía")
            shift_date = fecha_hoy
            opened_at = None
            opened_datetime = None
        else:
            # Obtener fecha de apertura del turno
            opened_at = jornada_actual.abierto_en.isoformat() if jornada_actual.abierto_en else None
            shift_date = jornada_actual.fecha_jornada
            
            # Convertir opened_at a formato para la API
            try:
                if opened_at:
                    opened_datetime = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                else:
                    opened_datetime = datetime.now()
            except:
                opened_datetime = datetime.now()
            
            if opened_datetime.tzinfo:
                opened_datetime = opened_datetime.replace(tzinfo=None)
        
        # start_date y end_date solo se usan si hay turno abierto
        if opened_datetime:
            start_date = opened_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            start_date = None
            end_date = None
        
        # OPTIMIZADO: Usar agregaciones SQL para totales por caja
        from sqlalchemy import func, case
        from app.models import db, PosSale
        from app.models.jornada_models import AperturaCaja
        
        logger.info(f"🔍 Calculando totales por caja usando SQL para turno: {shift_date}")
        
        # Query base
        query = db.session.query(
            PosSale.register_id,
            PosSale.register_name,
            func.count(PosSale.id).label('total_sales'),
            func.sum(PosSale.total_amount).label('total_amount'),
            func.sum(PosSale.payment_cash).label('total_cash'),
            func.sum(PosSale.payment_debit).label('total_debit'),
            func.sum(PosSale.payment_credit).label('total_credit'),
            func.max(PosSale.created_at).label('last_sale_at')
        )
        
        if jornada_actual and jornada_actual.abierto_en:
            opened_dt = jornada_actual.abierto_en
            if opened_dt.tzinfo:
                opened_dt = opened_dt.replace(tzinfo=None)
            query = query.filter(PosSale.created_at >= opened_dt)
        elif shift_date:
            query = query.filter(PosSale.shift_date == shift_date)
            
        sales_stats = query.group_by(PosSale.register_id, PosSale.register_name).all()
        
        # Agrupar ventas por caja
        registers_data = {}
        summary_total_sales = 0
        summary_total_amount = 0.0
        summary_total_cash = 0.0
        summary_total_debit = 0.0
        summary_total_credit = 0.0
        
        # Obtener información de bloqueos y cierres de cajas
        from app.helpers.register_lock_db import get_all_register_locks
        from app.models.pos_models import RegisterClose
        
        try:
            register_locks_list = get_all_register_locks()
            # Convertir lista a diccionario indexado por register_id
            register_locks = {}
            for lock in register_locks_list:
                reg_id = str(lock.get('register_id', ''))
                if reg_id:
                    register_locks[reg_id] = lock
        except Exception as e:
            logger.warning(f"No se pudieron obtener bloqueos de cajas: {e}")
            register_locks = {}
        
        # Obtener TODOS los cierres de cajas del turno actual (usar shift_date)
        # IMPORTANTE: Guardar todos los cierres, no solo el último (un trabajador puede cerrar múltiples veces)
        # También incluir cierres pendientes de otras fechas para mostrar en la página principal
        register_closes = {}  # Dict de listas: {register_id: [cierre1, cierre2, ...]}
        register_closes_latest = {}  # Dict del último cierre: {register_id: cierre_más_reciente}
        try:
            # Procesar cierres siempre, incluso si no hay turno abierto
            # Incluir cierres del turno actual Y cierres pendientes de cualquier fecha
            from sqlalchemy import or_
            closes = RegisterClose.query.filter(
                or_(
                    RegisterClose.shift_date == shift_date,
                    RegisterClose.status == 'pending'
                )
            ).order_by(RegisterClose.closed_at.desc()).all()
            logger.info(f"📋 Encontrados {len(closes)} cierres para shift_date={shift_date} o status=pending")
            guardarropia_count = sum(1 for c in closes if str(c.register_id) == 'GUARDARROPIA')
            logger.info(f"📦 De esos, {guardarropia_count} son de guardarropía")
                
            for close in closes:
                reg_id = str(close.register_id)
                logger.info(f"🔍 Procesando cierre: register_id={reg_id}, total_sales={close.total_sales}, total_amount={close.total_amount}")
                
                # Formatear opened_at (puede ser string o datetime)
                opened_at_formatted = None
                if close.opened_at:
                    if isinstance(close.opened_at, str):
                        opened_at_formatted = close.opened_at
                    elif isinstance(close.opened_at, datetime):
                        opened_at_formatted = close.opened_at.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        opened_at_formatted = str(close.opened_at)
                
                # Formatear closed_at (siempre datetime)
                # IMPORTANTE: Si no tiene timezone, podría estar en UTC desde SQLite
                closed_at_formatted = None
                if close.closed_at:
                    if isinstance(close.closed_at, datetime):
                        if close.closed_at.tzinfo:
                            # Ya tiene timezone, convertir a hora de Chile
                            closed_at_chile = close.closed_at.astimezone(CHILE_TZ)
                            closed_at_formatted = closed_at_chile.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            # Sin timezone: asumir UTC y convertir a hora de Chile
                            # Esto corrige el problema si SQLite almacenó como UTC
                            utc = pytz.UTC
                            closed_at_utc = utc.localize(close.closed_at)
                            closed_at_chile = closed_at_utc.astimezone(CHILE_TZ)
                            closed_at_formatted = closed_at_chile.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        closed_at_formatted = str(close.closed_at)
                    
                    close_info = {
                        'id': close.id,
                        'employee_id': str(close.employee_id) if close.employee_id else None,
                        'employee_name': close.employee_name or 'Sin asignar',
                        'opened_at': opened_at_formatted,
                        'closed_at': closed_at_formatted,
                        'total_sales': int(close.total_sales) if close.total_sales else 0,
                        'total_amount': float(close.total_amount) if close.total_amount else 0.0,
                        'expected_cash': float(close.expected_cash or 0),
                        'expected_debit': float(close.expected_debit or 0),
                        'expected_credit': float(close.expected_credit or 0),
                        'status': 'closed'
                    }
                    
                    # Agregar a lista de cierres (todos los cierres)
                    if reg_id not in register_closes:
                        register_closes[reg_id] = []
                    register_closes[reg_id].append(close_info)
                    
                # Guardar solo el más reciente (para compatibilidad con lógica existente)
                if reg_id not in register_closes_latest:
                    register_closes_latest[reg_id] = close_info
        except Exception as e:
            logger.error(f"❌ Error al obtener cierres de cajas: {e}", exc_info=True)
            register_closes = {}
            register_closes_latest = {}
        
        # Obtener nombres de cajas desde snapshot del turno (NO desde API)
        registers_map = {}
        try:
            from app.models.jornada_models import SnapshotCajas
            
            if jornada_actual:
                # Usar snapshot guardado al abrir el turno
                snapshot_cajas = SnapshotCajas.query.filter_by(jornada_id=jornada_actual.id).all()
                registers_map = {caja.caja_id: caja.nombre_caja for caja in snapshot_cajas}
        except Exception as e:
            logger.warning(f"No se pudieron obtener nombres de cajas desde snapshot: {e}")
        
        # Si no hay snapshot, crear nombres básicos desde las cajas abiertas
        if not registers_map:
            for reg_id in register_locks.keys():
                registers_map[str(reg_id)] = f'Caja {reg_id}'
            for reg_id in register_closes.keys():
                if str(reg_id) not in registers_map:
                    registers_map[str(reg_id)] = f'Caja {reg_id}'
        
        # Asegurar que GUARDARROPIA esté en el mapa con nombre correcto
        if 'GUARDARROPIA' not in registers_map:
            registers_map['GUARDARROPIA'] = 'Guardarropía'
        
        # También agregar GUARDARROPIA si hay ventas o cierres pero no está en el mapa
        for stat in sales_stats:
            reg_id = str(stat.register_id)
            if reg_id == 'GUARDARROPIA' and reg_id not in registers_map:
                registers_map[reg_id] = 'Guardarropía'
        
        # Procesar resultados de la query SQL
        for stat in sales_stats:
            reg_id = str(stat.register_id)
            
            # Filtrar por caja específica si se solicita
            if register_id and reg_id != str(register_id):
                continue
                
            register_name = stat.register_name or registers_map.get(reg_id, f'Caja {reg_id}')
            
            # Totales
            total_sales = stat.total_sales or 0
            total_amount = float(stat.total_amount or 0)
            total_cash = float(stat.total_cash or 0)
            total_debit = float(stat.total_debit or 0)
            total_credit = float(stat.total_credit or 0)
            last_sale_at = stat.last_sale_at.isoformat() if stat.last_sale_at else None
            
            # Actualizar resumen general
            summary_total_sales += total_sales
            summary_total_amount += total_amount
            summary_total_cash += total_cash
            summary_total_debit += total_debit
            summary_total_credit += total_credit
            
            # Obtener información del bloqueo/cierre
            # IMPORTANTE: Si hay un bloqueo activo, la caja está ABIERTA (incluso si hubo un cierre anterior)
            lock_info = register_locks.get(reg_id, {})
            close_info = register_closes_latest.get(reg_id)  # Usar el último cierre para determinar estado
            all_closes = register_closes.get(reg_id, [])  # Todos los cierres para esta caja
            
            # La caja está cerrada solo si NO hay bloqueo activo Y hay un cierre
            is_closed = close_info is not None and not lock_info
            
            current_cashier_id = None
            current_cashier_name = 'Sin asignar'
            opened_at_reg = None
            
            # Priorizar bloqueo activo sobre cierre anterior
            if lock_info:
                # Caja está ABIERTA (hay bloqueo activo)
                current_cashier_id = lock_info.get('employee_id')
                current_cashier_name = lock_info.get('employee_name', 'Sin asignar')
                opened_at_reg = lock_info.get('locked_at')
            elif close_info:
                # Caja está CERRADA (no hay bloqueo activo pero hay un cierre)
                current_cashier_id = close_info.get('employee_id')
                current_cashier_name = close_info.get('employee_name', 'Sin asignar')
                opened_at_reg = close_info.get('opened_at')
            
            # Calcular porcentajes
            total_payment = total_cash + total_debit + total_credit
            cash_pct = (total_cash / total_payment * 100) if total_payment > 0 else 0
            debit_pct = (total_debit / total_payment * 100) if total_payment > 0 else 0
            credit_pct = (total_credit / total_payment * 100) if total_payment > 0 else 0
            
            # Calcular ticket promedio
            avg_ticket = total_amount / total_sales if total_sales > 0 else 0
            
            registers_data[reg_id] = {
                'register_id': reg_id,
                'register_name': register_name,
                'sales': [], # NO cargar todas las ventas para no saturar memoria
                'total_sales': total_sales,
                'total_amount': total_amount,
                'total_cash': total_cash,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'last_sale_at': last_sale_at,
                'employee_id': current_cashier_id,
                'employee_name': current_cashier_name,
                'employees': {}, # Simplificado
                'current_cashier_id': current_cashier_id,
                'current_cashier_name': current_cashier_name,
                'opened_at': opened_at_reg,
                'is_closed': is_closed,
                # Solo mostrar closed_at si la caja está realmente cerrada (no hay bloqueo activo)
                'closed_at': close_info.get('closed_at') if is_closed and close_info else None,
                'close_status': close_info.get('status') if is_closed and close_info else None,
                # TODOS los cierres de esta caja (para mostrar múltiples cierres)
                'all_closes': all_closes if all_closes else [],
                'close_count': len(all_closes) if all_closes else 0,
                'average_ticket': avg_ticket,
                'cash_percentage': cash_pct,
                'debit_percentage': debit_pct,
                'credit_percentage': credit_pct,
                'cash_sales_count': 0, # Aproximado o requeriría otra query
                'debit_sales_count': 0,
                'credit_sales_count': 0
            }

        # Agregar cajas abiertas sin ventas
        for register_id_key, lock_info in register_locks.items():
            reg_id = str(register_id_key)
            if register_id and reg_id != str(register_id):
                continue
                
            if reg_id not in registers_data:
                # Caja abierta pero sin ventas
                register_name = registers_map.get(reg_id, f'Caja {reg_id}')
                registers_data[reg_id] = {
                    'register_id': reg_id,
                    'register_name': register_name,
                    'sales': [],
                    'total_sales': 0,
                    'total_amount': 0.0,
                    'total_cash': 0.0,
                    'total_debit': 0.0,
                    'total_credit': 0.0,
                    'last_sale_at': None,
                    'employee_id': lock_info.get('employee_id'),
                    'employee_name': lock_info.get('employee_name', 'Sin asignar'),
                    'employees': {},
                    'current_cashier_id': lock_info.get('employee_id'),
                    'current_cashier_name': lock_info.get('employee_name', 'Sin asignar'),
                    'opened_at': lock_info.get('locked_at'),
                    'is_closed': False,
                    'closed_at': None,
                    'close_status': None,
                    # También incluir cierres anteriores si existen
                    'all_closes': register_closes.get(reg_id, []),
                    'close_count': len(register_closes.get(reg_id, [])),
                    'average_ticket': 0.0,
                    'cash_percentage': 0,
                    'debit_percentage': 0,
                    'credit_percentage': 0,
                    'cash_sales_count': 0,
                    'debit_sales_count': 0,
                    'credit_sales_count': 0
                }
        
        # Agregar cajas con cierres pero sin ventas en el turno actual (ej: Guardarropía)
        # IMPORTANTE: Esto debe ejecutarse DESPUÉS de procesar ventas pero ANTES de agregar cajas abiertas
        logger.info(f"🔍 Revisando cierres: {list(register_closes.keys())}")
        logger.info(f"🔍 Cajas ya en registers_data: {list(registers_data.keys())}")
        
        for reg_id_key, closes_list in register_closes.items():
            reg_id_str = str(reg_id_key)
            logger.info(f"🔍 Procesando cierre para caja {reg_id_str}: {len(closes_list)} cierres")
            
            if register_id and reg_id_str != str(register_id):
                continue
                
            if reg_id_str not in registers_data and closes_list:
                # Caja con cierres pero sin ventas en el turno actual
                close_info = closes_list[0]  # Usar el más reciente
                register_name = registers_map.get(reg_id_str, f'Caja {reg_id_str}')
                
                # Obtener totales del cierre más reciente
                latest_close = register_closes_latest.get(reg_id_str, {})
                total_sales_from_close = latest_close.get('total_sales', 0)
                total_amount_from_close = latest_close.get('total_amount', 0.0)
                total_cash_from_close = latest_close.get('expected_cash', 0.0)
                total_debit_from_close = latest_close.get('expected_debit', 0.0)
                total_credit_from_close = latest_close.get('expected_credit', 0.0)
                
                logger.info(f"📦 Agregando caja {reg_id_str} ({register_name}) con {len(closes_list)} cierres pero sin ventas en turno actual")
                registers_data[reg_id_str] = {
                    'register_id': reg_id_str,
                    'register_name': register_name,
                    'sales': [],
                    'total_sales': total_sales_from_close,
                    'total_amount': total_amount_from_close,
                    'total_cash': total_cash_from_close,
                    'total_debit': total_debit_from_close,
                    'total_credit': total_credit_from_close,
                    'last_sale_at': None,
                    'employee_id': close_info.get('employee_id'),
                    'employee_name': close_info.get('employee_name', 'Sin asignar'),
                    'employees': {},
                    'current_cashier_id': close_info.get('employee_id'),
                    'current_cashier_name': close_info.get('employee_name', 'Sin asignar'),
                    'opened_at': close_info.get('opened_at'),
                    'is_closed': True,  # Si hay cierre y no hay bloqueo, está cerrada
                    'closed_at': close_info.get('closed_at'),
                    'close_status': close_info.get('status'),
                    'all_closes': closes_list,
                    'close_count': len(closes_list),
                    'average_ticket': total_amount_from_close / total_sales_from_close if total_sales_from_close > 0 else 0.0,
                    'cash_percentage': 0,
                    'debit_percentage': 0,
                    'credit_percentage': 0,
                    'cash_sales_count': 0,
                    'debit_sales_count': 0,
                    'credit_sales_count': 0
                }
                
                # Actualizar resumen con datos del cierre
                summary_total_sales += total_sales_from_close
                summary_total_amount += total_amount_from_close
                summary_total_cash += total_cash_from_close
                summary_total_debit += total_debit_from_close
                summary_total_credit += total_credit_from_close

        return {
            'registers': registers_data,
            'summary': {
                'total_registers': len(registers_data),
                'total_sales': summary_total_sales,
                'total_amount': summary_total_amount,
                'total_cash': summary_total_cash,
                'total_debit': summary_total_debit,
                'total_credit': summary_total_credit,
                'shift_date': shift_date,
                'opened_at': opened_at
            }
        }
        
    except Exception as e:
        logger.error(f"Error al obtener ventas por caja: {e}", exc_info=True)
        return {
            'registers': {},
            'summary': {
                'total_registers': 0,
                'total_sales': 0,
                'total_amount': 0.0,
                'total_cash': 0.0,
                'total_debit': 0.0,
                'total_credit': 0.0,
                'error': str(e)
            }
        }

