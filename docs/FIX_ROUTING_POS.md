# 🔧 FIX: Routing del POS - /caja 404

**Fecha:** 2025-01-15  
**Problema:** `GET /caja` devolvía 404 en producción  
**Solución:** Agregada ruta home que redirige a `/caja/login`

---

## 🐛 PROBLEMA

En producción:
- `GET https://stvaldivia.cl/caja` → **404 Not Found**
- `GET https://stvaldivia.cl/caja/login` → ✅ 200 OK

**Causa:** No existía ruta para `/caja` o `/caja/` en el blueprint `caja_bp`.

---

## ✅ SOLUCIÓN IMPLEMENTADA

### 1. Ruta Home Agregada

**Archivo:** `app/blueprints/pos/views/auth.py`

```python
@caja_bp.route('/', methods=['GET'])
@caja_bp.route('', methods=['GET'])
def home():
    """Home del POS - Redirige a login"""
    return redirect(url_for('caja.login'))
```

**Comportamiento:**
- `GET /caja` → 302 → `/caja/login`
- `GET /caja/` → 302 → `/caja/login`
- `GET /caja/login` → 200 (sin cambios)

### 2. Smoke Test Creado

**Archivo:** `tools/test_pos_routes.py`

Script para validar que las rutas funcionan correctamente:

```bash
# Probar en producción
python3 tools/test_pos_routes.py https://stvaldivia.cl

# Probar en local
python3 tools/test_pos_routes.py http://localhost:5001
```

**Valida:**
- `GET /caja` → 302 con Location: `/caja/login`
- `GET /caja/` → 302 con Location: `/caja/login`
- `GET /caja/login` → 200

### 3. Documentación Actualizada

**Archivo:** `docs/ACCESO_POS_BIMBA.md`

- Actualizado para indicar que `/caja` redirige automáticamente a `/caja/login`
- Clarificado que ambas URLs son válidas

---

## 🧪 VERIFICACIÓN LOCAL

```python
from app import create_app
app = create_app()
with app.test_client() as client:
    # Test /caja
    r1 = client.get('/caja', follow_redirects=False)
    assert r1.status_code == 302
    assert '/caja/login' in r1.headers.get('Location', '')
    
    # Test /caja/
    r2 = client.get('/caja/', follow_redirects=False)
    assert r2.status_code == 302
    assert '/caja/login' in r2.headers.get('Location', '')
    
    # Test /caja/login
    r3 = client.get('/caja/login', follow_redirects=False)
    assert r3.status_code == 200
```

---

## 🚀 DESPLIEGUE

### Pre-requisitos
- [ ] Código en branch main/stable
- [ ] Tests locales pasan

### Pasos

1. **Pull en servidor:**
   ```bash
   cd /ruta/al/proyecto
   git pull origin main
   ```

2. **Reiniciar servicio:**
   ```bash
   sudo systemctl restart gunicorn
   # o
   sudo systemctl restart flask-app
   ```

3. **Verificar:**
   ```bash
   # Usar el smoke test
   python3 tools/test_pos_routes.py https://stvaldivia.cl
   ```

4. **Verificar manualmente:**
   - Abrir `https://stvaldivia.cl/caja` en navegador
   - Debe redirigir automáticamente a `/caja/login`
   - No debe mostrar 404

---

## ✅ CHECKLIST POST-DEPLOY

- [ ] `GET /caja` responde 302 (redirect)
- [ ] `GET /caja/` responde 302 (redirect)
- [ ] `GET /caja/login` responde 200 (OK)
- [ ] No hay redirect loops
- [ ] Smoke test pasa
- [ ] Navegador redirige correctamente

---

## 🔍 TROUBLESHOOTING

### Si sigue dando 404 después del deploy

1. **Verificar que el código se actualizó:**
   ```bash
   grep -n "def home" app/blueprints/pos/views/auth.py
   ```

2. **Verificar que el servicio se reinició:**
   ```bash
   sudo systemctl status gunicorn
   ```

3. **Verificar logs:**
   ```bash
   sudo journalctl -u gunicorn -n 50 --no-pager
   ```

4. **Verificar nginx (si aplica):**
   - Asegurar que `proxy_pass` apunta al upstream correcto
   - Verificar que no hay reglas que bloqueen `/caja`

### Si hay redirect loop

- Verificar que `home()` solo redirige a `caja.login`
- Verificar que `login()` no redirige a `home()`

---

## 📝 NOTAS

- **Sin breaking changes:** Todas las URLs existentes siguen funcionando
- **Sin cambios en lógica:** Solo se agregó routing, no se modificó lógica de ventas
- **Compatible:** Funciona con y sin trailing slash

---

**Fix completado** ✅


