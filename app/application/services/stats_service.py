"""
Servicio de Aplicación: Estadísticas (Stats)
Contiene la lógica de cálculo de estadísticas.
Solo lectura, sin lógica de escritura.
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from flask import current_app

from app.infrastructure.repositories.delivery_repository import DeliveryRepository, CsvDeliveryRepository
from app.infrastructure.repositories.shift_repository import ShiftRepository, JsonShiftRepository
from app.infrastructure.repositories.survey_repository import SurveyRepository, CsvSurveyRepository
from app.infrastructure.external.pos_api_client import PosApiClient, PhpPosApiClient


class StatsService:
    """
    Servicio de estadísticas.
    Solo lectura - calcula estadísticas sin modificar datos.
    """
    
    def __init__(
        self,
        delivery_repository: Optional[DeliveryRepository] = None,
        shift_repository: Optional[ShiftRepository] = None,
        survey_repository: Optional[SurveyRepository] = None,
        pos_client: Optional[PosApiClient] = None
    ):
        """
        Inicializa el servicio de estadísticas.
        
        Args:
            delivery_repository: Repositorio de entregas
            shift_repository: Repositorio de turnos
            survey_repository: Repositorio de encuestas
            pos_client: Cliente POS API
        """
        self.delivery_repository = delivery_repository or CsvDeliveryRepository()
        self.shift_repository = shift_repository or JsonShiftRepository()
        self.survey_repository = survey_repository or CsvSurveyRepository()
        self.pos_client = pos_client or PhpPosApiClient()
        
        # Cache para categorías de items
        self._item_categorias_cache = {}
        self._all_items_cache = None
    
    def _get_item_category(self, item_name: str) -> Optional[str]:
        """
        Obtiene la categoría de un producto por su nombre.
        Usa cache para evitar múltiples consultas.
        Mapea "Puerta" a "Entradas" y detecta entradas por nombre.
        
        Args:
            item_name: Nombre del producto
            
        Returns:
            str: Categoría del producto (limpia) o None
        """
        # Si ya tenemos la categoría en cache, retornarla
        if item_name in self._item_categorias_cache:
            return self._item_categorias_cache[item_name]
        
        # Verificar si es una entrada por nombre (antes de consultar API)
        item_name_lower = item_name.lower().strip()
        if 'entrada' in item_name_lower:
            self._item_categorias_cache[item_name] = 'Entradas'
            return 'Entradas'
        
        try:
            # Obtener todos los items desde la API POS (con cache)
            if self._all_items_cache is None:
                # Intentar obtener items desde la API
                api_key = current_app.config.get('API_KEY')
                base_url = current_app.config.get('BASE_API_URL', 'https://clubbb.phppointofsale.com/index.php/api/v1')
                
                if api_key:
                    import requests
                    url = f"{base_url}/items"
                    headers = {
                        "x-api-key": api_key,
                        "accept": "application/json"
                    }
                    try:
                        response = requests.get(url, headers=headers, params={"limit": 1000}, timeout=10)
                        if response.status_code == 200:
                            self._all_items_cache = response.json()
                        else:
                            self._all_items_cache = []
                    except Exception as e:
                        current_app.logger.warning(f"Error al obtener items desde API: {e}")
                        self._all_items_cache = []
                else:
                    self._all_items_cache = []
            
            if not self._all_items_cache:
                self._item_categorias_cache[item_name] = None
                return None
            
            # Buscar el item por nombre
            for item in self._all_items_cache:
                item_api_name = item.get('name', '')
                if item_api_name:
                    item_api_name_lower = item_api_name.lower().strip()
                    # Buscar coincidencia (exacta o parcial)
                    if item_name_lower == item_api_name_lower or item_name_lower in item_api_name_lower or item_api_name_lower in item_name_lower:
                        categoria_raw = item.get('category') or item.get('category_name') or None
                        
                        if categoria_raw:
                            # Limpiar categoría: "Barra > Cervezas" -> "Cervezas"
                            if ' > ' in categoria_raw:
                                categoria = categoria_raw.split(' > ')[-1].strip()
                            elif categoria_raw == 'Puerta':
                                categoria = 'Entradas'  # Mapear "Puerta" a "Entradas"
                            elif categoria_raw == 'Ninguno':
                                categoria = 'Otros'
                            else:
                                categoria = categoria_raw.strip()
                            
                            if not categoria or categoria == 'Ninguno':
                                categoria = 'Otros'
                            
                            # También verificar si el nombre del item contiene "entrada"
                            if 'entrada' in item_name_lower and categoria == 'Otros':
                                categoria = 'Entradas'
                            
                            # Guardar en cache
                            self._item_categorias_cache[item_name] = categoria
                            return categoria
            
            # Si no se encontró, verificar si el nombre contiene "entrada"
            if 'entrada' in item_name_lower:
                self._item_categorias_cache[item_name] = 'Entradas'
                return 'Entradas'
            
            # Si no se encontró, guardar None en cache
            self._item_categorias_cache[item_name] = None
            return None
        except Exception as e:
            current_app.logger.warning(f"Error al obtener categoría para {item_name}: {e}")
            # Si hay error pero el nombre contiene "entrada", retornar "Entradas"
            if 'entrada' in item_name_lower:
                self._item_categorias_cache[item_name] = 'Entradas'
                return 'Entradas'
            self._item_categorias_cache[item_name] = None
            return None
    
    def get_delivery_stats_for_shift(self, shift) -> Dict[str, Any]:
        """
        Obtiene estadísticas de entregas para un turno específico.
        OPTIMIZADO: Usa find_by_timestamp_after si está disponible.
        
        Args:
            shift: ShiftStatus del turno actual
            
        Returns:
            dict: Estadísticas de entregas del turno
        """
        from datetime import datetime
        
        # Obtener fecha de apertura del turno
        shift_opened_at = datetime.fromisoformat(shift.opened_at.replace('Z', '+00:00').replace('+00:00', ''))
        if shift_opened_at.tzinfo is not None:
            shift_opened_at = shift_opened_at.replace(tzinfo=None)
            
        # Intentar usar método optimizado del repositorio
        if hasattr(self.delivery_repository, 'find_by_timestamp_after'):
            shift_deliveries = self.delivery_repository.find_by_timestamp_after(shift_opened_at)
        else:
            # Fallback: cargar todo y filtrar (lento)
            all_deliveries = self.delivery_repository.find_all()
            
            shift_deliveries = []
            for delivery in all_deliveries:
                try:
                    if isinstance(delivery.timestamp, str):
                        delivery_time = datetime.strptime(delivery.timestamp, '%Y-%m-%d %H:%M:%S')
                    else:
                        delivery_time = delivery.timestamp
                    
                    if delivery_time >= shift_opened_at:
                        shift_deliveries.append(delivery)
                except:
                    continue
        
        # Usar el método existente pero con las entregas filtradas
        return self._calculate_delivery_stats(shift_deliveries)
    
    def _calculate_delivery_stats(self, deliveries: List) -> Dict[str, Any]:
        """
        Calcula estadísticas de entregas a partir de una lista de entregas.
        
        Args:
            deliveries: Lista de entregas
            
        Returns:
            dict: Estadísticas de entregas
        """
        # Contadores
        item_counts = Counter()
        bartender_counts = Counter()
        barra_counts = Counter()
        categoria_counts = Counter()
        total_qty = 0
        hour_counts = Counter()
        item_categorias_cache = {}
        
        for delivery in deliveries:
            item_counts[delivery.item_name] += delivery.qty
            bartender_counts[delivery.bartender] += delivery.qty
            barra_counts[delivery.barra] += delivery.qty
            total_qty += delivery.qty
            
            # Obtener categoría del producto
            item_name = delivery.item_name
            if item_name not in item_categorias_cache:
                categoria = self._get_item_category(item_name)
                item_categorias_cache[item_name] = categoria
            else:
                categoria = item_categorias_cache[item_name]
            
            if categoria:
                categoria_counts[categoria] += delivery.qty
            
            # Extraer hora del timestamp
            try:
                if isinstance(delivery.timestamp, str):
                    hour = int(delivery.timestamp[11:13])  # HH
                else:
                    # Es un objeto datetime
                    hour = delivery.timestamp.hour
                hour_counts[hour] += delivery.qty
            except (ValueError, IndexError, AttributeError):
                pass
        
        # Calcular contadores del turno
        now = datetime.now()
        shift_count = total_qty  # Total del turno
        
        # Hora pico
        peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
        peak_hour_count = hour_counts.get(peak_hour, 0)
        
        # Estadísticas de hora actual
        current_hour = now.hour
        current_hour_count = hour_counts.get(current_hour, 0)
        
        # Promedio por hora (aproximado)
        hours_elapsed = max(1, (now - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() / 3600)
        avg_per_hour = shift_count / hours_elapsed if hours_elapsed > 0 else 0
        
        # Top productos
        top_items = [{'name': name, 'count': count} for name, count in item_counts.most_common(10)]
        top_bartenders = [{'name': name, 'count': count} for name, count in bartender_counts.most_common(10)]
        top_barras = [{'name': name, 'count': count} for name, count in barra_counts.most_common(10)]
        top_categorias = [{'name': name, 'count': count} for name, count in categoria_counts.most_common(10)]
        
        return {
            'today_count': shift_count,
            'week_count': shift_count,  # Para compatibilidad
            'month_count': shift_count,  # Para compatibilidad
            'total_qty': total_qty,
            'top_items': top_items,
            'top_bartenders': top_bartenders,
            'top_barras': top_barras,
            'top_categorias': top_categorias,
            'hour_counts': dict(hour_counts),
            'peak_hour': peak_hour,
            'peak_hour_count': peak_hour_count,
            'current_hour': current_hour,
            'current_hour_count': current_hour_count,
            'avg_per_hour': avg_per_hour
        }
    
    def get_delivery_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas de entregas.
        
        Args:
            start_date: Fecha de inicio (YYYY-MM-DD) - opcional
            end_date: Fecha de fin (YYYY-MM-DD) - opcional
            
        Returns:
            dict: Estadísticas de entregas
        """
        all_deliveries = self.delivery_repository.find_all()
        
        # Filtrar por fechas si se proporcionan
        if start_date or end_date:
            filtered_deliveries = []
            for delivery in all_deliveries:
                # Manejar timestamp como string o datetime
                if isinstance(delivery.timestamp, str):
                    timestamp_str = delivery.timestamp[:10]  # YYYY-MM-DD
                else:
                    # Es un objeto datetime
                    timestamp_str = delivery.timestamp.strftime('%Y-%m-%d')
                
                if start_date and timestamp_str < start_date:
                    continue
                if end_date and timestamp_str > end_date:
                    continue
                filtered_deliveries.append(delivery)
            all_deliveries = filtered_deliveries
        
        # Contadores
        item_counts = Counter()
        bartender_counts = Counter()
        barra_counts = Counter()
        categoria_counts = Counter()  # Nuevo: contador de categorías
        total_qty = 0
        
        # Contar por hora
        hour_counts = Counter()
        
        # Cache de categorías por item_name para evitar múltiples consultas
        item_categorias_cache = {}
        
        for delivery in all_deliveries:
            item_counts[delivery.item_name] += delivery.qty
            bartender_counts[delivery.bartender] += delivery.qty
            barra_counts[delivery.barra] += delivery.qty
            total_qty += delivery.qty
            
            # Obtener categoría del producto
            item_name = delivery.item_name
            if item_name not in item_categorias_cache:
                categoria = self._get_item_category(item_name)
                item_categorias_cache[item_name] = categoria
            else:
                categoria = item_categorias_cache[item_name]
            
            if categoria:
                categoria_counts[categoria] += delivery.qty
            
            # Extraer hora del timestamp
            try:
                if isinstance(delivery.timestamp, str):
                    hour = int(delivery.timestamp[11:13])  # HH
                else:
                    # Es un objeto datetime
                    hour = delivery.timestamp.hour
                hour_counts[hour] += delivery.qty
            except (ValueError, IndexError, AttributeError):
                pass
        
        # Calcular hoy, esta semana, este mes
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        today_count = 0
        week_count = 0
        month_count = 0
        day_counts = defaultdict(int)  # Días de la semana (0-6)
        date_counts = defaultdict(int)  # Por fecha (YYYY-MM-DD)
        hour_item_counts = defaultdict(lambda: defaultdict(int))  # Items por hora
        
        for delivery in all_deliveries:
            try:
                # Parsear timestamp
                if isinstance(delivery.timestamp, str):
                    delivery_time = datetime.strptime(delivery.timestamp, '%Y-%m-%d %H:%M:%S')
                else:
                    delivery_time = delivery.timestamp
                
                # Contadores por período
                if delivery_time >= today_start:
                    today_count += delivery.qty
                if delivery_time >= week_start:
                    week_count += delivery.qty
                if delivery_time >= month_start:
                    month_count += delivery.qty
                
                # Por día de la semana
                day_of_week = delivery_time.weekday()
                day_counts[day_of_week] += delivery.qty
                
                # Por fecha
                date_key = delivery_time.strftime('%Y-%m-%d')
                date_counts[date_key] += delivery.qty
                
                # Items por hora
                hour = delivery_time.hour
                hour_item_counts[hour][delivery.item_name] += delivery.qty
            except Exception as e:
                current_app.logger.warning(f"Error procesando delivery timestamp: {e}")
                pass
        
        # Estadísticas de hora actual
        current_hour = now.hour
        current_hour_count = hour_counts.get(current_hour, 0)
        
        # Hora pico
        peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
        peak_hour_count = hour_counts.get(peak_hour, 0)
        
        # Promedio por hora
        total_days = len(set(d.timestamp[:10] if isinstance(d.timestamp, str) else d.timestamp.strftime('%Y-%m-%d') for d in all_deliveries)) or 1
        total_hours = sum(hour_counts.values())
        avg_per_hour = total_hours / 24 / total_days if total_days > 0 else 0
        
        # Verificar si es hora ocupada o lenta
        is_busy_hour = current_hour_count > avg_per_hour * 1.5 if avg_per_hour > 0 else False
        is_slow_hour = current_hour_count < avg_per_hour * 0.5 if avg_per_hour > 0 else False
        
        # Preparar datos para gráficos - horas del día (21:00 a 06:00)
        hours_data = []
        hours_labels = []
        for i in range(10):  # 21:00 a 06:00
            hour = (21 + i) % 24
            hours_data.append(hour_counts.get(hour, 0))
            hours_labels.append(f"{hour:02d}:00")
        
        # Días de la semana
        days_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        days_data = [day_counts.get(d, 0) for d in range(7)]
        
        # Últimos 7 días
        last_7_days = []
        last_7_days_labels = []
        for i in range(6, -1, -1):
            date = (now - timedelta(days=i)).strftime('%Y-%m-%d')
            last_7_days_labels.append((now - timedelta(days=i)).strftime('%d/%m'))
            last_7_days.append(date_counts.get(date, 0))
        
        # Top productos por hora
        top_hours_with_items = []
        for hour in range(24):
            if hour_counts[hour] > 0:
                top_items_hour = sorted(hour_item_counts[hour].items(), key=lambda x: x[1], reverse=True)[:3]
                top_hours_with_items.append({
                    'hour': hour,
                    'total': hour_counts[hour],
                    'top_items': top_items_hour
                })
        top_hours_with_items.sort(key=lambda x: x['total'], reverse=True)
        
        return {
            'total_deliveries': len(all_deliveries),
            'total_qty': total_qty,
            'today_count': today_count,
            'week_count': week_count,
            'month_count': month_count,
            'top_items': item_counts.most_common(20),
            'top_bartenders': bartender_counts.most_common(20),
            'top_barras': barra_counts.most_common(10),
            'top_categorias': categoria_counts.most_common(15),  # Nuevo: rankings de categorías
            'hour_counts': dict(hour_counts),
            'hours_data': hours_data,
            'hours_labels': hours_labels,
            'days_data': days_data,
            'days_names': days_names,
            'last_7_days': last_7_days,
            'last_7_days_labels': last_7_days_labels,
            'top_hours_with_items': top_hours_with_items[:10],
            'current_hour': current_hour,
            'current_hour_count': current_hour_count,
            'peak_hour': peak_hour,
            'peak_hour_count': peak_hour_count,
            'avg_per_hour': round(avg_per_hour, 1),
            'is_busy_hour': is_busy_hour,
            'is_slow_hour': is_slow_hour
        }
    
    def get_shift_stats(self, shift_date: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene estadísticas de un turno específico.
        
        Args:
            shift_date: Fecha del turno (YYYY-MM-DD)
            
        Returns:
            dict: Estadísticas del turno o None
        """
        # Obtener entregas del turno
        deliveries = self.delivery_repository.find_by_shift_date(shift_date)
        
        if not deliveries:
            return None
        
        # Contadores
        item_counts = Counter()
        bartender_counts = Counter()
        barra_counts = Counter()
        categoria_counts = Counter()  # Nuevo: contador de categorías
        total_qty = 0
        
        # Cache de categorías por item_name
        item_categorias_cache = {}
        
        for delivery in deliveries:
            item_counts[delivery.item_name] += delivery.qty
            bartender_counts[delivery.bartender] += delivery.qty
            barra_counts[delivery.barra] += delivery.qty
            total_qty += delivery.qty
            
            # Obtener categoría del producto
            item_name = delivery.item_name
            if item_name not in item_categorias_cache:
                categoria = self._get_item_category(item_name)
                item_categorias_cache[item_name] = categoria
            else:
                categoria = item_categorias_cache[item_name]
            
            if categoria:
                categoria_counts[categoria] += delivery.qty
        
        # Obtener información del turno
        shift_history = self.shift_repository.get_shift_history(limit=365)
        shift_info = None
        for shift in shift_history:
            if shift.get('shift_date') == shift_date:
                shift_info = shift
                break
        
        return {
            'shift_date': shift_date,
            'total_entregas': len(deliveries),
            'total_cantidad': total_qty,
            'top_items': item_counts.most_common(5),
            'top_bartenders': bartender_counts.most_common(3),
            'top_barras': barra_counts.most_common(3),
            'top_categorias': categoria_counts.most_common(10),  # Nuevo: rankings de categorías
            'shift_info': shift_info
        }
    
    def get_shifts_history_stats(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Obtiene estadísticas de turnos cerrados.
        
        Args:
            limit: Número máximo de turnos a retornar
            
        Returns:
            List[dict]: Lista de estadísticas por turno
        """
        shift_history = self.shift_repository.get_shift_history(limit=limit)
        shifts_stats = []
        
        for shift in shift_history:
            shift_date = shift.get('shift_date', '')
            if not shift_date:
                continue
            
            # Obtener estadísticas del turno (puede ser None si no hay entregas)
            stats = self.get_shift_stats(shift_date)
            
            # Si no hay estadísticas, crear estructura básica
            if not stats:
                stats = {
                    'shift_date': shift_date,
                    'total_entregas': 0,
                    'total_cantidad': 0,
                    'top_items': [],
                    'top_bartenders': [],
                    'top_barras': []
                }
            
            # Agregar información del turno (siempre presente)
            stats['opened_at'] = shift.get('opened_at', '')
            stats['closed_at'] = shift.get('closed_at', '')
            stats['opened_by'] = shift.get('opened_by', 'admin')
            stats['closed_by'] = shift.get('closed_by', 'admin')
            stats['fiesta_nombre'] = shift.get('fiesta_nombre', '')
            stats['djs'] = shift.get('djs', '')
            stats['barras_disponibles'] = shift.get('barras_disponibles', [])
            stats['bartenders'] = shift.get('bartenders', [])
            
            # Obtener estadísticas de encuestas para este turno
            survey_stats = self._get_survey_stats_for_shift(shift_date)
            stats['survey_stats'] = survey_stats
            
            shifts_stats.append(stats)
        
        return shifts_stats
    
    def _get_survey_stats_for_shift(self, shift_date: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas de encuestas para un turno específico.
        
        Args:
            shift_date: Fecha del turno (YYYY-MM-DD)
            
        Returns:
            dict: Estadísticas de encuestas del turno
        """
        try:
            # Obtener respuestas de encuestas para la fecha del turno
            # El survey_repo usa survey_repository, así que usamos el atributo correcto
            responses = self.survey_repository.find_responses_by_session_date(shift_date)
            
            if not responses:
                return {
                    'total_respuestas': 0,
                    'promedio_rating': 0.0,
                    'ratings_count': {},
                    'by_barra': {},
                    'has_data': False
                }
            
            # Calcular estadísticas
            ratings = [r.rating for r in responses if hasattr(r, 'rating') and r.rating]
            total_respuestas = len(responses)
            promedio_rating = sum(ratings) / len(ratings) if ratings else 0.0
            
            # Contadores
            ratings_count = Counter()
            by_barra = Counter()
            
            for r in responses:
                if hasattr(r, 'rating') and r.rating:
                    ratings_count[r.rating] += 1
                if hasattr(r, 'barra') and r.barra:
                    by_barra[r.barra] += 1
            
            return {
                'total_respuestas': total_respuestas,
                'promedio_rating': round(promedio_rating, 2),
                'ratings_count': dict(ratings_count),
                'by_barra': dict(by_barra),
                'has_data': True
            }
        except Exception as e:
            current_app.logger.error(f"Error obteniendo estadísticas de encuestas para turno {shift_date}: {e}")
            return {
                'total_respuestas': 0,
                'promedio_rating': 0.0,
                'ratings_count': {},
                'by_barra': {},
                'has_data': False
            }
    
    def get_survey_stats(
        self,
        session_date: Optional[str] = None,
        barra: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas de encuestas.
        
        Args:
            session_date: Fecha de sesión (YYYY-MM-DD) - opcional
            barra: Barra específica ('1' o '2') - opcional
            
        Returns:
            dict: Estadísticas de encuestas
        """
        if session_date:
            responses = self.survey_repository.find_responses_by_session_date(session_date)
        else:
            responses = self.survey_repository.find_all_responses()
        
        if barra:
            responses = [r for r in responses if r.barra == str(barra)]
        
        if not responses:
            return {
                'total_responses': 0,
                'promedio_rating': 0.0,
                'rating_distribution': {},
                'barra_stats': {}
            }
        
        # Calcular estadísticas
        total_responses = len(responses)
        total_rating = sum(r.rating for r in responses)
        promedio_rating = round(total_rating / total_responses, 2) if total_responses > 0 else 0.0
        
        # Distribución de ratings
        rating_distribution = Counter(r.rating for r in responses)
        
        # Estadísticas por barra
        barra_stats = defaultdict(lambda: {'total': 0, 'sum_rating': 0, 'ratings': []})
        for response in responses:
            barra_key = response.barra
            barra_stats[barra_key]['total'] += 1
            barra_stats[barra_key]['sum_rating'] += response.rating
            barra_stats[barra_key]['ratings'].append(response.rating)
        
        # Calcular promedios por barra
        for barra_key in barra_stats:
            stats = barra_stats[barra_key]
            stats['promedio'] = round(
                stats['sum_rating'] / stats['total'], 2
            ) if stats['total'] > 0 else 0.0
        
        return {
            'total_responses': total_responses,
            'promedio_rating': promedio_rating,
            'rating_distribution': dict(rating_distribution),
            'barra_stats': dict(barra_stats)
        }
    
    def get_cashiers_and_registers_stats_from_log_for_shift(self, shift) -> Dict[str, Any]:
        """
        Obtiene estadísticas de cajeros y cajas desde el log local para un turno específico (NO consulta API).
        
        Args:
            shift: ShiftStatus del turno actual
            
        Returns:
            dict: Estadísticas de cajeros y cajas del turno desde el log
        """
        from datetime import datetime
        try:
            from app.helpers.ticket_scans import get_all_ticket_scans
            ticket_scans = get_all_ticket_scans()
            
            # Filtrar por turno
            shift_opened_at = datetime.fromisoformat(shift.opened_at.replace('Z', '+00:00').replace('+00:00', ''))
            if shift_opened_at.tzinfo is not None:
                shift_opened_at = shift_opened_at.replace(tzinfo=None)
            
            cashier_sales_count = Counter()
            cashier_total_amount = defaultdict(float)
            cashier_names = {}
            
            register_sales_count = Counter()
            register_total_amount = defaultdict(float)
            register_names = {}
            
            # Ya están filtrados por fecha en SQL, no necesitamos filtrar de nuevo
            for sale_id, ticket_data in ticket_scans.items():
                
                sale_data = ticket_data.get('sale_data', {})
                employee_id = str(ticket_data.get('employee_id') or sale_data.get('employee_id') or sale_data.get('sold_by_employee_id') or '')
                register_id = str(ticket_data.get('register_id') or sale_data.get('register_id') or '')
                sale_total = float(sale_data.get('total', sale_data.get('sale_total', 0)) or 0)
                
                # Usar nombres guardados en el log
                vendedor = ticket_data.get('vendedor', 'Desconocido')
                caja = ticket_data.get('caja', 'Caja desconocida')
                
                # Contar por cajero
                if employee_id and employee_id != 'Sin cajero' and employee_id:
                    cashier_sales_count[employee_id] += 1
                    cashier_total_amount[employee_id] += sale_total
                    if employee_id not in cashier_names:
                        cashier_names[employee_id] = vendedor if vendedor != 'Desconocido' else f'Cajero {employee_id}'
                
                # Contar por caja
                if register_id and register_id != 'Sin caja' and register_id:
                    register_sales_count[register_id] += 1
                    register_total_amount[register_id] += sale_total
                    if register_id not in register_names:
                        register_names[register_id] = caja if caja != 'Caja desconocida' else f'Caja {register_id}'
            
            # Top cajeros por cantidad de ventas
            top_cashiers_by_count = []
            for employee_id, count in cashier_sales_count.most_common(20):
                top_cashiers_by_count.append({
                    'id': employee_id,
                    'name': cashier_names.get(employee_id, f'Cajero {employee_id}'),
                    'sales_count': count,
                    'total_amount': cashier_total_amount.get(employee_id, 0)
                })
            
            # Top cajeros por monto total
            top_cashiers_by_amount = sorted(
                [(eid, cashier_total_amount.get(eid, 0)) for eid in cashier_sales_count.keys()],
                key=lambda x: x[1],
                reverse=True
            )[:20]
            top_cashiers_by_amount_list = []
            for employee_id, total_amount in top_cashiers_by_amount:
                top_cashiers_by_amount_list.append({
                    'id': employee_id,
                    'name': cashier_names.get(employee_id, f'Cajero {employee_id}'),
                    'sales_count': cashier_sales_count.get(employee_id, 0),
                    'total_amount': total_amount
                })
            
            # Top cajas por cantidad de ventas
            top_registers_by_count = []
            for register_id, count in register_sales_count.most_common(10):
                top_registers_by_count.append({
                    'id': register_id,
                    'name': register_names.get(register_id, f'Caja {register_id}'),
                    'sales_count': count,
                    'total_amount': register_total_amount.get(register_id, 0)
                })
            
            # Top cajas por monto total
            top_registers_by_amount = sorted(
                [(rid, register_total_amount.get(rid, 0)) for rid in register_sales_count.keys()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            top_registers_by_amount_list = []
            for register_id, total_amount in top_registers_by_amount:
                top_registers_by_amount_list.append({
                    'id': register_id,
                    'name': register_names.get(register_id, f'Caja {register_id}'),
                    'sales_count': register_sales_count.get(register_id, 0),
                    'total_amount': total_amount
                })
            
            return {
                'top_cashiers_by_count': top_cashiers_by_count,
                'top_cashiers_by_amount': top_cashiers_by_amount_list,
                'top_registers_by_count': top_registers_by_count,
                'top_registers_by_amount': top_registers_by_amount_list
            }
        except Exception as e:
            current_app.logger.error(f"Error al obtener estadísticas de cajeros y cajas desde log: {e}")
            return {
                'top_cashiers_by_count': [],
                'top_cashiers_by_amount': [],
                'top_registers_by_count': [],
                'top_registers_by_amount': []
            }
    
    def get_cashiers_and_registers_stats(self, limit: int = 5000) -> Dict[str, Any]:
        """
        Obtiene estadísticas de cajeros y cajas.
        
        Args:
            limit: Límite de ventas a procesar
            
        Returns:
            dict: Estadísticas de cajeros y cajas
        """
        try:
            all_sales = self.pos_client.get_all_sales(limit=limit)
            
            cashier_sales_count = Counter()
            cashier_total_amount = defaultdict(float)
            cashier_names = {}
            
            register_sales_count = Counter()
            register_total_amount = defaultdict(float)
            register_names = {}
            
            for sale in all_sales:
                employee_id = str(sale.get('employee_id', '')) or 'Sin cajero'
                register_id = str(sale.get('register_id', '')) or 'Sin caja'
                sale_total = sale.get('sale_total', 0)
                
                # Contar por cajero
                if employee_id and employee_id != 'Sin cajero':
                    cashier_sales_count[employee_id] += 1
                    cashier_total_amount[employee_id] += sale_total
                    
                    if employee_id not in cashier_names:
                        employee_info = self.pos_client.get_entity_details("employees", employee_id)
                        if employee_info:
                            name = f"{employee_info.get('first_name', '')} {employee_info.get('last_name', '')}".strip()
                            cashier_names[employee_id] = name or employee_info.get('name', f'Cajero {employee_id}')
                        else:
                            cashier_names[employee_id] = f'Cajero {employee_id}'
                
                # Contar por caja
                if register_id and register_id != 'Sin caja':
                    register_sales_count[register_id] += 1
                    register_total_amount[register_id] += sale_total
                    
                    if register_id not in register_names:
                        register_info = self.pos_client.get_entity_details("registers", register_id)
                        if register_info:
                            register_names[register_id] = register_info.get('name', f'Caja {register_id}')
                        else:
                            register_names[register_id] = f'Caja {register_id}'
            
            # Top cajeros por cantidad de ventas
            top_cashiers_by_count = []
            for employee_id, count in cashier_sales_count.most_common(20):
                top_cashiers_by_count.append({
                    'id': employee_id,
                    'name': cashier_names.get(employee_id, f'Cajero {employee_id}'),
                    'sales_count': count,
                    'total_amount': cashier_total_amount.get(employee_id, 0)
                })
            
            # Top cajeros por monto total
            top_cashiers_by_amount = sorted(
                [(eid, cashier_total_amount.get(eid, 0)) for eid in cashier_sales_count.keys()],
                key=lambda x: x[1],
                reverse=True
            )[:20]
            top_cashiers_by_amount_list = []
            for employee_id, total_amount in top_cashiers_by_amount:
                top_cashiers_by_amount_list.append({
                    'id': employee_id,
                    'name': cashier_names.get(employee_id, f'Cajero {employee_id}'),
                    'sales_count': cashier_sales_count.get(employee_id, 0),
                    'total_amount': total_amount
                })
            
            # Top cajas por cantidad de ventas
            top_registers_by_count = []
            for register_id, count in register_sales_count.most_common(10):
                top_registers_by_count.append({
                    'id': register_id,
                    'name': register_names.get(register_id, f'Caja {register_id}'),
                    'sales_count': count,
                    'total_amount': register_total_amount.get(register_id, 0)
                })
            
            # Top cajas por monto total
            top_registers_by_amount = sorted(
                [(rid, register_total_amount.get(rid, 0)) for rid in register_sales_count.keys()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            top_registers_by_amount_list = []
            for register_id, total_amount in top_registers_by_amount:
                top_registers_by_amount_list.append({
                    'id': register_id,
                    'name': register_names.get(register_id, f'Caja {register_id}'),
                    'sales_count': register_sales_count.get(register_id, 0),
                    'total_amount': total_amount
                })
            
            return {
                'top_cashiers_by_count': top_cashiers_by_count,
                'top_cashiers_by_amount': top_cashiers_by_amount_list,
                'top_registers_by_count': top_registers_by_count,
                'top_registers_by_amount': top_registers_by_amount_list
            }
        except Exception as e:
            current_app.logger.error(f"Error al obtener estadísticas de cajeros y cajas: {e}")
            return {
                'top_cashiers_by_count': [],
                'top_cashiers_by_amount': [],
                'top_registers_by_count': [],
                'top_registers_by_amount': []
            }
    
    def get_entradas_stats_from_log_for_shift(self, shift) -> Dict[str, Any]:
        """
        Obtiene estadísticas de entradas desde el log local para un turno específico.
        
        Args:
            shift: ShiftStatus del turno actual
            
        Returns:
            dict: Estadísticas de entradas del turno
        """
        from datetime import datetime
        try:
            # OPTIMIZACIÓN: Usar consulta SQL filtrada en lugar de cargar todo en memoria
            from app.helpers.ticket_scans import get_ticket_scans_since
            
            # Filtrar por turno
            shift_opened_at = datetime.fromisoformat(shift.opened_at.replace('Z', '+00:00').replace('+00:00', ''))
            if shift_opened_at.tzinfo is not None:
                shift_opened_at = shift_opened_at.replace(tzinfo=None)
            
            # Obtener solo tickets desde el inicio del turno (optimizado con SQL)
            ticket_scans = get_ticket_scans_since(shift_opened_at)
            
            # Contadores
            entradas_5000_count = 0
            entradas_10000_count = 0
            entradas_other_count = 0
            hour_counts = Counter()
            date_counts = defaultdict(int)
            
            # Ya están filtrados por fecha en SQL, procesar directamente
            for sale_id, ticket_data in ticket_scans.items():
                # Obtener fecha del ticket (ya está en el rango correcto)
                scanned_at = ticket_data.get('scanned_at', '')
                ticket_time = None
                if scanned_at:
                    try:
                        ticket_time = datetime.fromisoformat(scanned_at.replace('Z', '+00:00').replace('+00:00', ''))
                        if ticket_time.tzinfo is not None:
                            ticket_time = ticket_time.replace(tzinfo=None)
                    except:
                        pass
                
                if not ticket_time:
                    fecha_venta = ticket_data.get('fecha_venta', '')
                    if fecha_venta and len(fecha_venta) >= 19:
                        try:
                            ticket_time = datetime.strptime(fecha_venta[:19], '%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                
                # Si aún no tenemos ticket_time, saltar este registro
                if not ticket_time:
                    continue
                
                items = ticket_data.get('items', [])
                fecha_venta = ticket_data.get('fecha_venta', '')
                
                for item in items:
                    item_name = item.get('name', '').lower()
                    if 'entrada' in item_name:
                        qty = item.get('quantity', 0)
                        price = item.get('unit_price', 0) or item.get('price', 0)
                        
                        # Si no hay precio, intentar calcular desde sale_data
                        if not price:
                            sale_data = ticket_data.get('sale_data', {})
                            total = float(sale_data.get('total', 0) or 0)
                            if total > 0 and qty > 0:
                                price = total / qty
                        
                        if abs(price - 5000) < 100:
                            entradas_5000_count += qty
                        elif abs(price - 10000) < 100:
                            entradas_10000_count += qty
                        else:
                            entradas_other_count += qty
                        
                        # Contar por hora
                        if fecha_venta and len(fecha_venta) >= 13:
                            try:
                                hour = int(fecha_venta[11:13])  # HH
                                hour_counts[hour] += qty
                            except (ValueError, IndexError):
                                pass
                        
                        # Contar por fecha
                        if fecha_venta and len(fecha_venta) >= 10:
                            try:
                                date_key = fecha_venta[:10]  # YYYY-MM-DD
                                date_counts[date_key] += qty
                            except:
                                pass
            
            total_personas = entradas_5000_count + entradas_10000_count + entradas_other_count
            
            # Hora pico de entradas
            peak_entradas_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
            peak_entradas_count = hour_counts.get(peak_entradas_hour, 0)
            
            # Preparar datos para gráficos - horas del día (21:00 a 06:00)
            entradas_hours_data = []
            entradas_hours_5000_data = []
            entradas_hours_10000_data = []
            entradas_hours_labels = []
            
            # Separar por precio para gráficos por hora
            entradas_hour_5000 = defaultdict(int)
            entradas_hour_10000 = defaultdict(int)
            
            for sale_id, ticket_data in ticket_scans.items():
                scanned_at = ticket_data.get('scanned_at', '')
                ticket_time = None
                if scanned_at:
                    try:
                        ticket_time = datetime.fromisoformat(scanned_at.replace('Z', '+00:00').replace('+00:00', ''))
                        if ticket_time.tzinfo is not None:
                            ticket_time = ticket_time.replace(tzinfo=None)
                    except:
                        pass
                
                if not ticket_time or ticket_time < shift_opened_at:
                    continue
                
                items = ticket_data.get('items', [])
                fecha_venta = ticket_data.get('fecha_venta', '')
                
                if fecha_venta and len(fecha_venta) >= 13:
                    try:
                        hour = int(fecha_venta[11:13])  # HH
                        for item in items:
                            item_name = item.get('name', '').lower()
                            if 'entrada' in item_name:
                                price = item.get('unit_price', 0) or item.get('price', 0)
                                if not price:
                                    sale_data = ticket_data.get('sale_data', {})
                                    total = float(sale_data.get('total', 0) or 0)
                                    qty = item.get('quantity', 0)
                                    if total > 0 and qty > 0:
                                        price = total / qty
                                
                                qty = item.get('quantity', 0)
                                
                                if abs(price - 5000) < 100:
                                    entradas_hour_5000[hour] += qty
                                elif abs(price - 10000) < 100:
                                    entradas_hour_10000[hour] += qty
                    except (ValueError, IndexError):
                        pass
            
            # Generar datos para gráficos (21:00 a 06:00)
            for i in range(10):
                hour = (21 + i) % 24
                entradas_hours_data.append(hour_counts.get(hour, 0))
                entradas_hours_5000_data.append(entradas_hour_5000.get(hour, 0))
                entradas_hours_10000_data.append(entradas_hour_10000.get(hour, 0))
                entradas_hours_labels.append(f"{hour:02d}:00")
            
            # Últimos 7 días (del turno)
            last_7_days = []
            last_7_days_labels = []
            now = datetime.now()
            for i in range(6, -1, -1):
                date = (now - timedelta(days=i)).strftime('%Y-%m-%d')
                last_7_days_labels.append((now - timedelta(days=i)).strftime('%d/%m'))
                last_7_days.append(date_counts.get(date, 0))
            
            return {
                'total_personas': total_personas,
                'entradas_5000_count': entradas_5000_count,
                'entradas_10000_count': entradas_10000_count,
                'entradas_other_count': entradas_other_count,
                'hour_counts': dict(hour_counts),
                'entradas_hours_data': entradas_hours_data,
                'entradas_hours_5000_data': entradas_hours_5000_data,
                'entradas_hours_10000_data': entradas_hours_10000_data,
                'entradas_hours_labels': entradas_hours_labels,
                'peak_entradas_hour': peak_entradas_hour,
                'peak_entradas_count': peak_entradas_count,
                'last_7_days': last_7_days,
                'last_7_days_labels': last_7_days_labels
            }
        except Exception as e:
            current_app.logger.error(f"Error al obtener estadísticas de entradas desde log para turno: {e}")
            return {
                'total_personas': 0,
                'entradas_5000_count': 0,
                'entradas_10000_count': 0,
                'entradas_other_count': 0,
                'hour_counts': {},
                'entradas_hours_data': [],
                'entradas_hours_5000_data': [],
                'entradas_hours_10000_data': [],
                'entradas_hours_labels': [],
                'peak_entradas_hour': 0,
                'peak_entradas_count': 0,
                'last_7_days': [],
                'last_7_days_labels': []
            }
    
    def get_entradas_stats_from_log(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de entradas desde el log local (NO consulta API).
        
        Returns:
            dict: Estadísticas de entradas desde el log
        """
        try:
            from app.helpers.ticket_scans import get_all_ticket_scans
            ticket_scans = get_all_ticket_scans()
            
            # Contadores
            entradas_5000_count = 0
            entradas_10000_count = 0
            entradas_other_count = 0
            hour_counts = Counter()
            date_counts = defaultdict(int)
            
            for sale_id, ticket_data in ticket_scans.items():
                items = ticket_data.get('items', [])
                fecha_venta = ticket_data.get('fecha_venta', '')
                
                for item in items:
                    item_name = item.get('name', '').lower()
                    if 'entrada' in item_name:
                        qty = item.get('quantity', 0)
                        price = item.get('unit_price', 0) or item.get('price', 0)
                        
                        # Si no hay precio, intentar calcular desde sale_data
                        if not price:
                            sale_data = ticket_data.get('sale_data', {})
                            total = float(sale_data.get('total', 0) or 0)
                            if total > 0 and qty > 0:
                                price = total / qty
                        
                        if abs(price - 5000) < 100:
                            entradas_5000_count += qty
                        elif abs(price - 10000) < 100:
                            entradas_10000_count += qty
                        else:
                            entradas_other_count += qty
                        
                        # Contar por hora
                        if fecha_venta and len(fecha_venta) >= 13:
                            try:
                                hour = int(fecha_venta[11:13])  # HH
                                hour_counts[hour] += qty
                            except (ValueError, IndexError):
                                pass
                        
                        # Contar por fecha
                        if fecha_venta and len(fecha_venta) >= 10:
                            try:
                                date_key = fecha_venta[:10]  # YYYY-MM-DD
                                date_counts[date_key] += qty
                            except:
                                pass
            
            total_personas = entradas_5000_count + entradas_10000_count + entradas_other_count
            
            # Hora pico de entradas
            peak_entradas_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
            peak_entradas_count = hour_counts.get(peak_entradas_hour, 0)
            
            # Preparar datos para gráficos - horas del día (21:00 a 06:00)
            entradas_hours_data = []
            entradas_hours_5000_data = []
            entradas_hours_10000_data = []
            entradas_hours_labels = []
            
            # Separar por precio para gráficos por hora
            entradas_hour_5000 = defaultdict(int)
            entradas_hour_10000 = defaultdict(int)
            
            for sale_id, ticket_data in ticket_scans.items():
                items = ticket_data.get('items', [])
                fecha_venta = ticket_data.get('fecha_venta', '')
                
                if fecha_venta and len(fecha_venta) >= 13:
                    try:
                        hour = int(fecha_venta[11:13])  # HH
                        for item in items:
                            item_name = item.get('name', '').lower()
                            if 'entrada' in item_name:
                                price = item.get('unit_price', 0) or item.get('price', 0)
                                if not price:
                                    sale_data = ticket_data.get('sale_data', {})
                                    total = float(sale_data.get('total', 0) or 0)
                                    qty = item.get('quantity', 0)
                                    if total > 0 and qty > 0:
                                        price = total / qty
                                
                                qty = item.get('quantity', 0)
                                
                                if abs(price - 5000) < 100:
                                    entradas_hour_5000[hour] += qty
                                elif abs(price - 10000) < 100:
                                    entradas_hour_10000[hour] += qty
                    except (ValueError, IndexError):
                        pass
            
            # Generar datos para gráficos (21:00 a 06:00)
            for i in range(10):
                hour = (21 + i) % 24
                entradas_hours_data.append(hour_counts.get(hour, 0))
                entradas_hours_5000_data.append(entradas_hour_5000.get(hour, 0))
                entradas_hours_10000_data.append(entradas_hour_10000.get(hour, 0))
                entradas_hours_labels.append(f"{hour:02d}:00")
            
            # Últimos 7 días
            last_7_days = []
            last_7_days_labels = []
            now = datetime.now()
            for i in range(6, -1, -1):
                date = (now - timedelta(days=i)).strftime('%Y-%m-%d')
                last_7_days_labels.append((now - timedelta(days=i)).strftime('%d/%m'))
                last_7_days.append(date_counts.get(date, 0))
            
            return {
                'total_personas': total_personas,
                'entradas_5000_count': entradas_5000_count,
                'entradas_10000_count': entradas_10000_count,
                'entradas_other_count': entradas_other_count,
                'hour_counts': dict(hour_counts),
                'entradas_hours_data': entradas_hours_data,
                'entradas_hours_5000_data': entradas_hours_5000_data,
                'entradas_hours_10000_data': entradas_hours_10000_data,
                'entradas_hours_labels': entradas_hours_labels,
                'peak_entradas_hour': peak_entradas_hour,
                'peak_entradas_count': peak_entradas_count,
                'last_7_days': last_7_days,
                'last_7_days_labels': last_7_days_labels
            }
        except Exception as e:
            current_app.logger.error(f"Error al obtener estadísticas de entradas desde log: {e}")
            return {
                'total_personas': 0,
                'entradas_5000_count': 0,
                'entradas_10000_count': 0,
                'entradas_other_count': 0,
                'hour_counts': {},
                'entradas_hours_data': [],
                'entradas_hours_5000_data': [],
                'entradas_hours_10000_data': [],
                'entradas_hours_labels': [],
                'peak_entradas_hour': 0,
                'peak_entradas_count': 0,
                'last_7_days': [],
                'last_7_days_labels': []
            }
    
    def get_entradas_stats(self, limit: int = 1000) -> Dict[str, Any]:
        """
        Obtiene estadísticas de entradas vendidas.
        
        Args:
            limit: Límite de ventas a procesar
            
        Returns:
            dict: Estadísticas de entradas
        """
        try:
            # Obtener ventas de entradas desde POS API
            entradas_sales = self.pos_client.get_entradas_sales(limit=limit)
            
            if not entradas_sales:
                return {
                    'total_personas': 0,
                    'entradas_5000_count': 0,
                    'entradas_10000_count': 0,
                    'entradas_other_count': 0,
                    'hour_counts': {},
                    'last_7_days': []
                }
            
            # Contadores
            entradas_5000_count = 0
            entradas_10000_count = 0
            entradas_other_count = 0
            hour_counts = Counter()
            
            for sale in entradas_sales:
                cart_items = sale.get('cart_items', [])
                for item in cart_items:
                    item_name = item.get('name', '').lower()
                    qty = item.get('quantity', 0)
                    
                    if 'entrada' in item_name:
                        price = item.get('unit_price', 0)
                        if price == 5000:
                            entradas_5000_count += qty
                        elif price == 10000:
                            entradas_10000_count += qty
                        else:
                            entradas_other_count += qty
                        
                        # Contar por hora
                        sale_time = sale.get('sale_time', '')
                        if sale_time:
                            try:
                                hour = int(sale_time[11:13])  # HH
                                hour_counts[hour] += qty
                            except (ValueError, IndexError):
                                pass
            
            total_personas = entradas_5000_count + entradas_10000_count + entradas_other_count
            
            # Hora pico de entradas
            peak_entradas_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
            peak_entradas_count = hour_counts.get(peak_entradas_hour, 0)
            
            # Preparar datos para gráficos - horas del día (21:00 a 06:00)
            entradas_hours_data = []
            entradas_hours_5000_data = []
            entradas_hours_10000_data = []
            entradas_hours_labels = []
            
            # Separar por precio para gráficos por hora
            entradas_hour_5000 = defaultdict(int)
            entradas_hour_10000 = defaultdict(int)
            
            for sale in entradas_sales:
                cart_items = sale.get('cart_items', [])
                sale_time = sale.get('sale_time', '')
                
                if sale_time:
                    try:
                        hour = int(sale_time[11:13])  # HH
                        for item in cart_items:
                            item_name = item.get('name', '').lower()
                            if 'entrada' in item_name:
                                price = item.get('unit_price', 0)
                                qty = item.get('quantity', 0)
                                
                                if price == 5000:
                                    entradas_hour_5000[hour] += qty
                                elif price == 10000:
                                    entradas_hour_10000[hour] += qty
                    except (ValueError, IndexError):
                        pass
            
            # Generar datos para gráficos (21:00 a 06:00)
            for i in range(10):
                hour = (21 + i) % 24
                entradas_hours_data.append(hour_counts.get(hour, 0))
                entradas_hours_5000_data.append(entradas_hour_5000.get(hour, 0))
                entradas_hours_10000_data.append(entradas_hour_10000.get(hour, 0))
                entradas_hours_labels.append(f"{hour:02d}:00")
            
            # Últimos 7 días
            last_7_days = []
            last_7_days_labels = []
            date_counts = defaultdict(int)
            
            for sale in entradas_sales:
                sale_time = sale.get('sale_time', '')
                if sale_time:
                    try:
                        sale_date = datetime.strptime(sale_time[:10], '%Y-%m-%d')
                        date_key = sale_date.strftime('%Y-%m-%d')
                        cart_items = sale.get('cart_items', [])
                        for item in cart_items:
                            if 'entrada' in item.get('name', '').lower():
                                date_counts[date_key] += item.get('quantity', 0)
                    except (ValueError, IndexError):
                        pass
            
            now = datetime.now()
            for i in range(6, -1, -1):
                date = (now - timedelta(days=i)).strftime('%Y-%m-%d')
                last_7_days_labels.append((now - timedelta(days=i)).strftime('%d/%m'))
                last_7_days.append(date_counts.get(date, 0))
            
            return {
                'total_personas': total_personas,
                'entradas_5000_count': entradas_5000_count,
                'entradas_10000_count': entradas_10000_count,
                'entradas_other_count': entradas_other_count,
                'hour_counts': dict(hour_counts),
                'entradas_hours_data': entradas_hours_data,
                'entradas_hours_5000_data': entradas_hours_5000_data,
                'entradas_hours_10000_data': entradas_hours_10000_data,
                'entradas_hours_labels': entradas_hours_labels,
                'peak_entradas_hour': peak_entradas_hour,
                'peak_entradas_count': peak_entradas_count,
                'last_7_days': last_7_days,
                'last_7_days_labels': last_7_days_labels
            }
        except Exception as e:
            current_app.logger.error(f"Error al obtener estadísticas de entradas: {e}")
            return {
                    'total_personas': 0,
                    'entradas_5000_count': 0,
                    'entradas_10000_count': 0,
                    'entradas_other_count': 0,
                    'hour_counts': {},
                    'entradas_hours_data': [],
                    'entradas_hours_5000_data': [],
                    'entradas_hours_10000_data': [],
                    'entradas_hours_labels': [],
                    'peak_entradas_hour': 0,
                    'peak_entradas_count': 0,
                    'last_7_days': [],
                    'last_7_days_labels': []
                }
    
    def get_rankings_from_closes(
        self,
        period_type: str = 'week',  # 'day', 'week', 'month'
        period_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene rankings desde los cierres diarios de cajas.
        
        Args:
            period_type: Tipo de período ('day', 'week', 'month')
            period_date: Fecha del período (YYYY-MM-DD). Si no se proporciona, usa la fecha actual.
            
        Returns:
            dict: Rankings de cajas, cajeros, etc. basados en cierres diarios
        """
        from datetime import datetime, timedelta
        from app.models.pos_models import RegisterClose
        from collections import Counter, defaultdict
        
        # Calcular rango de fechas según el período
        if period_date:
            base_date = datetime.strptime(period_date, '%Y-%m-%d')
        else:
            base_date = datetime.now()
        
        if period_type == 'day':
            start_date = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = base_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            period_label = base_date.strftime('%d/%m/%Y')
        elif period_type == 'week':
            # Calcular lunes de la semana
            days_since_monday = base_date.weekday()
            week_start = base_date - timedelta(days=days_since_monday)
            start_date = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
            period_label = f"{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}"
        elif period_type == 'month':
            # Primer día del mes
            start_date = base_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Último día del mes
            if base_date.month == 12:
                end_date = base_date.replace(year=base_date.year + 1, month=1, day=1) - timedelta(microseconds=1)
            else:
                end_date = base_date.replace(month=base_date.month + 1, day=1) - timedelta(microseconds=1)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            period_label = base_date.strftime('%B %Y').capitalize()
        else:
            raise ValueError(f"Tipo de período inválido: {period_type}")
        
        current_app.logger.info(f"📊 Obteniendo rankings desde cierres: {period_type} - {period_label}")
        
        # Obtener cierres en el rango de fechas
        closes = RegisterClose.query.filter(
            RegisterClose.closed_at >= start_date,
            RegisterClose.closed_at <= end_date,
            RegisterClose.status.in_(['balanced', 'resolved'])  # Solo cierres completados
        ).all()
        
        current_app.logger.info(f"✅ Encontrados {len(closes)} cierres en el período")
        
        # Contadores para rankings
        cashier_sales_count = Counter()
        cashier_total_amount = defaultdict(float)
        cashier_names = {}
        
        register_sales_count = Counter()
        register_total_amount = defaultdict(float)
        register_names = {}
        
        total_sales = 0
        total_amount = 0.0
        
        # Procesar cierres
        for close in closes:
            # Cajeros
            if close.employee_id:
                cashier_sales_count[close.employee_id] += close.total_sales
                cashier_total_amount[close.employee_id] += float(close.total_amount or 0)
                if close.employee_id not in cashier_names:
                    cashier_names[close.employee_id] = close.employee_name
            
            # Cajas
            if close.register_id:
                register_sales_count[close.register_id] += close.total_sales
                register_total_amount[close.register_id] += float(close.total_amount or 0)
                if close.register_id not in register_names:
                    register_names[close.register_id] = close.register_name
            
            total_sales += close.total_sales
            total_amount += float(close.total_amount or 0)
        
        # Generar rankings de cajeros
        top_cashiers = []
        for employee_id, count in cashier_sales_count.most_common(20):
            top_cashiers.append({
                'id': employee_id,
                'name': cashier_names.get(employee_id, f'Cajero {employee_id}'),
                'sales_count': count,
                'total_amount': cashier_total_amount.get(employee_id, 0)
            })
        
        # Ordenar cajeros por monto también
        top_cashiers_by_amount = sorted(
            top_cashiers,
            key=lambda x: x['total_amount'],
            reverse=True
        )[:20]
        
        # Generar rankings de cajas
        top_registers = []
        for register_id, count in register_sales_count.most_common(20):
            top_registers.append({
                'id': register_id,
                'name': register_names.get(register_id, f'Caja {register_id}'),
                'sales_count': count,
                'total_amount': register_total_amount.get(register_id, 0)
            })
        
        # Ordenar cajas por monto también
        top_registers_by_amount = sorted(
            top_registers,
            key=lambda x: x['total_amount'],
            reverse=True
        )[:20]
        
        current_app.logger.info(f"📊 Rankings generados: {len(top_cashiers)} cajeros, {len(top_registers)} cajas")
        
        return {
            'period_type': period_type,
            'period_label': period_label,
            'period_start': start_date.strftime('%Y-%m-%d'),
            'period_end': end_date.strftime('%Y-%m-%d'),
            'top_cashiers': top_cashiers,
            'top_cashiers_by_amount': top_cashiers_by_amount,
            'top_registers': top_registers,
            'top_registers_by_amount': top_registers_by_amount,
            'total_sales': total_sales,
            'total_amount': total_amount,
            'total_closes': len(closes)
        }
    
    def get_weekly_rankings(
        self,
        week_start_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene rankings semanales para bonos.
        
        Args:
            week_start_date: Fecha de inicio de la semana (YYYY-MM-DD). 
                           Si no se proporciona, usa la semana actual (lunes).
            
        Returns:
            dict: Rankings semanales de cajas, cajeros, bartenders, barras, etc.
        """
        from datetime import datetime, timedelta
        
        # Calcular inicio y fin de semana (lunes a domingo)
        if week_start_date:
            week_start = datetime.strptime(week_start_date, '%Y-%m-%d')
        else:
            today = datetime.now()
            # Calcular el lunes de esta semana
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        week_start_str = week_start.strftime('%Y-%m-%d')
        week_end_str = week_end.strftime('%Y-%m-%d')
        
        # Obtener entregas de la semana (optimizado con consulta SQL)
        current_app.logger.info(f"📊 Obteniendo rankings semanales: {week_start_str} al {week_end_str}")
        
        # Usar consulta SQL filtrada en lugar de cargar todo
        from app.models.delivery_models import Delivery
        week_deliveries = Delivery.query.filter(
            Delivery.timestamp >= week_start,
            Delivery.timestamp <= week_end
        ).all()
        
        current_app.logger.info(f"✅ Encontradas {len(week_deliveries)} entregas en la semana")
        
        # Rankings de entregas
        bartender_counts = Counter()
        barra_counts = Counter()
        item_counts = Counter()
        categoria_counts = Counter()  # Nuevo: contador de categorías
        
        # Cache de categorías por item_name
        item_categorias_cache = {}
        
        for delivery in week_deliveries:
            bartender_counts[delivery.bartender] += delivery.qty
            barra_counts[delivery.barra] += delivery.qty
            item_counts[delivery.item_name] += delivery.qty
            
            # Obtener categoría del producto
            item_name = delivery.item_name
            if item_name not in item_categorias_cache:
                categoria = self._get_item_category(item_name)
                item_categorias_cache[item_name] = categoria
            else:
                categoria = item_categorias_cache[item_name]
            
            if categoria:
                categoria_counts[categoria] += delivery.qty
        
        # Rankings de cajas y cajeros
        top_cashiers = []
        top_registers = []
        cashier_counts_week = Counter()
        register_counts_week = Counter()
        cashier_amounts_week = defaultdict(float)
        register_amounts_week = defaultdict(float)
        cashier_names = {}
        register_names = {}
        
        try:
            # PHP POS API: aumentar límite para obtener más ventas de la semana
            # Intentar obtener más ventas usando paginación
            current_app.logger.info("📊 Obteniendo ventas desde API POS...")
            all_sales = self.pos_client.get_all_sales(limit=1000, max_results=1000, use_pagination=True)
            current_app.logger.info(f"✅ Obtenidas {len(all_sales)} ventas desde API")
            
            sales_in_week = 0
            for sale in all_sales:
                sale_time = sale.get('sale_time', '')
                if sale_time:
                    try:
                        sale_dt = datetime.strptime(sale_time[:19], '%Y-%m-%d %H:%M:%S')
                        if week_start <= sale_dt <= week_end:
                            sales_in_week += 1
                            employee_id = str(sale.get('employee_id', '')) or 'Sin cajero'
                            register_id = str(sale.get('register_id', '')) or 'Sin caja'
                            sale_total = sale.get('sale_total', 0)
                            
                            if employee_id and employee_id != 'Sin cajero':
                                cashier_counts_week[employee_id] += 1
                                cashier_amounts_week[employee_id] += sale_total
                                if employee_id not in cashier_names:
                                    employee_info = self.pos_client.get_entity_details("employees", employee_id)
                                    if employee_info:
                                        name = f"{employee_info.get('first_name', '')} {employee_info.get('last_name', '')}".strip()
                                        cashier_names[employee_id] = name or employee_info.get('name', f'Cajero {employee_id}')
                                    else:
                                        cashier_names[employee_id] = f'Cajero {employee_id}'
                            
                            if register_id and register_id != 'Sin caja':
                                register_counts_week[register_id] += 1
                                register_amounts_week[register_id] += sale_total
                                if register_id not in register_names:
                                    register_info = self.pos_client.get_entity_details("registers", register_id)
                                    if register_info:
                                        register_names[register_id] = register_info.get('name', f'Caja {register_id}')
                                    else:
                                        register_names[register_id] = f'Caja {register_id}'
                    except Exception as e:
                        current_app.logger.debug(f"Error procesando venta: {e}")
                        continue
            
            current_app.logger.info(f"✅ {sales_in_week} ventas encontradas en la semana")
            current_app.logger.info(f"✅ {len(cashier_counts_week)} cajeros únicos, {len(register_counts_week)} cajas únicas")
            
            # Top cajeros de la semana
            for employee_id, count in cashier_counts_week.most_common(20):
                top_cashiers.append({
                    'id': employee_id,
                    'name': cashier_names.get(employee_id, f'Cajero {employee_id}'),
                    'sales_count': count,
                    'total_amount': cashier_amounts_week.get(employee_id, 0)
                })
            
            # Top cajas de la semana
            for register_id, count in register_counts_week.most_common(20):
                top_registers.append({
                    'id': register_id,
                    'name': register_names.get(register_id, f'Caja {register_id}'),
                    'sales_count': count,
                    'total_amount': register_amounts_week.get(register_id, 0)
                })
        except Exception as e:
            current_app.logger.error(f"❌ Error al obtener rankings de cajas semanales: {e}", exc_info=True)
        
        # Log resumen final
        current_app.logger.info(f"📊 Rankings generados: {len(top_cashiers)} cajeros, {len(top_registers)} cajas, {len(bartender_counts)} bartenders, {len(barra_counts)} barras, {len(item_counts)} productos")
        
        return {
            'week_start': week_start_str,
            'week_end': week_end_str,
            'week_label': f"{week_start_str} al {week_end_str}",
            'top_cashiers': top_cashiers,
            'top_registers': top_registers,
            'top_bartenders': bartender_counts.most_common(20),
            'top_barras': barra_counts.most_common(10),
            'top_items': item_counts.most_common(20),
            'top_categorias': categoria_counts.most_common(15),  # Nuevo: rankings de categorías
            'total_deliveries': len(week_deliveries),
            'total_sales_cashiers': sum(cashier_counts_week.values()),
            'total_sales_registers': sum(register_counts_week.values())
        }
