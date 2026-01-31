"""
Helper para gestión de impresoras por TPV
"""
import platform
import subprocess
import json
import logging
from typing import Optional, Dict, Any, List
from flask import current_app

logger = logging.getLogger(__name__)


class PrinterHelper:
    """Helper para gestionar impresoras del sistema"""
    
    @staticmethod
    def get_available_printers() -> List[str]:
        """
        Obtiene lista de impresoras disponibles en el sistema
        
        Returns:
            Lista de nombres de impresoras
        """
        try:
            system = platform.system()
            printers = []
            
            if system == "Windows":
                # Windows: usar wmic
                result = subprocess.run(
                    ['wmic', 'printer', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Saltar header
                        printer_name = line.strip()
                        if printer_name:
                            printers.append(printer_name)
            
            elif system == "Darwin":  # macOS
                # macOS: usar lpstat
                result = subprocess.run(
                    ['lpstat', '-p'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.startswith('printer'):
                            # Formato: "printer NombreImpresora is idle..."
                            parts = line.split()
                            if len(parts) > 1:
                                printer_name = parts[1]
                                printers.append(printer_name)
            
            elif system == "Linux":
                # Linux: usar lpstat
                result = subprocess.run(
                    ['lpstat', '-p', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.startswith('printer'):
                            # Formato: "printer NombreImpresora is idle..."
                            parts = line.split()
                            if len(parts) > 1:
                                printer_name = parts[1]
                                printers.append(printer_name)
            
            # Eliminar duplicados y ordenar
            printers = sorted(list(set(printers)))
            
            logger.info(f"✅ Impresoras encontradas: {len(printers)}")
            return printers
            
        except Exception as e:
            logger.error(f"Error al obtener impresoras: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_default_printer() -> Optional[str]:
        """
        Obtiene la impresora por defecto del sistema
        
        Returns:
            Nombre de la impresora por defecto o None
        """
        try:
            system = platform.system()
            
            if system == "Windows":
                result = subprocess.run(
                    ['wmic', 'printer', 'where', 'default=true', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Saltar header
                        printer_name = line.strip()
                        if printer_name:
                            return printer_name
            
            elif system == "Darwin":  # macOS
                result = subprocess.run(
                    ['lpstat', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Formato: "system default destination: NombreImpresora"
                    for line in result.stdout.split('\n'):
                        if 'system default destination:' in line:
                            parts = line.split(':', 1)
                            if len(parts) > 1:
                                return parts[1].strip()
            
            elif system == "Linux":
                result = subprocess.run(
                    ['lpstat', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Formato: "system default destination: NombreImpresora"
                    for line in result.stdout.split('\n'):
                        if 'system default destination:' in line:
                            parts = line.split(':', 1)
                            if len(parts) > 1:
                                return parts[1].strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener impresora por defecto: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_printer_config_for_register(register) -> Dict[str, Any]:
        """
        Obtiene la configuración de impresora para un TPV
        
        Args:
            register: Objeto PosRegister
            
        Returns:
            Diccionario con configuración de impresora
        """
        default_config = {
            'printer_name': None,
            'printer_type': 'thermal',
            'auto_print': True,
            'print_items': True,
            'print_total': True,
            'print_barcode': True,
            'paper_width': 80,
            'open_drawer': True,
            'cut_paper': True
        }
        
        if not register or not register.printer_config:
            # Usar impresora por defecto del sistema si no hay configuración
            default_printer = PrinterHelper.get_default_printer()
            if default_printer:
                default_config['printer_name'] = default_printer
            return default_config
        
        try:
            config = json.loads(register.printer_config)
            # Combinar con valores por defecto
            merged_config = {**default_config, **config}
            return merged_config
        except Exception as e:
            logger.error(f"Error al parsear printer_config: {e}", exc_info=True)
            return default_config
    
    @staticmethod
    def validate_printer_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Valida una configuración de impresora
        
        Args:
            config: Diccionario con configuración
            
        Returns:
            Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
        """
        # Validar printer_type
        valid_types = ['thermal', 'inkjet', 'laser', 'default']
        if 'printer_type' in config and config['printer_type'] not in valid_types:
            return False, f"printer_type debe ser uno de: {', '.join(valid_types)}"
        
        # Validar paper_width
        if 'paper_width' in config:
            try:
                width = int(config['paper_width'])
                valid_widths = [58, 80, 110, 210]  # mm
                if width not in valid_widths:
                    return False, f"paper_width debe ser uno de: {', '.join(map(str, valid_widths))} mm"
            except (ValueError, TypeError):
                return False, "paper_width debe ser un número"
        
        # Validar booleanos
        boolean_fields = ['auto_print', 'print_items', 'print_total', 'print_barcode', 'open_drawer', 'cut_paper']
        for field in boolean_fields:
            if field in config and not isinstance(config[field], bool):
                return False, f"{field} debe ser true o false"
        
        return True, None
    
    @staticmethod
    def create_printer_config(
        printer_name: Optional[str] = None,
        printer_type: str = 'thermal',
        auto_print: bool = True,
        print_items: bool = True,
        print_total: bool = True,
        print_barcode: bool = True,
        paper_width: int = 80,
        open_drawer: bool = True,
        cut_paper: bool = True
    ) -> str:
        """
        Crea una configuración de impresora en formato JSON
        
        Returns:
            String JSON con la configuración
        """
        config = {
            'printer_name': printer_name,
            'printer_type': printer_type,
            'auto_print': auto_print,
            'print_items': print_items,
            'print_total': print_total,
            'print_barcode': print_barcode,
            'paper_width': paper_width,
            'open_drawer': open_drawer,
            'cut_paper': cut_paper
        }
        
        return json.dumps(config)

