#!/usr/bin/env python3
"""
Script para agregar trabajadores al equipo y asignarlos en programación
basado en la tabla de programación proporcionada.
"""
from app import create_app
from app.models import db
from app.models.pos_models import Employee
from app.models.cargo_models import Cargo
from app.models.programacion_models import ProgramacionAsignacion
from datetime import date, datetime
from sqlalchemy import func

def get_or_create_cargo(nombre_cargo):
    """Obtiene o crea un cargo si no existe"""
    cargo = Cargo.query.filter_by(nombre=nombre_cargo.upper()).first()
    if not cargo:
        # Buscar cargo similar
        cargo = Cargo.query.filter(func.lower(Cargo.nombre) == nombre_cargo.lower()).first()
    if not cargo:
        print(f"⚠️  Cargo '{nombre_cargo}' no encontrado. Creando...")
        # Obtener el máximo orden
        max_orden = db.session.query(func.max(Cargo.orden)).scalar() or 0
        cargo = Cargo(
            nombre=nombre_cargo.upper(),
            descripcion=f"Cargo {nombre_cargo}",
            activo=True,
            orden=max_orden + 1
        )
        db.session.add(cargo)
        db.session.commit()
        print(f"✅ Cargo '{nombre_cargo}' creado con ID {cargo.id}")
    return cargo

def get_or_create_employee(nombre, cargo_nombre=None):
    """Obtiene o crea un empleado si no existe"""
    # Buscar por nombre (case insensitive)
    employee = Employee.query.filter(
        func.lower(Employee.name) == nombre.lower()
    ).first()
    
    if not employee:
        # Generar ID único
        max_id = db.session.query(func.max(func.cast(Employee.id, db.Integer))).filter(
            func.cast(Employee.id, db.Integer).isnot(None)
        ).scalar()
        
        if max_id is None:
            # Buscar el máximo ID numérico de otra forma
            try:
                employees = Employee.query.all()
                numeric_ids = []
                for emp in employees:
                    try:
                        numeric_ids.append(int(emp.id))
                    except (ValueError, TypeError):
                        pass
                max_id = max(numeric_ids) if numeric_ids else 0
            except:
                max_id = 0
        
        employee_id = str(max_id + 1)
        
        # Verificar que el ID no exista
        while Employee.query.get(employee_id):
            max_id += 1
            employee_id = str(max_id)
        
        # Determinar si es bartender o cajero según el cargo
        cargo_lower = cargo_nombre.lower() if cargo_nombre else ''
        is_bartender = 'barra' in cargo_lower or cargo_lower == 'bartender' or cargo_lower == 'coperx'
        is_cashier = cargo_lower == 'caja' or cargo_lower == 'cajero'
        
        employee = Employee(
            id=employee_id,
            name=nombre,
            cargo=cargo_nombre.upper() if cargo_nombre else None,
            is_active=True,
            is_bartender=is_bartender,
            is_cashier=is_cashier,
            synced_from_phppos=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(employee)
        db.session.commit()
        print(f"✅ Trabajador '{nombre}' creado con ID {employee_id}")
    else:
        # Actualizar cargo si se proporciona y es diferente
        if cargo_nombre and employee.cargo != cargo_nombre.upper():
            employee.cargo = cargo_nombre.upper()
            db.session.commit()
            print(f"🔄 Trabajador '{nombre}' actualizado con cargo {cargo_nombre.upper()}")
    
    return employee

def create_programacion_asignacion(fecha, tipo_turno, cargo_nombre, trabajador_nombre):
    """Crea una asignación de programación si no existe"""
    # Obtener cargo
    cargo = get_or_create_cargo(cargo_nombre)
    
    # Obtener trabajador
    trabajador = get_or_create_employee(trabajador_nombre, cargo_nombre)
    
    # Verificar si ya existe
    existing = ProgramacionAsignacion.query.filter_by(
        fecha=fecha,
        tipo_turno=tipo_turno,
        cargo_id=cargo.id,
        trabajador_id=trabajador.id
    ).first()
    
    if existing:
        print(f"  ⏭️  Asignación ya existe: {cargo_nombre} - {trabajador_nombre} ({fecha})")
        return existing
    
    # Crear asignación
    asignacion = ProgramacionAsignacion(
        fecha=fecha,
        tipo_turno=tipo_turno,
        cargo_id=cargo.id,
        trabajador_id=trabajador.id,
        created_at=datetime.utcnow()
    )
    db.session.add(asignacion)
    db.session.commit()
    print(f"  ✅ Asignación creada: {cargo_nombre} - {trabajador_nombre} ({fecha})")
    return asignacion

def main():
    app = create_app()
    with app.app_context():
        print("🚀 Iniciando carga de trabajadores y programación...")
        print("=" * 60)
        
        # Fechas (asumiendo diciembre 2025)
        fecha_viernes = date(2025, 12, 12)
        fecha_sabado = date(2025, 12, 13)
        tipo_turno = 'NOCHE'
        
        # Datos de la programación
        programacion = [
            # BARRA
            ('BARRA', fecha_viernes, ['Zafiro', 'Niko', 'Ignacio']),
            ('BARRA', fecha_sabado, ['Javi', 'Fefy', 'Niko']),
            
            # COPERX
            ('COPERX', fecha_viernes, ['Claudio']),
            ('COPERX', fecha_sabado, ['Ursula']),
            
            # CAJA
            ('CAJA', fecha_viernes, ['David', 'Andy', 'Angie']),
            ('CAJA', fecha_sabado, ['David', 'Andy', 'Franco V.', 'Angie']),
            
            # GUARDIA
            ('GUARDIA', fecha_viernes, ['Jaime', 'Jonathan', 'Nathy']),
            ('GUARDIA', fecha_sabado, ['Jaime', 'Jonathan', 'Claudia']),
            
            # ANFITRIONA
            ('ANFITRIONA', fecha_viernes, ['Ursula']),
            ('ANFITRIONA', fecha_sabado, ['Mala']),
            
            # ASEO
            ('ASEO', fecha_viernes, ['Haydee']),
            ('ASEO', fecha_sabado, ['Haydee']),
            
            # GUARDARROP
            ('GUARDARROP', fecha_viernes, ['Jana']),
            ('GUARDARROP', fecha_sabado, ['Jana']),
            
            # TÉCNICA
            ('TÉCNICA', fecha_viernes, ['Koi']),
            ('TÉCNICA', fecha_sabado, ['Seba']),
            
            # DRAG
            ('DRAG', fecha_viernes, ['Noxie']),
            ('DRAG', fecha_sabado, ['Reina']),
            
            # DJ
            ('DJ', fecha_viernes, ['Garos']),
            ('DJ', fecha_sabado, ['Thanatos', 'Shespi', 'Popa']),
        ]
        
        trabajadores_creados = set()
        asignaciones_creadas = 0
        
        print("\n📋 Creando trabajadores y asignaciones...")
        print("-" * 60)
        
        for cargo_nombre, fecha, trabajadores in programacion:
            print(f"\n📌 {cargo_nombre} - {fecha.strftime('%Y-%m-%d')}:")
            for trabajador_nombre in trabajadores:
                if trabajador_nombre.strip():  # Ignorar nombres vacíos
                    # Crear trabajador si no existe
                    trabajador = get_or_create_employee(trabajador_nombre.strip(), cargo_nombre)
                    trabajadores_creados.add(trabajador.name)
                    
                    # Crear asignación
                    create_programacion_asignacion(fecha, tipo_turno, cargo_nombre, trabajador_nombre.strip())
                    asignaciones_creadas += 1
        
        print("\n" + "=" * 60)
        print(f"✅ Proceso completado:")
        print(f"   - Trabajadores únicos: {len(trabajadores_creados)}")
        print(f"   - Asignaciones creadas: {asignaciones_creadas}")
        print("=" * 60)

if __name__ == '__main__':
    main()

