# ⚡ INSTRUCCIONES RÁPIDAS - CONFIGURAR DNS EN GOOGLE DOMAINS

## 🚀 MÉTODO RÁPIDO (2 minutos)

### Opción 1: Usar el script automatizado
```bash
./configurar_dns_google_domains.sh
```

### Opción 2: Manual (si prefieres hacerlo tú mismo)

1. **Abre Google Domains:**
   - Ve a: https://domains.google.com/registrar/stvaldivia.cl/dns
   - O ve a domains.google.com → stvaldivia.cl → DNS

2. **Crea 2 registros A:**
   
   **Registro 1:**
   - Tipo: `A`
   - Nombre: `@`
   - IP: `34.176.68.46`
   - TTL: `3600`
   - ✅ Guardar
   
   **Registro 2:**
   - Tipo: `A`
   - Nombre: `www`
   - IP: `34.176.68.46`
   - TTL: `3600`
   - ✅ Guardar

3. **Espera 10-15 minutos** para la propagación DNS

4. **Verifica:**
   ```bash
   dig stvaldivia.cl +short
   # Debe mostrar: 34.176.68.46
   ```

---

## ✅ CHECKLIST RÁPIDO

- [ ] Abierto Google Domains
- [ ] Creado registro A: `@` → `34.176.68.46`
- [ ] Creado registro A: `www` → `34.176.68.46`
- [ ] Guardado cambios
- [ ] Esperado 10-15 minutos
- [ ] Verificado con `dig stvaldivia.cl +short`

---

## 🎯 RESULTADO

Una vez propagado:
- ✅ http://stvaldivia.cl → Funciona
- ✅ http://www.stvaldivia.cl → Funciona
- ✅ http://stvaldivia.cl/api/v1/public/evento/hoy → Funciona

---

**IP:** `34.176.68.46`  
**URL directa:** https://domains.google.com/registrar/stvaldivia.cl/dns


