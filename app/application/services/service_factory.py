"""
Factory para crear instancias de servicios con todas sus dependencias.
Centraliza la creación de servicios para evitar duplicación de código.
"""
from typing import Optional
from flask import current_app

from .shift_service import ShiftService
from .fraud_service import FraudService
from .delivery_service import DeliveryService
from .survey_service import SurveyService
from .stats_service import StatsService
from .social_media_service import SocialMediaService
from .inventory_service import InventoryService
from .guardarropia_service import GuardarropiaService

from app.infrastructure.repositories.shift_repository import JsonShiftRepository
from app.infrastructure.repositories.sql_shift_repository import SqlShiftRepository
from app.infrastructure.repositories.delivery_repository import CsvDeliveryRepository
from app.infrastructure.repositories.sql_delivery_repository import SqlDeliveryRepository
from app.infrastructure.repositories.survey_repository import CsvSurveyRepository
from app.infrastructure.repositories.sql_survey_repository import SqlSurveyRepository
from app.infrastructure.repositories.social_media_repository import CsvSocialMediaRepository
from app.infrastructure.repositories.inventory_repository import JsonInventoryRepository
from app.infrastructure.repositories.sql_inventory_repository import SqlInventoryRepository
from app.infrastructure.external.pos_api_client import PhpPosApiClient
from app.infrastructure.external.openai_client import OpenAIAPIClient
from app.infrastructure.events.socketio_publisher import SocketIOEventPublisher, NoOpEventPublisher


def get_socketio_instance():
    """Obtiene la instancia de SocketIO desde app.__init__"""
    try:
        from app import socketio
        return socketio
    except ImportError:
        return None


def create_event_publisher(socketio_instance=None) -> Optional[SocketIOEventPublisher]:
    """
    Crea un EventPublisher usando SocketIO si está disponible.
    
    Args:
        socketio_instance: Instancia de SocketIO (opcional, intentará obtenerla si no se proporciona)
        
    Returns:
        SocketIOEventPublisher o NoOpEventPublisher si no hay SocketIO
    """
    if socketio_instance is None:
        socketio_instance = get_socketio_instance()
    
    if socketio_instance:
        return SocketIOEventPublisher(socketio_instance)
    
    return NoOpEventPublisher()


def create_shift_service(
    event_publisher=None,
    shift_repository=None
) -> ShiftService:
    """
    Crea una instancia de ShiftService con sus dependencias.
    
    Returns:
        ShiftService: Instancia configurada
    """
    if event_publisher is None:
        event_publisher = create_event_publisher()
    
    if shift_repository is None:
        # Intentar usar SQL primero, fallback a JSON solo si falla
        try:
            shift_repository = SqlShiftRepository()
            try:
                current_app.logger.info("✅ SqlShiftRepository inicializado")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).info("✅ SqlShiftRepository inicializado")
        except Exception as e:
            # Fallback a JSON solo en desarrollo
            try:
                current_app.logger.warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            shift_repository = JsonShiftRepository()
    
    return ShiftService(
        shift_repository=shift_repository,
        event_publisher=event_publisher
    )


def create_fraud_service(
    delivery_repository=None,
    max_hours_old_ticket: int = 24,
    max_delivery_attempts: int = 3
) -> FraudService:
    """
    Crea una instancia de FraudService con sus dependencias.
    
    Returns:
        FraudService: Instancia configurada
    """
    if delivery_repository is None:
        # Usar SQL repository por defecto para mejor rendimiento
        try:
            delivery_repository = SqlDeliveryRepository()
        except:
            delivery_repository = CsvDeliveryRepository()
    
    # Cargar configuración de antifraude si existe
    try:
        from app.helpers.fraud_config import load_fraud_config
        config = load_fraud_config()
        max_hours_old_ticket = config.get('max_hours_old_ticket', max_hours_old_ticket)
        max_delivery_attempts = config.get('max_delivery_attempts', max_delivery_attempts)
    except:
        pass
    
    return FraudService(
        delivery_repository=delivery_repository,
        max_hours_old_ticket=max_hours_old_ticket,
        max_delivery_attempts=max_delivery_attempts
    )


def create_delivery_service(
    event_publisher=None,
    delivery_repository=None,
    shift_repository=None,
    pos_client=None,
    fraud_service=None,
    shift_service=None
) -> DeliveryService:
    """
    Crea una instancia de DeliveryService con todas sus dependencias.
    
    Returns:
        DeliveryService: Instancia configurada
    """
    if event_publisher is None:
        event_publisher = create_event_publisher()
    
    if delivery_repository is None:
        # Usar SQL repository por defecto para mejor rendimiento
        try:
            delivery_repository = SqlDeliveryRepository()
        except:
            delivery_repository = CsvDeliveryRepository()
    
    if shift_repository is None:
        # Intentar usar SQL primero, fallback a JSON solo si falla
        try:
            shift_repository = SqlShiftRepository()
            try:
                current_app.logger.info("✅ SqlShiftRepository inicializado")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).info("✅ SqlShiftRepository inicializado")
        except Exception as e:
            # Fallback a JSON solo en desarrollo
            try:
                current_app.logger.warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            shift_repository = JsonShiftRepository()
    
    if pos_client is None:
        pos_client = PhpPosApiClient()
    
    if fraud_service is None:
        fraud_service = create_fraud_service(delivery_repository=delivery_repository)
    
    if shift_service is None:
        shift_service = create_shift_service(
            event_publisher=event_publisher,
            shift_repository=shift_repository
        )
    
    return DeliveryService(
        delivery_repository=delivery_repository,
        shift_repository=shift_repository,
        pos_client=pos_client,
        fraud_service=fraud_service,
        shift_service=shift_service,
        event_publisher=event_publisher
    )


def create_survey_service(
    event_publisher=None,
    survey_repository=None,
    shift_repository=None,
    shift_service=None
) -> SurveyService:
    """
    Crea una instancia de SurveyService con sus dependencias.
    
    Returns:
        SurveyService: Instancia configurada
    """
    if event_publisher is None:
        event_publisher = create_event_publisher()
    
    if survey_repository is None:
        # Intentar usar SQL primero, fallback a CSV solo si falla
        try:
            survey_repository = SqlSurveyRepository()
            try:
                current_app.logger.info("✅ SqlSurveyRepository inicializado")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).info("✅ SqlSurveyRepository inicializado")
        except Exception as e:
            # Fallback a CSV solo en desarrollo
            try:
                current_app.logger.warning(f"⚠️ No se pudo inicializar SqlSurveyRepository, usando CsvSurveyRepository: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ No se pudo inicializar SqlSurveyRepository, usando CsvSurveyRepository: {e}")
            survey_repository = CsvSurveyRepository()
    
    if shift_repository is None:
        # Intentar usar SQL primero, fallback a JSON solo si falla
        try:
            shift_repository = SqlShiftRepository()
            try:
                current_app.logger.info("✅ SqlShiftRepository inicializado")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).info("✅ SqlShiftRepository inicializado")
        except Exception as e:
            # Fallback a JSON solo en desarrollo
            try:
                current_app.logger.warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            shift_repository = JsonShiftRepository()
    
    if shift_service is None:
        shift_service = create_shift_service(
            event_publisher=event_publisher,
            shift_repository=shift_repository
        )
    
    return SurveyService(
        survey_repository=survey_repository,
        shift_repository=shift_repository,
        shift_service=shift_service,
        event_publisher=event_publisher
    )


def create_stats_service(
    delivery_repository=None,
    shift_repository=None,
    survey_repository=None,
    pos_client=None
) -> StatsService:
    """
    Crea una instancia de StatsService con sus dependencias.
    
    Returns:
        StatsService: Instancia configurada
    """
    if delivery_repository is None:
        # Usar SQL repository por defecto para mejor rendimiento
        try:
            delivery_repository = SqlDeliveryRepository()
        except:
            delivery_repository = CsvDeliveryRepository()
    
    if shift_repository is None:
        # Intentar usar SQL primero, fallback a JSON solo si falla
        try:
            shift_repository = SqlShiftRepository()
            try:
                current_app.logger.info("✅ SqlShiftRepository inicializado")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).info("✅ SqlShiftRepository inicializado")
        except Exception as e:
            # Fallback a JSON solo en desarrollo
            try:
                current_app.logger.warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            shift_repository = JsonShiftRepository()
    
    if survey_repository is None:
        # Intentar usar SQL primero, fallback a CSV solo si falla
        try:
            survey_repository = SqlSurveyRepository()
            try:
                current_app.logger.info("✅ SqlSurveyRepository inicializado")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).info("✅ SqlSurveyRepository inicializado")
        except Exception as e:
            # Fallback a CSV solo en desarrollo
            try:
                current_app.logger.warning(f"⚠️ No se pudo inicializar SqlSurveyRepository, usando CsvSurveyRepository: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ No se pudo inicializar SqlSurveyRepository, usando CsvSurveyRepository: {e}")
            survey_repository = CsvSurveyRepository()
    
    if pos_client is None:
        pos_client = PhpPosApiClient()
    
    return StatsService(
        delivery_repository=delivery_repository,
        shift_repository=shift_repository,
        survey_repository=survey_repository,
        pos_client=pos_client
    )


# Funciones de conveniencia para uso en rutas
def get_shift_service() -> ShiftService:
    """Obtiene una instancia de ShiftService (singleton pattern opcional)"""
    return create_shift_service()


def get_fraud_service() -> FraudService:
    """Obtiene una instancia de FraudService"""
    return create_fraud_service()


def get_delivery_service() -> DeliveryService:
    """Obtiene una instancia de DeliveryService"""
    return create_delivery_service()


def get_survey_service() -> SurveyService:
    """Obtiene una instancia de SurveyService"""
    return create_survey_service()


def get_stats_service() -> StatsService:
    """Obtiene una instancia de StatsService"""
    return create_stats_service()


def create_social_media_service(
    openai_client=None,
    repository=None,
    default_model: str = "gpt-4o-mini",
    default_temperature: float = 0.7
) -> SocialMediaService:
    """
    Crea una instancia de SocialMediaService con sus dependencias.
    
    Returns:
        SocialMediaService: Instancia configurada
    """
    if openai_client is None:
        # Obtener API key de config si está disponible
        try:
            from flask import current_app
            api_key = current_app.config.get('OPENAI_API_KEY')
            organization = current_app.config.get('OPENAI_ORGANIZATION_ID')
            project = current_app.config.get('OPENAI_PROJECT_ID')
            openai_client = OpenAIAPIClient(api_key=api_key, organization=organization, project=project)
        except RuntimeError:
            # Si no hay contexto de Flask, crear sin configuración
            import os
            api_key = os.environ.get('OPENAI_API_KEY')
            organization = os.environ.get('OPENAI_ORGANIZATION_ID')
            project = os.environ.get('OPENAI_PROJECT_ID')
            openai_client = OpenAIAPIClient(api_key=api_key, organization=organization, project=project)
    
    if repository is None:
        repository = CsvSocialMediaRepository()
    
    return SocialMediaService(
        openai_client=openai_client,
        repository=repository,
        default_model=default_model,
        default_temperature=default_temperature
    )


def get_social_media_service() -> SocialMediaService:
    """Obtiene una instancia de SocialMediaService"""
    return create_social_media_service()


def create_inventory_service(
    inventory_repository=None,
    shift_repository=None
) -> InventoryService:
    """
    Crea una instancia de InventoryService con sus dependencias.
    
    Returns:
        InventoryService: Instancia configurada
    """
    if inventory_repository is None:
        import os
        from flask import current_app
        
        # Detectar si estamos en Cloud Run
        is_cloud_run = bool(
            os.environ.get('K_SERVICE') or 
            os.environ.get('GAE_ENV') or 
            os.environ.get('CLOUD_RUN_SERVICE')
        )
        
        # En Cloud Run, SIEMPRE usar SQL (JSON no funciona con sistema de archivos efímero)
        if is_cloud_run:
            try:
                inventory_repository = SqlInventoryRepository()
                try:
                    current_app.logger.info("✅ SqlInventoryRepository inicializado correctamente en Cloud Run")
                except RuntimeError:
                    # Si no hay contexto de Flask, usar logging estándar
                    import logging
                    logging.getLogger(__name__).info("✅ SqlInventoryRepository inicializado correctamente en Cloud Run")
            except Exception as e:
                # En Cloud Run, NO hacer fallback a JSON - fallar explícitamente
                error_msg = f"❌ Error crítico: No se pudo inicializar SqlInventoryRepository en Cloud Run: {e}"
                try:
                    current_app.logger.error(error_msg, exc_info=True)
                except RuntimeError:
                    import logging
                    logging.getLogger(__name__).error(error_msg, exc_info=True)
                raise RuntimeError(
                    "No se pudo inicializar el repositorio de inventario SQL. "
                    "Verifica la conexión a la base de datos y que la tabla 'inventory_items' exista."
                ) from e
        else:
            # En desarrollo local, intentar SQL primero, luego JSON como fallback
            try:
                inventory_repository = SqlInventoryRepository()
                try:
                    current_app.logger.info("✅ SqlInventoryRepository inicializado (desarrollo local)")
                except RuntimeError:
                    import logging
                    logging.getLogger(__name__).info("✅ SqlInventoryRepository inicializado (desarrollo local)")
            except Exception as e:
                # En desarrollo, permitir fallback a JSON
                try:
                    current_app.logger.warning(
                        f"⚠️ No se pudo inicializar SqlInventoryRepository, usando JsonInventoryRepository: {e}"
                    )
                except RuntimeError:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"⚠️ No se pudo inicializar SqlInventoryRepository, usando JsonInventoryRepository: {e}"
                    )
                inventory_repository = JsonInventoryRepository()
    
    if shift_repository is None:
        # Intentar usar SQL primero, fallback a JSON solo si falla
        try:
            shift_repository = SqlShiftRepository()
            try:
                current_app.logger.info("✅ SqlShiftRepository inicializado")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).info("✅ SqlShiftRepository inicializado")
        except Exception as e:
            # Fallback a JSON solo en desarrollo
            try:
                current_app.logger.warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            shift_repository = JsonShiftRepository()
    
    return InventoryService(
        inventory_repository=inventory_repository,
        shift_repository=shift_repository
    )


def get_inventory_service() -> InventoryService:
    """Obtiene una instancia de InventoryService"""
    return create_inventory_service()


def create_guardarropia_service(
    repository=None,
    shift_repository=None
) -> GuardarropiaService:
    """
    Crea una instancia de GuardarropiaService con sus dependencias.
    
    Returns:
        GuardarropiaService: Instancia configurada
    """
    if repository is None:
        from app.infrastructure.repositories.sql_guardarropia_repository import SqlGuardarropiaRepository
        repository = SqlGuardarropiaRepository()
    
    if shift_repository is None:
        # Intentar usar SQL primero, fallback a JSON solo si falla
        try:
            shift_repository = SqlShiftRepository()
            try:
                current_app.logger.info("✅ SqlShiftRepository inicializado")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).info("✅ SqlShiftRepository inicializado")
        except Exception as e:
            # Fallback a JSON solo en desarrollo
            try:
                current_app.logger.warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ No se pudo inicializar SqlShiftRepository, usando JsonShiftRepository: {e}")
            shift_repository = JsonShiftRepository()
    
    return GuardarropiaService(
        repository=repository,
        shift_repository=shift_repository
    )


def get_guardarropia_service() -> GuardarropiaService:
    """Obtiene una instancia de GuardarropiaService"""
    return create_guardarropia_service()

