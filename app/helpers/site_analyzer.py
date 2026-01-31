"""
Cerebro que analiza el sitio web para extraer conocimiento
sobre el negocio, productos, servicios, horarios, etc.
"""
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

logger = logging.getLogger(__name__)


class SiteAnalyzer:
    """
    Analiza el sitio web para extraer conocimiento estructurado
    sobre el negocio, productos, servicios, horarios, etc.
    """
    
    def __init__(self, base_url: str = "https://stvaldivia.cl"):
        self.base_url = base_url
        self.knowledge_base: Dict = {}
        self.last_analysis: Optional[datetime] = None
        
    def analyze_site(self, force_refresh: bool = False) -> Dict:
        """
        Analiza el sitio web completo y extrae conocimiento estructurado
        
        Returns:
            Dict con el conocimiento extraído
        """
        # Si ya analizamos recientemente y no se fuerza refresh, retornar cache
        if not force_refresh and self.knowledge_base and self.last_analysis:
            hours_since = (datetime.now() - self.last_analysis).total_seconds() / 3600
            if hours_since < 24:  # Cache de 24 horas
                logger.info("Usando conocimiento en cache")
                return self.knowledge_base
        
        logger.info(f"Iniciando análisis del sitio: {self.base_url}")
        
        knowledge = {
            'business_info': {},
            'products': [],
            'services': [],
            'schedules': {},
            'contact_info': {},
            'social_media': {},
            'events': [],
            'prices': {},
            'faq': [],
            'extracted_text': []
        }
        
        try:
            # Analizar página principal
            main_page = self._fetch_page(self.base_url)
            if main_page:
                knowledge['business_info'] = self._extract_business_info(main_page)
                knowledge['contact_info'] = self._extract_contact_info(main_page)
                knowledge['social_media'] = self._extract_social_media(main_page)
                knowledge['extracted_text'].append(self._extract_main_text(main_page))
            
            # Analizar otras páginas importantes
            important_pages = [
                '/',
                '/menu',
                '/eventos',
                '/contacto',
                '/nosotros',
                '/horarios'
            ]
            
            for page_path in important_pages:
                try:
                    page = self._fetch_page(urljoin(self.base_url, page_path))
                    if page:
                        if 'menu' in page_path or 'productos' in page_path:
                            knowledge['products'].extend(self._extract_products(page))
                        if 'eventos' in page_path:
                            knowledge['events'].extend(self._extract_events(page))
                        if 'horarios' in page_path or 'horario' in page_path:
                            knowledge['schedules'].update(self._extract_schedules(page))
                        knowledge['extracted_text'].append(self._extract_main_text(page))
                except Exception as e:
                    logger.warning(f"Error analizando {page_path}: {e}")
            
            # Extraer FAQ de todo el contenido
            knowledge['faq'] = self._extract_faq(knowledge['extracted_text'])
            
            self.knowledge_base = knowledge
            self.last_analysis = datetime.now()
            
            logger.info(f"Análisis completado. Extraído: {len(knowledge['products'])} productos, "
                       f"{len(knowledge['events'])} eventos, {len(knowledge['faq'])} FAQs")
            
            return knowledge
            
        except Exception as e:
            logger.error(f"Error en análisis del sitio: {e}", exc_info=True)
            return self.knowledge_base or knowledge
    
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Obtiene y parsea una página HTML"""
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; SiteAnalyzer/1.0)'
            })
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.warning(f"Error obteniendo {url}: {e}")
            return None
    
    def _extract_business_info(self, soup: BeautifulSoup) -> Dict:
        """Extrae información general del negocio"""
        info = {}
        
        # Nombre del negocio
        title = soup.find('title')
        if title:
            info['name'] = title.get_text().strip()
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            info['description'] = meta_desc.get('content', '').strip()
        
        # Buscar información en el contenido
        text = soup.get_text()
        
        # Horarios (patrones comunes)
        schedule_patterns = [
            r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})',
            r'(lunes|martes|miércoles|jueves|viernes|sábado|domingo)[:\s]+(\d{1,2}):(\d{2})',
        ]
        
        # Dirección
        address_patterns = [
            r'([A-Za-z\s]+)\s+\d+[,\s]+[A-Za-z\s]+',
            r'Dirección[:\s]+([^\n]+)',
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['address'] = match.group(1).strip()
                break
        
        return info
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict:
        """Extrae información de contacto"""
        contact = {}
        text = soup.get_text()
        
        # Teléfono
        phone_patterns = [
            r'(\+?56\s?)?(\d{1,2})\s?(\d{4})\s?(\d{4})',
            r'(\d{2})\s?(\d{4})\s?(\d{4})',
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                contact['phone'] = ''.join(match.groups())
                break
        
        # Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            contact['email'] = email_match.group(0)
        
        # WhatsApp (si está mencionado)
        whatsapp_match = re.search(r'whatsapp[:\s]+(\+?56\s?\d+)', text, re.IGNORECASE)
        if whatsapp_match:
            contact['whatsapp'] = whatsapp_match.group(1).strip()
        
        return contact
    
    def _extract_social_media(self, soup: BeautifulSoup) -> Dict:
        """Extrae enlaces a redes sociales"""
        social = {}
        
        # Buscar enlaces a redes sociales
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text().strip().lower()
            
            if 'instagram' in href or 'instagram' in text:
                social['instagram'] = href
            elif 'facebook' in href or 'facebook' in text:
                social['facebook'] = href
            elif 'twitter' in href or 'twitter' in text:
                social['twitter'] = href
            elif 'tiktok' in href or 'tiktok' in text:
                social['tiktok'] = href
        
        return social
    
    def _extract_products(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrae información de productos"""
        products = []
        
        # Buscar elementos que parezcan productos (listas, cards, etc.)
        # Esto es heurístico y puede necesitar ajustes según la estructura del sitio
        product_elements = soup.find_all(['div', 'li', 'article'], class_=re.compile(r'product|item|menu', re.I))
        
        for elem in product_elements[:20]:  # Limitar a 20 productos
            name = elem.find(['h1', 'h2', 'h3', 'h4', 'span', 'p'], class_=re.compile(r'name|title', re.I))
            price = elem.find(['span', 'div', 'p'], class_=re.compile(r'price|precio', re.I))
            description = elem.find(['p', 'div'], class_=re.compile(r'desc|description', re.I))
            
            if name:
                product = {
                    'name': name.get_text().strip(),
                    'price': price.get_text().strip() if price else None,
                    'description': description.get_text().strip() if description else None
                }
                products.append(product)
        
        return products
    
    def _extract_events(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrae información de eventos"""
        events = []
        
        # Buscar elementos de eventos
        event_elements = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'event|evento', re.I))
        
        for elem in event_elements[:10]:  # Limitar a 10 eventos
            title = elem.find(['h1', 'h2', 'h3', 'h4'])
            date = elem.find(['time', 'span', 'div'], class_=re.compile(r'date|fecha', re.I))
            description = elem.find(['p', 'div'], class_=re.compile(r'desc|description', re.I))
            
            if title:
                event = {
                    'title': title.get_text().strip(),
                    'date': date.get_text().strip() if date else None,
                    'description': description.get_text().strip() if description else None
                }
                events.append(event)
        
        return events
    
    def _extract_schedules(self, soup: BeautifulSoup) -> Dict:
        """Extrae horarios"""
        schedules = {}
        text = soup.get_text()
        
        # Patrones para horarios
        days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        
        for day in days:
            pattern = rf'{day}[:\s]+(\d{{1,2}}):(\d{{2}})\s*-\s*(\d{{1,2}}):(\d{{2}})'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                schedules[day] = f"{match.group(1)}:{match.group(2)} - {match.group(3)}:{match.group(4)}"
        
        return schedules
    
    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        """Extrae el texto principal de la página"""
        # Remover scripts y estilos
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        text = soup.get_text()
        # Limpiar espacios múltiples
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text[:5000]  # Limitar a 5000 caracteres
    
    def _extract_faq(self, texts: List[str]) -> List[Dict]:
        """Extrae preguntas frecuentes del contenido"""
        faq = []
        
        # Buscar patrones de pregunta-respuesta
        combined_text = ' '.join(texts)
        
        # Patrones comunes de FAQ
        qa_patterns = [
            r'([¿?]\s*[^?]+\?)\s+([^¿]+?)(?=[¿?]|$)',
            r'(Pregunta[:\s]+[^:]+)\s+(Respuesta[:\s]+[^\n]+)',
        ]
        
        for pattern in qa_patterns:
            matches = re.finditer(pattern, combined_text, re.IGNORECASE | re.DOTALL)
            for match in matches[:10]:  # Limitar a 10 FAQs
                if len(match.groups()) >= 2:
                    faq.append({
                        'question': match.group(1).strip(),
                        'answer': match.group(2).strip()[:200]  # Limitar respuesta
                    })
        
        return faq
    
    def get_knowledge_summary(self) -> str:
        """
        Genera un resumen del conocimiento extraído para usar en prompts de IA
        """
        if not self.knowledge_base:
            self.analyze_site()
        
        kb = self.knowledge_base
        summary_parts = []
        
        # Información del negocio
        if kb.get('business_info'):
            info = kb['business_info']
            summary_parts.append(f"Negocio: {info.get('name', 'N/A')}")
            if info.get('description'):
                summary_parts.append(f"Descripción: {info.get('description')}")
        
        # Contacto
        if kb.get('contact_info'):
            contact = kb['contact_info']
            if contact.get('phone'):
                summary_parts.append(f"Teléfono: {contact['phone']}")
            if contact.get('email'):
                summary_parts.append(f"Email: {contact['email']}")
            if contact.get('whatsapp'):
                summary_parts.append(f"WhatsApp: {contact['whatsapp']}")
        
        # Horarios
        if kb.get('schedules'):
            schedules = kb['schedules']
            summary_parts.append(f"Horarios: {', '.join([f'{k}: {v}' for k, v in schedules.items()])}")
        
        # Productos principales
        if kb.get('products'):
            products = kb['products'][:5]  # Top 5
            product_names = [p['name'] for p in products if p.get('name')]
            if product_names:
                summary_parts.append(f"Productos principales: {', '.join(product_names)}")
        
        # Eventos próximos
        if kb.get('events'):
            events = kb['events'][:3]  # Top 3
            event_titles = [e['title'] for e in events if e.get('title')]
            if event_titles:
                summary_parts.append(f"Eventos: {', '.join(event_titles)}")
        
        return '\n'.join(summary_parts)
    
    def get_context_for_query(self, query: str) -> str:
        """
        Obtiene contexto relevante del conocimiento base para una consulta específica
        """
        if not self.knowledge_base:
            self.analyze_site()
        
        kb = self.knowledge_base
        context_parts = []
        
        query_lower = query.lower()
        
        # Si pregunta por horarios
        if any(word in query_lower for word in ['horario', 'hora', 'abierto', 'cierra', 'abre']):
            if kb.get('schedules'):
                context_parts.append(f"Horarios: {kb['schedules']}")
        
        # Si pregunta por productos
        if any(word in query_lower for word in ['producto', 'menu', 'comida', 'bebida', 'cerveza']):
            if kb.get('products'):
                products = kb['products'][:10]
                context_parts.append(f"Productos disponibles: {[p['name'] for p in products if p.get('name')]}")
        
        # Si pregunta por eventos
        if any(word in query_lower for word in ['evento', 'show', 'concierto', 'actividad']):
            if kb.get('events'):
                events = kb['events'][:5]
                context_parts.append(f"Eventos: {[e['title'] for e in events if e.get('title')]}")
        
        # Si pregunta por contacto
        if any(word in query_lower for word in ['contacto', 'teléfono', 'email', 'dirección', 'ubicación']):
            if kb.get('contact_info'):
                context_parts.append(f"Información de contacto: {kb['contact_info']}")
        
        # Si no hay contexto específico, usar resumen general
        if not context_parts:
            context_parts.append(self.get_knowledge_summary())
        
        return '\n'.join(context_parts)

