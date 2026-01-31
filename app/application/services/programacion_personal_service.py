"""
Servicio para gestión de programación de personal (asignaciones masivas)
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from flask import current_app
import csv
import io
import re

from app.models import db
from app.models.programacion_models import ProgramacionAsignacion
from app.models.cargo_models import Cargo
from app.models.pos_models import Employee


class ProgramacionPersonalService:
    """
    Servicio para gestión de asignaciones de personal por turno.
    Maneja importación masiva desde tablas (tab-separated o CSV).
    """
    
    def __init__(self):
        """Inicializa el servicio"""
        pass
    
    def parse_tabla_texto(self, texto: str) -> List[Dict[str, Any]]:
        """
        Parsea texto copiado de tabla (tab-separated o CSV).
        
        Formato esperado:
        SERVICIO | VIERNES 12 | SABADO 13
        BARRA    | Zafiro/Niko/Ignacio | Javi/Fefy/Niko
        CAJA 1   | David | 
        
        Args:
            texto: Texto copiado de Sheets/Excel
            
        Returns:
            Lista de dicts con estructura: [{'cargo': 'BARRA', 'viernes': 'Zafiro/Niko/Ignacio', 'sabado': 'Javi/Fefy/Niko'}, ...]
        """
        lineas = []
        
        # Intentar detectar si es CSV o tab-separated
        # Si tiene comas y no muchos tabs, probablemente es CSV
        tiene_comas = ',' in texto
        tiene_tabs = '\t' in texto
        
        if tiene_tabs and not tiene_comas:
            # Tab-separated
            delimiter = '\t'
        elif tiene_comas:
            # CSV
            delimiter = ','
        else:
            # Por defecto, intentar tab
            delimiter = '\t'
        
        # Parsear línea por línea
        for linea in texto.strip().split('\n'):
            linea = linea.strip()
            if not linea:
                continue
            
            # Saltar encabezados comunes
            if linea.upper().startswith('SERVICIO') or linea.upper().startswith('CARGO'):
                continue
            
            # Dividir por delimitador
            partes = [p.strip() for p in linea.split(delimiter)]
            
            if len(partes) < 2:
                continue
            
            cargo = partes[0].strip()
            if not cargo:
                continue
            
            # Obtener valores de viernes y sábado (pueden estar en diferentes posiciones)
            viernes = partes[1] if len(partes) > 1 else ''
            sabado = partes[2] if len(partes) > 2 else ''
            
            lineas.append({
                'cargo': cargo,
                'viernes': viernes,
                'sabado': sabado
            })
        
        return lineas
    
    def parse_nombres_trabajadores(self, texto: str) -> List[str]:
        """
        Parsea una celda que puede contener múltiples nombres separados por / o ,
        
        Ejemplos:
        - "Zafiro/Niko/Ignacio" -> ["Zafiro", "Niko", "Ignacio"]
        - "David, Juan" -> ["David", "Juan"]
        - "Javi" -> ["Javi"]
        
        Args:
            texto: Texto con nombres separados
            
        Returns:
            Lista de nombres normalizados
        """
        if not texto or not texto.strip():
            return []
        
        # Dividir por / o ,
        nombres = re.split(r'[/,]', texto)
        
        # Limpiar y normalizar
        nombres_limpios = []
        for nombre in nombres:
            nombre = nombre.strip()
            if nombre:
                nombres_limpios.append(nombre)
        
        return nombres_limpios
    
    def buscar_trabajador_por_nombre(self, nombre: str) -> Optional[Employee]:
        """
        Busca un trabajador por nombre (búsqueda flexible).
        
        Args:
            nombre: Nombre del trabajador (puede ser parcial)
            
        Returns:
            Employee o None
        """
        if not nombre:
            return None
        
        nombre_clean = nombre.strip().upper()
        
        # Buscar coincidencia exacta (case-insensitive)
        trabajador = Employee.query.filter(
            db.func.upper(Employee.name) == nombre_clean
        ).first()
        
        if trabajador:
            return trabajador
        
        # Buscar coincidencia parcial (contiene)
        trabajador = Employee.query.filter(
            db.func.upper(Employee.name).contains(nombre_clean)
        ).first()
        
        if trabajador:
            return trabajador
        
        # Buscar por first_name o last_name
        trabajador = Employee.query.filter(
            db.or_(
                db.func.upper(Employee.first_name).contains(nombre_clean),
                db.func.upper(Employee.last_name).contains(nombre_clean)
            )
        ).first()
        
        return trabajador
    
    def buscar_cargo_por_nombre(self, nombre: str) -> Optional[Cargo]:
        """
        Busca un cargo por nombre (búsqueda flexible).
        
        Args:
            nombre: Nombre del cargo
            
        Returns:
            Cargo o None
        """
        if not nombre:
            return None
        
        nombre_clean = nombre.strip().upper()
        
        # Buscar coincidencia exacta
        cargo = Cargo.query.filter(
            db.func.upper(Cargo.nombre) == nombre_clean
        ).first()
        
        if cargo:
            return cargo
        
        # Buscar coincidencia parcial
        cargo = Cargo.query.filter(
            db.func.upper(Cargo.nombre).contains(nombre_clean)
        ).first()
        
        return cargo
    
    def previsualizar_importacion(
        self,
        texto: str,
        fecha_viernes: date,
        fecha_sabado: date,
        tipo_turno: str
    ) -> Dict[str, Any]:
        """
        Previsualiza la importación sin guardar.
        
        Args:
            texto: Texto copiado de tabla
            fecha_viernes: Fecha del viernes
            fecha_sabado: Fecha del sábado
            tipo_turno: 'NOCHE' o 'DIA'
            
        Returns:
            Dict con resumen de lo que se importaría
        """
        lineas = self.parse_tabla_texto(texto)
        
        resultados = {
            'validos': [],
            'errores': [],
            'advertencias': []
        }
        
        for linea in lineas:
            cargo_nombre = linea['cargo']
            viernes_texto = linea['viernes']
            sabado_texto = linea['sabado']
            
            # Buscar cargo
            cargo = self.buscar_cargo_por_nombre(cargo_nombre)
            if not cargo:
                resultados['errores'].append({
                    'tipo': 'cargo_no_existe',
                    'cargo': cargo_nombre,
                    'mensaje': f'Cargo "{cargo_nombre}" no encontrado'
                })
                continue
            
            # Procesar trabajadores del viernes
            if viernes_texto:
                nombres_viernes = self.parse_nombres_trabajadores(viernes_texto)
                for nombre in nombres_viernes:
                    trabajador = self.buscar_trabajador_por_nombre(nombre)
                    if trabajador:
                        resultados['validos'].append({
                            'fecha': fecha_viernes,
                            'tipo_turno': tipo_turno,
                            'cargo': cargo.nombre,
                            'cargo_id': cargo.id,
                            'trabajador': trabajador.name,
                            'trabajador_id': trabajador.id
                        })
                    else:
                        resultados['advertencias'].append({
                            'tipo': 'trabajador_no_existe',
                            'nombre': nombre,
                            'cargo': cargo_nombre,
                            'fecha': fecha_viernes,
                            'mensaje': f'Trabajador "{nombre}" no encontrado para cargo {cargo_nombre}'
                        })
            
            # Procesar trabajadores del sábado
            if sabado_texto:
                nombres_sabado = self.parse_nombres_trabajadores(sabado_texto)
                for nombre in nombres_sabado:
                    trabajador = self.buscar_trabajador_por_nombre(nombre)
                    if trabajador:
                        resultados['validos'].append({
                            'fecha': fecha_sabado,
                            'tipo_turno': tipo_turno,
                            'cargo': cargo.nombre,
                            'cargo_id': cargo.id,
                            'trabajador': trabajador.name,
                            'trabajador_id': trabajador.id
                        })
                    else:
                        resultados['advertencias'].append({
                            'tipo': 'trabajador_no_existe',
                            'nombre': nombre,
                            'cargo': cargo_nombre,
                            'fecha': fecha_sabado,
                            'mensaje': f'Trabajador "{nombre}" no encontrado para cargo {cargo_nombre}'
                        })
        
        return resultados
    
    def importar_asignaciones(
        self,
        texto: str,
        fecha_viernes: date,
        fecha_sabado: date,
        tipo_turno: str,
        crear_placeholders: bool = False
    ) -> Dict[str, Any]:
        """
        Importa asignaciones desde texto.
        
        Args:
            texto: Texto copiado de tabla
            fecha_viernes: Fecha del viernes
            fecha_sabado: Fecha del sábado
            tipo_turno: 'NOCHE' o 'DIA'
            crear_placeholders: Si True, crea trabajadores placeholder si no existen
            
        Returns:
            Dict con resumen de importación
        """
        lineas = self.parse_tabla_texto(texto)
        
        resultados = {
            'insertados': 0,
            'duplicados': 0,
            'errores': [],
            'advertencias': []
        }
        
        for linea in lineas:
            cargo_nombre = linea['cargo']
            viernes_texto = linea['viernes']
            sabado_texto = linea['sabado']
            
            # Buscar cargo
            cargo = self.buscar_cargo_por_nombre(cargo_nombre)
            if not cargo:
                resultados['errores'].append({
                    'tipo': 'cargo_no_existe',
                    'cargo': cargo_nombre,
                    'mensaje': f'Cargo "{cargo_nombre}" no encontrado'
                })
                continue
            
            # Procesar trabajadores del viernes
            if viernes_texto:
                nombres_viernes = self.parse_nombres_trabajadores(viernes_texto)
                for nombre in nombres_viernes:
                    trabajador = self.buscar_trabajador_por_nombre(nombre)
                    
                    if not trabajador:
                        if crear_placeholders:
                            # Crear placeholder
                            trabajador = self._crear_trabajador_placeholder(nombre, cargo)
                            resultados['advertencias'].append({
                                'tipo': 'trabajador_placeholder',
                                'nombre': nombre,
                                'mensaje': f'Trabajador "{nombre}" creado como placeholder'
                            })
                        else:
                            resultados['errores'].append({
                                'tipo': 'trabajador_no_existe',
                                'nombre': nombre,
                                'cargo': cargo_nombre,
                                'fecha': fecha_viernes,
                                'mensaje': f'Trabajador "{nombre}" no encontrado'
                            })
                            continue
                    
                    # Intentar crear asignación
                    resultado = self._crear_asignacion(
                        fecha_viernes,
                        tipo_turno,
                        cargo.id,
                        trabajador.id
                    )
                    
                    if resultado['exito']:
                        resultados['insertados'] += 1
                    elif resultado['duplicado']:
                        resultados['duplicados'] += 1
                    else:
                        resultados['errores'].append(resultado['error'])
            
            # Procesar trabajadores del sábado
            if sabado_texto:
                nombres_sabado = self.parse_nombres_trabajadores(sabado_texto)
                for nombre in nombres_sabado:
                    trabajador = self.buscar_trabajador_por_nombre(nombre)
                    
                    if not trabajador:
                        if crear_placeholders:
                            trabajador = self._crear_trabajador_placeholder(nombre, cargo)
                            resultados['advertencias'].append({
                                'tipo': 'trabajador_placeholder',
                                'nombre': nombre,
                                'mensaje': f'Trabajador "{nombre}" creado como placeholder'
                            })
                        else:
                            resultados['errores'].append({
                                'tipo': 'trabajador_no_existe',
                                'nombre': nombre,
                                'cargo': cargo_nombre,
                                'fecha': fecha_sabado,
                                'mensaje': f'Trabajador "{nombre}" no encontrado'
                            })
                            continue
                    
                    # Intentar crear asignación
                    resultado = self._crear_asignacion(
                        fecha_sabado,
                        tipo_turno,
                        cargo.id,
                        trabajador.id
                    )
                    
                    if resultado['exito']:
                        resultados['insertados'] += 1
                    elif resultado['duplicado']:
                        resultados['duplicados'] += 1
                    else:
                        resultados['errores'].append(resultado['error'])
        
        return resultados
    
    def _crear_trabajador_placeholder(self, nombre: str, cargo: Cargo) -> Employee:
        """
        Crea un trabajador placeholder.
        
        Args:
            nombre: Nombre del trabajador
            cargo: Cargo asociado
            
        Returns:
            Employee creado
        """
        # Generar ID único (usar timestamp + nombre)
        import time
        nuevo_id = f"PLACEHOLDER_{int(time.time())}_{nombre.replace(' ', '_')}"
        
        trabajador = Employee(
            id=nuevo_id,
            name=nombre,
            first_name=nombre.split()[0] if nombre.split() else nombre,
            last_name=' '.join(nombre.split()[1:]) if len(nombre.split()) > 1 else '',
            cargo=cargo.nombre,
            is_active=True,
            synced_from_phppos=False
        )
        
        db.session.add(trabajador)
        db.session.flush()  # Para obtener el ID
        
        current_app.logger.warning(f"⚠️ Trabajador placeholder creado: {nombre} (ID: {nuevo_id})")
        
        return trabajador
    
    def _crear_asignacion(
        self,
        fecha: date,
        tipo_turno: str,
        cargo_id: int,
        trabajador_id: str
    ) -> Dict[str, Any]:
        """
        Crea una asignación si no existe.
        
        Args:
            fecha: Fecha del turno
            tipo_turno: 'NOCHE' o 'DIA'
            cargo_id: ID del cargo
            trabajador_id: ID del trabajador
            
        Returns:
            Dict con resultado: {'exito': bool, 'duplicado': bool, 'error': dict}
        """
        try:
            # Verificar si ya existe
            existente = ProgramacionAsignacion.query.filter_by(
                fecha=fecha,
                tipo_turno=tipo_turno,
                cargo_id=cargo_id,
                trabajador_id=trabajador_id
            ).first()
            
            if existente:
                return {
                    'exito': False,
                    'duplicado': True,
                    'error': None
                }
            
            # Crear nueva asignación
            asignacion = ProgramacionAsignacion(
                fecha=fecha,
                tipo_turno=tipo_turno,
                cargo_id=cargo_id,
                trabajador_id=trabajador_id
            )
            
            db.session.add(asignacion)
            db.session.commit()
            
            return {
                'exito': True,
                'duplicado': False,
                'error': None
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear asignación: {e}", exc_info=True)
            return {
                'exito': False,
                'duplicado': False,
                'error': {
                    'tipo': 'error_creacion',
                    'mensaje': str(e)
                }
            }











