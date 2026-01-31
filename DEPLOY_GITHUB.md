# 🚀 Guía para Actualizar GitHub

## Opción 1: Si ya tienes un repositorio en GitHub

1. **Configurar el remoto**:
```bash
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
```

2. **Crear commits organizados** (ver abajo)

3. **Hacer push**:
```bash
git branch -M main
git push -u origin main
```

## Opción 2: Si necesitas crear un nuevo repositorio

1. **Crear repositorio en GitHub** (desde la web)
2. **Seguir Opción 1**

## Commits Sugeridos para Responsive

### Commit 1: Menú Móvil Responsive
```bash
git add app/static/css/main.css app/templates/base.html
git commit -m "feat(responsive): menú móvil completo con despliegue animado

- CSS mejorado con position fixed y animación slideDown
- JavaScript optimizado con protección contra doble disparo
- Menú se despliega desde arriba con efecto blur
- Logs de depuración para monitoreo
- Verificado funcionalmente en navegador móvil"
```

### Commit 2: Sistema Responsive Base (si no está commitado)
```bash
git add app/static/css/responsive-base.css app/static/css/tables-responsive.css
git commit -m "feat(responsive): sistema base mobile-first

- Variables CSS responsive (breakpoints, spacing, typography)
- Sistema de tablas responsive (cards en móvil, scroll en tablet)
- Utilidades responsive (containers, modals, forms)"
```

### Commit 3: Tablas Responsive
```bash
git add app/templates/admin/products/list.html \
        app/templates/admin/ingredients/list.html \
        app/templates/admin/generar_pagos.html \
        app/templates/admin/equipo/listar.html \
        app/templates/index.html
git commit -m "feat(responsive): tablas responsive en vistas críticas

- Aplicado table-responsive-wrapper y data-label
- Cards en móvil, scroll controlado en tablet
- Botones táctiles (44px mínimo)"
```

### Commit 4: Formularios Responsive
```bash
git add app/templates/admin/products/form.html \
        app/templates/admin/registers/form.html
git commit -m "feat(responsive): formularios mobile-first

- Inputs táctiles (44px mínimo)
- Grids adaptativos (1 col móvil, 2+ desktop)
- Labels y padding responsive"
```

### Commit 5: Dashboard y Modales
```bash
git add app/templates/admin_dashboard.html \
        app/templates/admin/inventory.html
git commit -m "feat(responsive): dashboard y modales responsive

- Grids responsive con clamp()
- Modales con ancho adaptable y scroll interno
- Tipografía responsive"
```

## Crear Tag de Versión (Opcional)

```bash
# Versión menor (ej: v1.1.0)
git tag -a v1.1.0 -m "Versión 1.1.0: Sistema responsive mobile-first completo"
git push origin v1.1.0

# O versión patch (ej: v1.0.1)
git tag -a v1.0.1 -m "Versión 1.0.1: Fix menú móvil responsive"
git push origin v1.0.1
```

## Push Final

```bash
git push -u origin main
```


