# Resumen de Motor de Cuadratura Bancaria y Egresos (v2.0)
*Fecha: 22 de Mayo de 2026*

Este documento consolida todo el conocimiento, lógica y decisiones arquitectónicas desarrolladas para el módulo de Cuadratura Bancaria y Recursos Humanos del ERP The Boos Box.

## 1. Arquitectura de Ingesta Bancaria (Cartola BCI)
El sistema ha migrado de procesar resúmenes básicos a un **Motor de Ingesta Detallada (`process_bank_detailed.py`)**:
*   **Fuente de la verdad:** La cartola maestra en Excel (`MOVIMIENTOS 30122026A 22052027.xlsx` u otros futuros) exportada desde el banco BCI.
*   **Campos clave capturados:** El motor extrae 26 columnas del BCI, prestando especial atención a `Saldo contable`, `Monto`, `RUT`, `Nombre`, y `Glosa detalle`.
*   **Regla de Oro de Exportación:** Para evitar desfases o "agujeros" de días faltantes, **las cartolas siempre deben exportarse de corrido** (ej. semestre completo o trimestre completo) y no particionadas mes a mes, para asegurar que no se omita el día 31 o 1 del mes.

## 2. Auto-Categorización Inteligente y RRHH
Se implementó un motor que cruza automáticamente la cartola del banco con nuestra base de datos de "Sueldos Coaches" y "Personal".
*   **Coaches:** Basado en el archivo maestro de coaches (`docs/remuneraciones/sueldos_coaches.md`). Si el motor detecta una transferencia saliente a un RUT o Nombre de un coach conocido, lo clasifica como `Sueldo Coach`.
*   **Automatización de Ledger:** Crea un registro automático en la tabla `expense_ledger` con estado `PAID_VERIFIED` y vincula el UUID del ledger con el `source_bank_id` (el movimiento bancario en `raw_bank`).
*   **Otras categorías entrenadas:**
    *   VirtualPOS SpA / Lioren → "Comisiones Transaccionales"
    *   BoxMagic SpA → "Software y Licencias"

## 3. UI/UX: Dashboard de Cuadratura (`dashboard_cuadratura.py`)
Se reconstruyó la interfaz de análisis financiero (Círculos, badges y kpis).
*   **Saldo Cuenta (BCI):** Ahora el dashboard muestra directamente el último `Saldo contable` registrado en la base de datos (Ej: $5.364.786). Se eliminó la confusión matemática de mostrar solo el "Flujo Neto".
*   **Semáforo Mensual:** Los meses se marcan de color Verde (Cuadrado), Amarillo (Pendiente) o Rojo (Descuadre) dependiendo del porcentaje de movimientos huérfanos.
*   **Grilla en Vivo para Coaches:** La sección de Honorarios / RRHH cuenta con una barra tipo "badges" (Ene-Dic) que se ilumina en verde cuando el mes ya tiene honorarios registrados, y una grilla automática con totales de dinero.

## 4. Estado de Base de Datos y Limpieza
Para lograr la cuadratura perfecta de mayo 2026:
*   Se vació la tabla `raw_bank` que contenía archivos particionados con días faltantes.
*   Se inyectó el archivo `CARTOLA SEMESTRAL`.
*   **Importante:** El saldo "Real" lo dicta el campo `balance` (Saldo Contable) extraído directamente del Excel del banco. Ya no dependemos de "calcular hacia adelante" asumiendo un saldo de apertura cero.

## 5. Próximos Pasos Pendientes
*   **Centro de Conciliación Manual (MatchMaker):** Finalizar el flujo donde los 116 "movimientos huérfanos" que no son coaches (arriendos, pago de luz, etc.) puedan ser seleccionados en pantalla y atados a un egreso en el Ledger con 1 clic.
*   **Bloqueo de Periodos:** Evitar la edición de sueldos o egresos en meses donde el semáforo SAP ya está "Verde" (Cerrado).
