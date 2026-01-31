"""
DTOs relacionados con Jornadas
"""
from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class CrearJornadaRequest:
    """DTO para crear una jornada"""
    fecha_jornada: str
    tipo_turno: str  # "Noche", "Día", "Especial"
    nombre_fiesta: str
    horario_apertura_programado: str  # "20:00"
    horario_cierre_programado: Optional[str] = None  # Opcional - se registrará automáticamente al cerrar
    fecha_cierre_programada: Optional[str] = None  # Opcional - se calculará automáticamente al cerrar
    djs: Optional[str] = None
    barras_disponibles: Optional[List[str]] = None
    
    def validate(self) -> None:
        """Valida los datos del request"""
        if not self.fecha_jornada or not self.fecha_jornada.strip():
            raise ValueError("La fecha de jornada es requerida")
        if not self.tipo_turno or not self.tipo_turno.strip():
            raise ValueError("El tipo de turno es requerido")
        if not self.nombre_fiesta or not self.nombre_fiesta.strip():
            raise ValueError("El nombre de la fiesta es requerido")
        if not self.horario_apertura_programado or not self.horario_apertura_programado.strip():
            raise ValueError("El horario de apertura programado es requerido")
        
        # Validar formato de hora de apertura
        try:
            from datetime import datetime
            datetime.strptime(self.horario_apertura_programado, '%H:%M')
            # Si se proporciona horario de cierre, validarlo también
            if self.horario_cierre_programado:
                datetime.strptime(self.horario_cierre_programado, '%H:%M')
        except ValueError:
            raise ValueError("El formato de hora debe ser HH:MM (ej: 20:00)")


@dataclass
class AgregarTrabajadorRequest:
    """DTO para agregar un trabajador a la planilla"""
    id_empleado: str
    nombre_empleado: str
    rol: str  # "cajero", "bartender", "seguridad", "admin", "puerta"
    hora_inicio: str  # "20:00"
    hora_fin: str  # "04:00"
    costo_hora: float
    area: Optional[str] = None
    
    def validate(self) -> None:
        """Valida los datos del request"""
        if not self.id_empleado or not self.id_empleado.strip():
            raise ValueError("El ID del empleado es requerido")
        if not self.nombre_empleado or not self.nombre_empleado.strip():
            raise ValueError("El nombre del empleado es requerido")
        if not self.rol or not self.rol.strip():
            raise ValueError("El rol es requerido")
        if not self.hora_inicio or not self.hora_inicio.strip():
            raise ValueError("La hora de inicio es requerida")
        if not self.hora_fin or not self.hora_fin.strip():
            raise ValueError("La hora de fin es requerida")
        if self.costo_hora < 0:
            raise ValueError("El costo por hora debe ser mayor o igual a 0")
        
        # Validar formato de hora
        try:
            from datetime import datetime
            datetime.strptime(self.hora_inicio, '%H:%M')
            datetime.strptime(self.hora_fin, '%H:%M')
        except ValueError:
            raise ValueError("El formato de hora debe ser HH:MM (ej: 20:00)")


@dataclass
class EliminarTrabajadorRequest:
    """DTO para eliminar un trabajador de la planilla"""
    planilla_id: int
    
    def validate(self) -> None:
        """Valida los datos del request"""
        if not self.planilla_id or self.planilla_id <= 0:
            raise ValueError("El ID de planilla es requerido y debe ser mayor a 0")


@dataclass
class AsignarResponsablesRequest:
    """DTO para asignar responsables por área"""
    responsable_cajas: str
    responsable_puerta: str
    responsable_seguridad: str
    responsable_admin: str
    
    def validate(self) -> None:
        """Valida los datos del request"""
        if not self.responsable_cajas or not self.responsable_cajas.strip():
            raise ValueError("El responsable de cajas es requerido")
        if not self.responsable_puerta or not self.responsable_puerta.strip():
            raise ValueError("El responsable de puerta es requerido")
        if not self.responsable_seguridad or not self.responsable_seguridad.strip():
            raise ValueError("El responsable de seguridad es requerido")
        if not self.responsable_admin or not self.responsable_admin.strip():
            raise ValueError("El responsable admin es requerido")


@dataclass
class AbrirCajaRequest:
    """DTO para abrir una caja"""
    id_caja: str
    nombre_caja: str
    id_empleado: str
    nombre_empleado: str
    fondo_inicial: float
    abierto_por: str
    
    def validate(self) -> None:
        """Valida los datos del request"""
        if not self.id_caja or not self.id_caja.strip():
            raise ValueError("El ID de la caja es requerido")
        if not self.nombre_caja or not self.nombre_caja.strip():
            raise ValueError("El nombre de la caja es requerido")
        if not self.id_empleado or not self.id_empleado.strip():
            raise ValueError("El ID del empleado es requerido")
        if not self.nombre_empleado or not self.nombre_empleado.strip():
            raise ValueError("El nombre del empleado es requerido")
        if self.fondo_inicial < 0:
            raise ValueError("El fondo inicial debe ser mayor o igual a 0")
        if not self.abierto_por or not self.abierto_por.strip():
            raise ValueError("El campo abierto_por es requerido")


@dataclass
class CompletarChecklistTecnicoRequest:
    """DTO para completar el checklist técnico"""
    checklist: Dict[str, bool]  # {"pos_funcionando": True, "impresoras_ok": False, ...}
    
    def validate(self) -> None:
        """Valida los datos del request"""
        if not self.checklist:
            raise ValueError("El checklist no puede estar vacío")
        if not isinstance(self.checklist, dict):
            raise ValueError("El checklist debe ser un diccionario")


@dataclass
class AbrirLocalRequest:
    """DTO para abrir el local (finalizar proceso de apertura)"""
    abierto_por: str
    
    def validate(self) -> None:
        """Valida los datos del request"""
        if not self.abierto_por or not self.abierto_por.strip():
            raise ValueError("El campo abierto_por es requerido")

