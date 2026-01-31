"""
Rutas modulares del sistema BIMBA

NOTA: Por ahora importamos desde el archivo routes.py del nivel superior.
Los módulos en este directorio están preparados para migración futura.
"""
# Re-exportar el blueprint desde el archivo routes.py del nivel superior
# Para evitar conflicto con este directorio, importamos desde el módulo específico
import sys
import importlib.util
import os

# Importar desde app/routes.py (archivo, no este directorio)
parent_dir = os.path.dirname(os.path.dirname(__file__))
routes_file = os.path.join(parent_dir, 'routes.py')

# Verificar que el archivo existe
if os.path.exists(routes_file):
    # Usar importlib para importar desde la ruta del archivo
    spec = importlib.util.spec_from_file_location("app_routes_file", routes_file)
    if spec and spec.loader:
        routes_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(routes_module)
        # Re-exportar el blueprint
        bp = getattr(routes_module, 'bp', None)
        if bp is None:
            # Si no existe, crear uno vacío
            from flask import Blueprint
            bp = Blueprint('routes', __name__)
    else:
        from flask import Blueprint
        bp = Blueprint('routes', __name__)
else:
    # Si el archivo no existe, crear un blueprint vacío
    from flask import Blueprint
    bp = Blueprint('routes', __name__)

