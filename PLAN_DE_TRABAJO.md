# 📋 PLAN DE TRABAJO - SISTEMA DE CONTROL CROSSFIT BOX
## Proyecto: Automatización de Conectores y Dashboard Centralizado

---

## ✅ COMPLETADO

### 1. Análisis y Diseño Técnico
- [x] Análisis de implicaciones de negocio, impuestos y contabilidad
- [x] Diseño de arquitectura técnica para centralización
- [x] Definición de fuentes de datos (BoxMagic, VirtualPOS, Lioren, Banco)
- [x] Diseño de modelo de datos para ingresos
- [x] Diseño de modelo de datos para egresos
- [x] Definición de lógica de reconciliación (Banco vs Gastos)

### 2. Configuración de Entorno
- [x] Creación de directorio de proyecto
- [x] Configuración de archivo `.env` con credenciales
- [x] Instalación de dependencias (Playwright, python-dotenv)

### 3. Conector BoxMagic
- [x] Investigación de mecanismos anti-bot
- [x] Implementación de estrategia de inyección de cookie de sesión
- [x] Desarrollo de script de prueba de acceso
- [x] Desarrollo de script de descarga de reportes
- [x] Validación de descarga exitosa de CSV
- [x] **Script final:** `boxmagic_downloader.py` ✅
    - [ ] Extract Inactive Users Report (Jan-Dec 2025) <!-- id: 16b -->

### 4. Conector VirtualPOS
- [x] Obtención de credenciales
- [x] Análisis de flujo de login (Landing → Acceso Clientes → Login)
- [x] Implementación de navegación automática
- [x] Validación de login exitoso
- [x] **Script de prueba:** `test_vpos_login.py` ✅

---

## 🔄 EN PROGRESO

### 5. Conector VirtualPOS - Descarga de Reportes
**Prioridad:** ALTA  
**Estado:** En Progreso (75%)  
**Estimación:** 1-2 horas adicionales

**Tareas:**
- [x] Analizar estructura del dashboard de VirtualPOS
- [x] Identificar sección de reportes/exportación
- [x] Implementar navegación automática al dashboard
- [ ] Resolver navegación al menú de Transacciones (timeout en clic)
- [ ] Localizar botón de descarga/exportación en página de transacciones
- [ ] Implementar descarga de archivo (CSV/Excel)
- [ ] Validar estructura de datos descargados
- [ ] Crear script de producción `virtualpos_downloader.py` (creado, requiere ajustes)
- [ ] Pruebas de descarga exitosa

**Hallazgos:**
- Dashboard accesible con datos de ventas ($3.954.300) y abonos ($4.478.966)
- Menú lateral con opciones: Dashboard, Transacciones, Herramientas de cobro, PAT Digital, CRM, Catálogo, Reportes
- Botón "Descargar" encontrado en sección QR (descarga QR, no reportes)
- Navegación a "Transacciones" requiere interacción con menú lateral (en proceso)

**Bloqueador Actual:**
- Timeout al hacer clic en enlace de Transacciones (elemento puede estar oculto o requerir hover)

**Entregable:** Script funcional que descarga reportes de transacciones de VirtualPOS

---

## 📅 PENDIENTE

### 6. Integración con Base de Datos PostgreSQL
**Prioridad:** ALTA  
**Estado:** No iniciado  
**Estimación:** 4-5 horas  
**Dependencias:** Completar conectores BoxMagic y VirtualPOS

**Tareas:**
- [ ] Revisar y ajustar schema de base de datos (`schema.sql`)
- [ ] Crear tabla para almacenar datos de BoxMagic
- [ ] Crear tabla para almacenar datos de VirtualPOS
- [ ] Desarrollar parser para CSV de BoxMagic
- [ ] Desarrollar parser para CSV/Excel de VirtualPOS
- [ ] Implementar lógica de inserción de datos
- [ ] Implementar detección de duplicados
- [ ] Crear script de ETL (Extract, Transform, Load)
- [ ] Pruebas de carga de datos

**Entregable:** Script `etl_pipeline.py` que procesa y carga datos en PostgreSQL

---

### 7. Automatización y Scheduling
**Prioridad:** MEDIA  
**Estado:** No iniciado  
**Estimación:** 2-3 horas  
**Dependencias:** Completar integración con BD

**Tareas:**
- [ ] Crear script maestro `run_daily_sync.py`
- [ ] Implementar manejo de errores y reintentos
- [ ] Configurar logging detallado
- [ ] Configurar notificaciones por email (opcional)
- [ ] Documentar proceso de configuración de tarea programada (Windows Task Scheduler)
- [ ] Crear script de instalación/configuración

**Entregable:** Sistema automatizado que ejecuta sincronización diaria

---

### 8. Dashboard de Visualización
**Prioridad:** MEDIA  
**Estado:** No iniciado  
**Estimación:** 6-8 horas  
**Dependencias:** Completar integración con BD

**Tareas:**
- [ ] Diseñar mockup de dashboard
- [ ] Crear consultas SQL para métricas clave:
  - Ingresos totales por fuente
  - Tendencia de ventas mensual
  - Comparativa BoxMagic vs VirtualPOS
  - Indicadores de crecimiento
- [ ] Desarrollar interfaz web (Streamlit o similar)
- [ ] Implementar gráficos interactivos
- [ ] Agregar filtros por fecha/fuente
- [ ] Pruebas de usabilidad

**Entregable:** Dashboard web funcional accesible localmente

---

### 9. Renovación de Cookie de BoxMagic
**Prioridad:** BAJA  
**Estado:** No iniciado  
**Estimación:** 3-4 horas  
**Dependencias:** Ninguna (puede hacerse en paralelo)

**Tareas:**
- [ ] Investigar tiempo de expiración de cookie `laravel_session`
- [ ] Desarrollar script de renovación manual de cookie
- [ ] Documentar proceso de extracción de cookie desde navegador
- [ ] Implementar sistema de alertas cuando cookie esté por expirar
- [ ] (Opcional) Investigar alternativas de autenticación más robustas

**Entregable:** Documentación y script de renovación de cookie

---

### 10. Conector Lioren (Futuro)
**Prioridad:** BAJA  
**Estado:** No iniciado  
**Estimación:** 4-6 horas  
**Dependencias:** Completar BoxMagic y VirtualPOS

**Tareas:**
- [ ] Obtener credenciales de Lioren
- [ ] Analizar sitio web de Lioren
- [ ] Desarrollar estrategia de scraping
- [ ] Implementar conector
- [ ] Integrar con pipeline ETL

---

### 11. Conector Banco (Futuro)
**Prioridad:** BAJA  
**Estado:** No iniciado  
**Estimación:** 6-8 horas  
**Dependencias:** Completar conectores principales

**Tareas:**
- [ ] Identificar banco y tipo de acceso
- [ ] Evaluar API bancaria vs scraping
- [ ] Desarrollar conector
- [ ] Implementar lógica de reconciliación bancaria
- [ ] Integrar con pipeline ETL

---

## 🎯 HITOS PRINCIPALES

### Hito 1: Conectores Funcionales (PRÓXIMO)
**Fecha objetivo:** Esta semana  
**Criterio de éxito:**
- ✅ BoxMagic descarga CSV automáticamente
- ⏳ VirtualPOS descarga reportes automáticamente

### Hito 2: Pipeline de Datos Completo
**Fecha objetivo:** Próxima semana  
**Criterio de éxito:**
- Datos de BoxMagic y VirtualPOS se cargan automáticamente en PostgreSQL
- Sistema detecta y evita duplicados
- Logs de ejecución disponibles

### Hito 3: Sistema Automatizado
**Fecha objetivo:** En 2 semanas  
**Criterio de éxito:**
- Sincronización diaria automática funcionando
- Dashboard básico operativo
- Documentación completa

---

## 📊 MÉTRICAS DE PROGRESO

**Progreso General:** 45% completado

- ✅ Análisis y Diseño: 100%
- ✅ Configuración: 100%
- ✅ BoxMagic: 100%
- ✅ VirtualPOS (Login): 100%
- ⏳ VirtualPOS (Descarga): 0%
- ⏳ Integración BD: 0%
- ⏳ Automatización: 0%
- ⏳ Dashboard: 0%

---

## 🔧 PRÓXIMOS PASOS INMEDIATOS

1. **HOY:** Completar descarga de reportes de VirtualPOS
2. **MAÑANA:** Iniciar integración con PostgreSQL
3. **Esta semana:** Completar pipeline ETL básico
4. **Próxima semana:** Implementar automatización y dashboard

---

## 📝 NOTAS TÉCNICAS

### Archivos Clave Creados:
- `boxmagic_downloader.py` - Descargador de BoxMagic (PRODUCCIÓN)
- `test_vpos_login.py` - Login de VirtualPOS (PRUEBA)
- `.env` - Credenciales (SEGURO)
- `schema.sql` - Esquema de base de datos

### Dependencias Instaladas:
- `playwright` - Automatización de navegador
- `python-dotenv` - Gestión de variables de entorno
- `psycopg2` - Conexión a PostgreSQL (pendiente uso)

### Credenciales Configuradas:
- ✅ BoxMagic (Cookie de sesión)
- ✅ VirtualPOS (Usuario/Contraseña)
- ✅ PostgreSQL (Base de datos local)

---

**Última actualización:** 23 de enero de 2026, 15:14
**Responsable:** Agente Antigravity
**Cliente:** The Boos Box
