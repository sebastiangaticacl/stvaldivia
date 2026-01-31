"""
Infraestructura: Implementaciones concretas de repositorios y adaptadores externos.
"""
from .repositories.shift_repository import ShiftRepository, JsonShiftRepository
from .repositories.delivery_repository import DeliveryRepository, CsvDeliveryRepository
from .repositories.survey_repository import SurveyRepository, CsvSurveyRepository
from .external.pos_api_client import PosApiClient, PhpPosApiClient
from .events.socketio_publisher import EventPublisher, SocketIOEventPublisher, NoOpEventPublisher

__all__ = [
    'ShiftRepository',
    'JsonShiftRepository',
    'DeliveryRepository',
    'CsvDeliveryRepository',
    'SurveyRepository',
    'CsvSurveyRepository',
    'PosApiClient',
    'PhpPosApiClient',
    'EventPublisher',
    'SocketIOEventPublisher',
    'NoOpEventPublisher'
]

