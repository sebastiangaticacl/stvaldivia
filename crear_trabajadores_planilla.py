"""
Script para crear miembros del equipo desde la planilla
Todos los miembros del equipo tendrán PIN 1234
"""
from app import create_app
from app.models import db
from app.models.pos_models import Employee
from app.models.cargo_models import Cargo
from werkzeug.security import generate_password_hash
from datetime import datetime

# Mapeo de miembros del equipo y sus cargos según la planilla
# Si un miembro del equipo aparece en múltiples cargos, se usa el primero que aparece
EQUIPO = [
    # BARRA
    {'nombre': 'Zafiro', 'cargo': 'BARRA'},
    {'nombre': 'Niko', 'cargo': 'BARRA'},
    {'nombre': 'Ignacio', 'cargo': 'BARRA'},
    {'nombre': 'Javi', 'cargo': 'BARRA'},
    {'nombre': 'Fefy', 'cargo': 'BARRA'},
    
    # COPERX
    {'nombre': 'Claudio', 'cargo': 'COPERX'},
    {'nombre': 'Ursula', 'cargo': 'COPERX'},  # También aparece como ANFITRIONA, pero usamos COPERX
    
    # CAJA
    {'nombre': 'David', 'cargo': 'CAJA'},
    {'nombre': 'Andy', 'cargo': 'CAJA'},
    {'nombre': 'Angie', 'cargo': 'CAJA'},
    {'nombre': 'Franco V.', 'cargo': 'CAJA'},
    
    # GUARDIA
    {'nombre': 'Jaime', 'cargo': 'GUARDIA'},
    {'nombre': 'Jonathan', 'cargo': 'GUARDIA'},
    {'nombre': 'Nathy', 'cargo': 'GUARDIA'},
    {'nombre': 'Claudia', 'cargo': 'GUARDIA'},
    
    # ANFITRIONA
    {'nombre': 'Mala', 'cargo': 'ANFITRIONA'},
    
    # ASEO
    {'nombre': 'Haydee', 'cargo': 'ASEO'},
    
    # GUARDARROP
    {'nombre': 'Jana', 'cargo': 'GUARDARROP'},
    
    # TÉCNICA
    {'nombre': 'Koi', 'cargo': 'TÉCNICA'},
    {'nombre': 'Seba', 'cargo': 'TÉCNICA'},
    
    # DRAG
    {'nombre': 'Noxie', 'cargo': 'DRAG'},
    {'nombre': 'Reina', 'cargo': 'DRAG'},
    
    # DJ
    {'nombre': 'Garos', 'cargo': 'DJ'},
    {'nombre': 'Thanatos', 'cargo': 'DJ'},
    {'nombre': 'Shespi', 'cargo': 'DJ'},
    {'nombre': 'Popa', 'cargo': 'DJ'},
]

PIN_DEFAULT = '1234'

def get_next_employee_id():
    """Obtiene el siguiente ID disponible para empleado"""
    try:
        # Obtener todos los empleados y filtrar los que tienen ID numérico
        all_employees = Employee.query.all()
        numeric_ids = []
        
        for emp in all_employees:
            if emp.id:
                try:
                    # Intentar convertir a int
                    numeric_id = int(emp.id)
                    numeric_ids.append(numeric_id)
                except (ValueError, TypeError):
                    # Si no es numérico, ignorar
                    pass
        
        if numeric_ids:
            max_id = max(numeric_ids)
            return str(max_id + 1)
    except Exception as e:
        print(f"⚠️  Advertencia al obtener siguiente ID: {e}")
    
    # Si no hay empleados o hay error, empezar desde 1
    return '1'

def create_employees():
    """Crea los miembros del equipo en la base de datos"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar que los cargos existan
            cargos_existentes = {c.nombre: c for c in Cargo.query.all()}
            cargos_faltantes = []
            
            for miembro_equipo in EQUIPO:
                cargo_nombre = miembro_equipo['cargo']
                if cargo_nombre not in cargos_existentes:
                    cargos_faltantes.append(cargo_nombre)
            
            if cargos_faltantes:
                print(f"⚠️  ADVERTENCIA: Los siguientes cargos no existen: {', '.join(set(cargos_faltantes))}")
                print("   Se crearán automáticamente o se usarán los cargos existentes.")
            
            # Crear hash del PIN
            pin_hash = generate_password_hash(PIN_DEFAULT)
            
            miembros_creados = 0
            miembros_existentes = 0
            miembros_actualizados = 0
            errores = []
            
            print("\n" + "="*60)
            print("📋 CREACIÓN DE EQUIPO DESDE PLANILLA")
            print("="*60)
            print(f"\nTotal de miembros del equipo a procesar: {len(EQUIPO)}")
            print(f"PIN por defecto para todos: {PIN_DEFAULT}\n")
            
            for miembro_equipo in EQUIPO:
                nombre = miembro_equipo['nombre']
                cargo_nombre = miembro_equipo['cargo']
                
                try:
                    # Buscar si ya existe un empleado con ese nombre
                    empleado_existente = Employee.query.filter_by(name=nombre).first()
                    
                    if empleado_existente:
                        # Actualizar si es necesario
                        actualizado = False
                        if empleado_existente.cargo != cargo_nombre:
                            empleado_existente.cargo = cargo_nombre
                            actualizado = True
                        if empleado_existente.pin != PIN_DEFAULT:
                            empleado_existente.pin = PIN_DEFAULT
                            empleado_existente.pin_hash = pin_hash
                            actualizado = True
                        if not empleado_existente.is_active:
                            empleado_existente.is_active = True
                            actualizado = True
                        
                        if actualizado:
                            empleado_existente.updated_at = datetime.utcnow()
                            miembros_actualizados += 1
                            print(f"  ✅ Actualizado: {nombre} ({cargo_nombre})")
                        else:
                            miembros_existentes += 1
                            print(f"  ⏭️  Ya existe: {nombre} ({cargo_nombre})")
                    else:
                        # Crear nuevo empleado
                        nuevo_id = get_next_employee_id()
                        
                        # Verificar que el ID no exista (por seguridad)
                        existing_id = Employee.query.filter_by(id=nuevo_id).first()
                        if existing_id:
                            # Si existe, buscar el siguiente disponible
                            max_id = int(nuevo_id) - 1
                            while existing_id:
                                max_id += 1
                                nuevo_id = str(max_id)
                                existing_id = Employee.query.filter_by(id=nuevo_id).first()
                        
                        # Determinar tipo de empleado
                        is_bartender = cargo_nombre == 'BARRA'
                        is_cashier = cargo_nombre == 'CAJA'
                        
                        nuevo_empleado = Employee(
                            id=nuevo_id,
                            name=nombre,
                            pin=PIN_DEFAULT,
                            pin_hash=pin_hash,
                            cargo=cargo_nombre,
                            is_bartender=is_bartender,
                            is_cashier=is_cashier,
                            is_active=True,
                            deleted='0',
                            synced_from_phppos=False,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        
                        db.session.add(nuevo_empleado)
                        miembros_creados += 1
                        print(f"  ✨ Creado: {nombre} ({cargo_nombre}) - ID: {nuevo_id}")
                
                except Exception as e:
                    error_msg = f"Error con {nombre}: {str(e)}"
                    errores.append(error_msg)
                    print(f"  ❌ {error_msg}")
            
            # Commit de todos los cambios
            if miembros_creados > 0 or miembros_actualizados > 0:
                db.session.commit()
                print(f"\n✅ Cambios guardados en la base de datos")
            else:
                print(f"\nℹ️  No se realizaron cambios")
            
            # Resumen
            print("\n" + "="*60)
            print("📊 RESUMEN")
            print("="*60)
            print(f"  ✨ Miembros del equipo creados: {miembros_creados}")
            print(f"  ✅ Miembros del equipo actualizados: {miembros_actualizados}")
            print(f"  ⏭️  Miembros del equipo ya existentes: {miembros_existentes}")
            if errores:
                print(f"  ❌ Errores: {len(errores)}")
                for error in errores:
                    print(f"     - {error}")
            print("="*60 + "\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR CRÍTICO: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    create_employees()

