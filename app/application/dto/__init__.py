"""
DTOs (Data Transfer Objects)
Objetos para transferir datos entre capas.
"""
from .shift_dto import OpenShiftRequest, CloseShiftRequest
from .delivery_dto import DeliveryRequest, ScanSaleRequest
from .survey_dto import SurveyResponseRequest
from .social_media_dto import (
    SocialMediaMessage,
    SocialMediaResponse,
    GenerateResponseRequest,
    GenerateResponseResponse
)

__all__ = [
    'OpenShiftRequest',
    'CloseShiftRequest',
    'DeliveryRequest',
    'ScanSaleRequest',
    'SurveyResponseRequest',
    'SocialMediaMessage',
    'SocialMediaResponse',
    'GenerateResponseRequest',
    'GenerateResponseResponse'
]

