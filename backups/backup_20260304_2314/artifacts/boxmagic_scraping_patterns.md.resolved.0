# Patrones Expertos de Scraping: BoxMagic

Durante la optimización del proceso de sincronización de BoxMagic para "ERP The Boos Box", se han identificado los siguientes patrones y mejores prácticas para garantizar un scraping robusto, rápido y seguro.

## 1. Persistencia de Sesión (Storage State)
BoxMagic utiliza un flujo de autenticación basado en cookies y tokens que pueden ser persistidos.
- **Implementación**: Usar `context.storage_state(path=...)` de Playwright para guardar el estado tras el primer login.
- **Validación**: Al iniciar una nueva tarea, cargar el estado y navegar a una página protegida (ej. reportes). Si el sistema redirige a `auth.boxmagic.cl`, se dispara un re-login automático.
- **Beneficio**: Reduce el tiempo de ejecución en un ~70% y minimiza el riesgo de bloqueos por logins repetitivos.

## 2. Navegación Directa por Parámetros (Deep-Links)
Las interacciones con el `daterangepicker` de la UI son propensas a fallos debido a overlays y tiempos de carga de scripts externos (jQuery).
- **Patrón**: Construir la URL de reportes directamente con parámetros ISO:
  `https://boxmagic.cl/reportes/reportes_pagos?fecha_desde=YYYY-MM-DD&fecha_hasta=YYYY-MM-DD`
- **Aprendizaje**: Esto fuerza al servidor a renderizar la tabla con el filtro aplicado, eliminando la necesidad de interactuar con calendarios visuales.

## 3. Cambio de Sede Instantáneo
El menú lateral de cambio de sede puede ser inconsistente o estar oculto tras un menú "hamburguesa" en resoluciones bajas.
- **Patrón**: Navegar directamente al endpoint de selección:
  - **Campanario**: `https://boxmagic.cl/choose_box/R7XLbnaLV5`
  - **Marina**: `https://boxmagic.cl/choose_box/VWQDqk1489`
- **Aprendizaje**: Estos IDs (`R7XLbnaLV5`, `VWQDqk1489`) son constantes y permiten cambiar el contexto de la sesión de forma atómica.

## 4. Gestión de Pantallas Intermedias
Tras el login (o al expirar parcialmente la sesión), BoxMagic a veces muestra una pantalla de selección de "Panel de administración".
- **Insight**: El scraper debe incluir un "poller" que detecte el texto "Panel de administración" y haga clic en él si está presente, antes de intentar navegar a las páginas de datos.

## 5. Extracción de Datos SSR
La tabla de pagos se renderiza en el servidor (SSR), lo que la hace ideal para `pandas.read_html()`.
- **Tip**: Antes de extraer, ejecutar un script inyectado (`page.evaluate`) para cambiar el valor del selector `_length` a "100" para capturar más registros en una sola página sin paginar.

---
*Este documento sirve como registro de conocimientos para futuras expansiones del módulo de inteligencia comercial del ERP.*
