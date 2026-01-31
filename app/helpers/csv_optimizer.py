"""
Utilidades para optimizar operaciones con archivos CSV
Incluye streaming, paginación y procesamiento eficiente
"""
import csv
import os
from typing import Iterator, List, Optional, Callable, Dict, Any
from functools import lru_cache
from flask import current_app
from .logger import get_logger

logger = get_logger(__name__)


class CSVStreamReader:
    """
    Lector de CSV que procesa línea por línea sin cargar todo en memoria
    Útil para archivos grandes
    """
    
    def __init__(self, file_path: str, expected_header: Optional[List[str]] = None):
        """
        Args:
            file_path: Ruta al archivo CSV
            expected_header: Header esperado (opcional, para validación)
        """
        self.file_path = file_path
        self.expected_header = expected_header
    
    def read_stream(self, max_rows: Optional[int] = None, skip_rows: int = 0) -> Iterator[List[str]]:
        """
        Lee el CSV línea por línea (generator)
        
        Args:
            max_rows: Número máximo de filas a leer (None = todas)
            skip_rows: Número de filas a saltar desde el inicio
            
        Yields:
            Lista de valores de cada fila
        """
        if not os.path.exists(self.file_path):
            return
        
        try:
            with open(self.file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                
                # Leer header
                header = next(reader, None)
                if header is None:
                    return
                
                # Validar header si se especificó
                if self.expected_header and header != self.expected_header:
                    logger.warning(f"Header no coincide en {self.file_path}")
                    return
                
                # Saltar filas si se especificó
                for _ in range(skip_rows):
                    next(reader, None)
                
                # Leer filas
                rows_read = 0
                for row in reader:
                    if max_rows and rows_read >= max_rows:
                        break
                    yield row
                    rows_read += 1
                    
        except Exception as e:
            logger.error(f"Error al leer CSV stream {self.file_path}: {e}")
    
    def count_rows(self) -> int:
        """
        Cuenta el número de filas sin cargar todo en memoria
        
        Returns:
            Número de filas (sin contar header)
        """
        count = 0
        for _ in self.read_stream():
            count += 1
        return count
    
    def filter_rows(self, filter_func: Callable[[List[str]], bool]) -> Iterator[List[str]]:
        """
        Filtra filas usando una función
        
        Args:
            filter_func: Función que retorna True para filas a incluir
            
        Yields:
            Filas que cumplen el filtro
        """
        for row in self.read_stream():
            if filter_func(row):
                yield row


class CSVPaginator:
    """
    Paginador para archivos CSV grandes
    Útil para mostrar resultados por páginas
    """
    
    def __init__(self, file_path: str, expected_header: List[str], page_size: int = 100):
        """
        Args:
            file_path: Ruta al archivo CSV
            expected_header: Header esperado
            page_size: Tamaño de página
        """
        self.file_path = file_path
        self.expected_header = expected_header
        self.page_size = page_size
    
    def get_page(self, page: int = 1, reverse: bool = False) -> Dict[str, Any]:
        """
        Obtiene una página de resultados
        
        Args:
            page: Número de página (1-indexed)
            reverse: Si True, ordena en reverso (más recientes primero)
            
        Returns:
            dict con 'items', 'page', 'total_pages', 'total_items'
        """
        reader = CSVStreamReader(self.file_path, self.expected_header)
        
        # Contar total de items
        total_items = reader.count_rows()
        total_pages = (total_items + self.page_size - 1) // self.page_size
        
        # Validar página
        if page < 1:
            page = 1
        if page > total_pages and total_pages > 0:
            page = total_pages
        
        # Calcular offset
        skip_rows = (page - 1) * self.page_size
        
        # Leer items
        items = []
        if reverse:
            # Para orden reverso, necesitamos leer todo y luego invertir
            # Para optimizar, podríamos leer desde el final (más complejo)
            all_items = list(reader.read_stream())
            all_items.reverse()
            items = all_items[skip_rows:skip_rows + self.page_size]
        else:
            items = list(reader.read_stream(max_rows=self.page_size, skip_rows=skip_rows))
        
        return {
            'items': items,
            'page': page,
            'page_size': self.page_size,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }


def optimize_csv_read(file_path: str, expected_header: List[str], use_cache: bool = True):
    """
    Lee un CSV de forma optimizada, con cache opcional
    
    Args:
        file_path: Ruta al archivo CSV
        expected_header: Header esperado
        use_cache: Si True, cachea el resultado (útil para lecturas frecuentes)
        
    Returns:
        Lista de filas
    """
    if use_cache:
        # Usar cache para evitar leer el archivo múltiples veces
        return _cached_read_csv(file_path, expected_header)
    else:
        return _read_csv_direct(file_path, expected_header)


@lru_cache(maxsize=10)
def _cached_read_csv(file_path: str, expected_header: tuple):
    """
    Lee CSV con cache LRU (últimos 10 archivos)
    
    Note: El cache usa tuple para expected_header porque lru_cache requiere
    argumentos hashables
    """
    return _read_csv_direct(file_path, list(expected_header))


def _read_csv_direct(file_path: str, expected_header: List[str]) -> List[List[str]]:
    """Lee CSV directamente sin cache"""
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            if header != expected_header:
                logger.warning(f"Header no coincide en {file_path}")
                return []
            
            return list(reader)
    except Exception as e:
        logger.error(f"Error al leer CSV {file_path}: {e}")
        return []


def append_csv_row(file_path: str, header: List[str], row: List[str], ensure_header: bool = True):
    """
    Agrega una fila al final de un CSV de forma eficiente
    
    Args:
        file_path: Ruta al archivo CSV
        header: Header del CSV
        row: Fila a agregar
        ensure_header: Si True, crea el archivo con header si no existe
    """
    # Crear archivo con header si no existe
    if ensure_header and not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
    
    # Agregar fila al final
    try:
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    except Exception as e:
        logger.error(f"Error al agregar fila a CSV {file_path}: {e}")
        raise


def get_csv_statistics(file_path: str, expected_header: List[str]) -> Dict[str, Any]:
    """
    Obtiene estadísticas de un archivo CSV sin cargar todo en memoria
    
    Returns:
        dict con 'row_count', 'file_size_bytes', 'last_modified'
    """
    if not os.path.exists(file_path):
        return {
            'row_count': 0,
            'file_size_bytes': 0,
            'last_modified': None,
            'exists': False
        }
    
    try:
        reader = CSVStreamReader(file_path, expected_header)
        row_count = reader.count_rows()
        
        stat = os.stat(file_path)
        
        return {
            'row_count': row_count,
            'file_size_bytes': stat.st_size,
            'file_size_kb': round(stat.st_size / 1024, 2),
            'last_modified': stat.st_mtime,
            'exists': True
        }
    except Exception as e:
        logger.error(f"Error al obtener estadísticas de CSV {file_path}: {e}")
        return {
            'row_count': 0,
            'file_size_bytes': 0,
            'last_modified': None,
            'exists': False,
            'error': str(e)
        }














