"""
Repositorio de Conversaciones de Redes Sociales
Interfaz e implementación CSV.
"""
from abc import ABC, abstractmethod
import os
import csv
import json
from typing import List, Optional, Dict
from datetime import datetime
from flask import current_app

from app.application.dto.social_media_dto import SocialMediaMessage, SocialMediaResponse


class SocialMediaRepository(ABC):
    """Interfaz del repositorio de redes sociales"""
    
    @abstractmethod
    def save_message(self, message: SocialMediaMessage) -> bool:
        """Guarda un mensaje recibido"""
        pass
    
    @abstractmethod
    def save_response(self, response: SocialMediaResponse) -> bool:
        """Guarda una respuesta generada"""
        pass
    
    @abstractmethod
    def get_conversation_history(
        self,
        platform: str,
        sender: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Obtiene el historial de conversación formateado para OpenAI.
        Retorna lista de mensajes en formato [{"role": "user", "content": "..."}, ...]
        """
        pass
    
    @abstractmethod
    def find_messages_by_platform(
        self,
        platform: str,
        limit: int = 50
    ) -> List[SocialMediaMessage]:
        """Obtiene mensajes por plataforma"""
        pass


class CsvSocialMediaRepository(SocialMediaRepository):
    """
    Implementación del repositorio usando archivos CSV.
    Almacena mensajes y respuestas en archivos separados.
    """
    
    MESSAGES_FILE = 'social_media_messages.csv'
    RESPONSES_FILE = 'social_media_responses.csv'
    
    MESSAGE_HEADER = [
        'message_id',
        'platform',
        'sender',
        'content',
        'timestamp',
        'metadata'
    ]
    
    RESPONSE_HEADER = [
        'message_id',
        'response_text',
        'timestamp',
        'model_used',
        'tokens_used',
        'metadata'
    ]
    
    def _get_messages_file_path(self) -> str:
        """Obtiene la ruta del archivo de mensajes"""
        from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
        ensure_not_production("El sistema de mensajes de redes sociales desde archivo")
        instance_path = get_safe_instance_path()
        if not instance_path:
            instance_path = os.path.join(os.getcwd(), 'instance')
        
        os.makedirs(instance_path, exist_ok=True)
        return os.path.join(instance_path, self.MESSAGES_FILE)
    
    def _get_responses_file_path(self) -> str:
        """Obtiene la ruta del archivo de respuestas"""
        from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
        ensure_not_production("El sistema de respuestas de redes sociales desde archivo")
        instance_path = get_safe_instance_path()
        if not instance_path:
            instance_path = os.path.join(os.getcwd(), 'instance')
        
        os.makedirs(instance_path, exist_ok=True)
        return os.path.join(instance_path, self.RESPONSES_FILE)
    
    def _ensure_file_exists(self, file_path: str, header: List[str]):
        """Asegura que el archivo existe con el header correcto"""
        if not os.path.exists(file_path):
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
    
    def save_message(self, message: SocialMediaMessage) -> bool:
        """Guarda un mensaje recibido"""
        try:
            file_path = self._get_messages_file_path()
            self._ensure_file_exists(file_path, self.MESSAGE_HEADER)
            
            metadata_json = json.dumps(message.metadata) if message.metadata else ''
            
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    message.message_id,
                    message.platform,
                    message.sender or '',
                    message.content,
                    message.timestamp.isoformat(),
                    metadata_json
                ])
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error al guardar mensaje: {e}")
            return False
    
    def save_response(self, response: SocialMediaResponse) -> bool:
        """Guarda una respuesta generada"""
        try:
            file_path = self._get_responses_file_path()
            self._ensure_file_exists(file_path, self.RESPONSE_HEADER)
            
            metadata_json = json.dumps(response.metadata) if response.metadata else ''
            
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    response.message_id,
                    response.response_text,
                    response.timestamp.isoformat(),
                    response.model_used,
                    response.tokens_used or '',
                    metadata_json
                ])
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error al guardar respuesta: {e}")
            return False
    
    def get_conversation_history(
        self,
        platform: str,
        sender: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Obtiene el historial de conversación formateado para OpenAI.
        Retorna lista de mensajes en formato [{"role": "user", "content": "..."}, ...]
        """
        try:
            messages_file = self._get_messages_file_path()
            responses_file = self._get_responses_file_path()
            
            if not os.path.exists(messages_file):
                return []
            
            # Leer todos los mensajes relevantes
            messages = []
            message_ids = set()
            
            if os.path.exists(messages_file):
                with open(messages_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['platform'] == platform:
                            if sender is None or row.get('sender') == sender:
                                try:
                                    timestamp = datetime.fromisoformat(row['timestamp'])
                                    message_id = row['message_id']
                                    messages.append({
                                        'type': 'message',
                                        'message_id': message_id,
                                        'content': row['content'],
                                        'timestamp': timestamp,
                                        'sender': row.get('sender', '')
                                    })
                                    message_ids.add(message_id)
                                except Exception as e:
                                    current_app.logger.warning(f"Error al parsear mensaje: {e}")
                                    continue
            
            # Leer respuestas relacionadas con los mensajes encontrados
            responses = []
            if os.path.exists(responses_file) and message_ids:
                with open(responses_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Relacionar respuesta con mensaje por message_id
                        response_message_id = row.get('message_id', '')
                        if response_message_id in message_ids:
                            try:
                                timestamp = datetime.fromisoformat(row['timestamp'])
                                responses.append({
                                    'type': 'response',
                                    'message_id': response_message_id,
                                    'content': row['response_text'],
                                    'timestamp': timestamp
                                })
                            except Exception as e:
                                current_app.logger.warning(f"Error al parsear respuesta: {e}")
                                continue
            
            # Combinar mensajes y respuestas y ordenar por timestamp
            all_items = messages + responses
            all_items.sort(key=lambda x: x['timestamp'])
            
            # Formatear para OpenAI (solo últimos 'limit' items)
            formatted = []
            for item in all_items[-limit:]:
                if item['type'] == 'message':
                    formatted.append({
                        "role": "user",
                        "content": item['content']
                    })
                elif item['type'] == 'response':
                    formatted.append({
                        "role": "assistant",
                        "content": item['content']
                    })
            
            return formatted
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener historial: {e}")
            return []
    
    def find_messages_by_platform(
        self,
        platform: str,
        limit: int = 50
    ) -> List[SocialMediaMessage]:
        """Obtiene mensajes por plataforma"""
        try:
            file_path = self._get_messages_file_path()
            if not os.path.exists(file_path):
                return []
            
            messages = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['platform'] == platform:
                        try:
                            metadata = None
                            if row.get('metadata'):
                                metadata = json.loads(row['metadata'])
                            
                            message = SocialMediaMessage(
                                message_id=row['message_id'],
                                platform=row['platform'],
                                sender=row.get('sender', ''),
                                content=row['content'],
                                timestamp=datetime.fromisoformat(row['timestamp']),
                                metadata=metadata
                            )
                            messages.append(message)
                            
                            if len(messages) >= limit:
                                break
                        except Exception as e:
                            current_app.logger.warning(f"Error al parsear mensaje: {e}")
                            continue
            
            return messages
            
        except Exception as e:
            current_app.logger.error(f"Error al buscar mensajes: {e}")
            return []

