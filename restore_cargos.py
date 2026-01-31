"""
Script para restaurar cargos por defecto
"""
from app import create_app
from app.models import db
from app.models.cargo_models import Cargo
from app.models.cargo_salary_models import CargoSalaryConfig

def restore_cargos():
    app = create_app()
    with app.app_context():
        try:
            cargos_default = [
                ('BARRA', 1, 'Personal de barra y servicio de bebidas'),
                ('COPERX', 2, 'Coperx - Personal de servicio'),
                ('CAJA', 3, 'Personal de caja y cobro'),
                ('GUARDIA', 4, 'Personal de seguridad y guardia'),
                ('ANFITRIONA', 5, 'Anfitriona - Recepción y atención al cliente'),
                ('ASEO', 6, 'Personal de limpieza y aseo'),
                ('GUARDARROP', 7, 'Personal de guardarropa'),
                ('TÉCNICA', 8, 'Personal técnico y mantenimiento'),
                ('DRAG', 9, 'Artistas drag'),
                ('DJ', 10, 'DJs y música'),
                ('Supervisor', 11, 'Supervisores'),
                ('Administrador', 12, 'Personal administrativo'),
                ('Otro', 13, 'Otros cargos')
            ]
            
            # Verificar cargos existentes
            cargos_existentes = Cargo.query.all()
            print(f"📋 Cargos existentes en BD: {len(cargos_existentes)}")
            for cargo in cargos_existentes:
                print(f"  - {cargo.nombre} (ID: {cargo.id}, Activo: {cargo.activo})")
            
            cargos_creados = 0
            cargos_reactivados = 0
            configs_creadas = 0
            
            for nombre, orden, descripcion in cargos_default:
                cargo_existente = Cargo.query.filter_by(nombre=nombre).first()
                
                if not cargo_existente:
                    # Crear nuevo cargo
                    nuevo_cargo = Cargo(
                        nombre=nombre,
                        descripcion=descripcion,
                        activo=True,
                        orden=orden
                    )
                    db.session.add(nuevo_cargo)
                    cargos_creados += 1
                    print(f"✅ Creado cargo: {nombre}")
                else:
                    # Reactivar si está desactivado
                    if not cargo_existente.activo:
                        cargo_existente.activo = True
                        cargos_reactivados += 1
                        print(f"✅ Reactivado cargo: {nombre}")
                    # Actualizar orden si es necesario
                    if cargo_existente.orden != orden:
                        cargo_existente.orden = orden
                        print(f"📝 Actualizado orden de {nombre}: {cargo_existente.orden} -> {orden}")
                
                # Crear configuración de sueldo por defecto si no existe
                cargo_salary_existente = CargoSalaryConfig.query.filter_by(cargo=nombre).first()
                if not cargo_salary_existente:
                    cargo_salary = CargoSalaryConfig(
                        cargo=nombre,
                        sueldo_por_turno=0.0,
                        bono_fijo=0.0
                    )
                    db.session.add(cargo_salary)
                    configs_creadas += 1
                    print(f"✅ Creada configuración de sueldo para: {nombre}")
            
            if cargos_creados > 0 or cargos_reactivados > 0 or configs_creadas > 0:
                db.session.commit()
                print(f"\n✅ Resumen:")
                print(f"   - Cargos creados: {cargos_creados}")
                print(f"   - Cargos reactivados: {cargos_reactivados}")
                print(f"   - Configuraciones de sueldo creadas: {configs_creadas}")
            else:
                print("\n✅ Todos los cargos ya existen y están activos")
            
            # Verificar cargos activos
            cargos_activos = Cargo.query.filter_by(activo=True).order_by(Cargo.orden, Cargo.nombre).all()
            print(f"\n📋 Total de cargos activos: {len(cargos_activos)}")
            for cargo in cargos_activos:
                print(f"  - {cargo.nombre} (Orden: {cargo.orden})")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al restaurar cargos: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    restore_cargos()











