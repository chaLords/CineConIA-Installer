# Implementación del PLAN V2 — 3.0.0-rc.1

Fecha: 30 de septiembre de 2026. Base: `main`, commit `74a3ff3` (2.7.0).
Rama: `feature/instalador-v2-seguro`.

El [plan original](PLAN_V2.md) se conserva como contexto histórico. Su indicación de no implementar todavía fue sustituida por la autorización posterior del propietario para construir y probar esta nueva rama. No se autoriza desde esta rama fusionar ni publicar una release estable.

## Auditoría y decisión de arquitectura

La base ya tenía Python embebido, selección de portables por GPU, protección de PyTorch, instalación de nodos, migración con simulación y SHA-256, logs, progreso y prueba de arranque. Las 69 pruebas de la base pasaron antes de editar.

Faltaban detección de instalaciones antes de descargar, selector gráfico para la instalación, límites estrictos sobre destinos, catálogo externo fijado, flujo recomendado sin preguntas técnicas, Git local automático, diagnóstico ampliado y estados de instalación.

Se mantiene Python para configuración y migración. Un bootstrap PowerShell 5.1 sustituye la lógica extensa del BAT, porque Windows ya lo incluye y debe funcionar sin Python global. El BAT solo lo invoca con rutas entre comillas y expansión retardada desactivada. Reescribir todo en PowerShell o crear una aplicación gráfica completa añadiría una segunda implementación de lógica ya probada, sin mejorar este flujo.

La V2 conceptual se numera **3.0.0-rc.1**, porque el proyecto ya publicó 2.7.0. Se implementa una rama candidata, no una sustitución de la release estable.

## Cobertura de requisitos

| Requisitos | Implementación |
|---|---|
| RF-01 | Idioma de interfaz/región de Windows, español o inglés; `--lang` opcional |
| RF-02 a RF-09 | Diagnóstico PowerShell antes de descargas; Windows x64, CPU, RAM, GPU, VRAM, driver, compute y PCIe; datos no disponibles explícitos |
| RF-10 | `hardware_profiles.json`: <8, 8, 12, 16, 24, 32, 48 y ≥64 GB, con recomendaciones |
| RF-11 y RF-12 | Detecta Python global solo como dato; usa el Python embebido del portable fijado |
| RF-13 y RF-14 | Detecta Git o descarga MinGit local con versión y SHA-256; PATH solo del proceso y lanzadores |
| RF-15 y RF-16 | PyTorch/runtime del paquete oficial fijado; verificación de matriz, protección de versiones y operación FP16 en GPU |
| RF-17 y RF-18 | Busca instalaciones con y sin modelos antes de instalar; bloquea destinos ocupados, solapamientos y reparse points; consentimiento para configurar un portable existente |
| RF-19 y RF-20 | Conservar instalación sin cambios o crear una independiente; mantenimiento de portable con confirmación explícita |
| RF-21 y RF-22 | Selector nativo, cancelación segura, prueba de escritura, tipo de disco y espacio mínimo |
| RF-23 y RF-24 | Portable fijado, extracción en staging, nodos fijados por commit; recomendado pequeño y avanzado con grupos |
| RF-25 y RF-26 | Migrador anterior conservado con simulación, espacio, copia verificada y consentimiento separado para mover |
| RF-27 | Reutilización mediante YAML respaldado; avanzado permite varias bibliotecas |
| RF-28 y RF-29 | Progreso existente, transcript de bootstrap, registros fechados y estado JSON |
| RF-30 | ComfyUI `--quick-test-for-ci`, carga de nodos, operación real GPU y evaluación de conflictos |

## Decisiones de producto

- El modo recomendado instala Manager clásico, Cine con IA y VideoHelperSuite. Los otros nodos y aceleradores continúan en avanzado. Esto evita añadir requisitos pesados sin necesidad al primer arranque.
- Las versiones base no siguen `latest`: el portable y MinGit tienen URL/hash, y los nodos tienen commit. Las dependencias transitivas de nodos siguen sus requirements, restringiendo el conjunto PyTorch; el resultado instalado se registra con `pip freeze`.
- Los perfiles AMD, Intel y NVIDIA antigua conservan soporte de selección y comprobación, con estado candidato hasta probarlos físicamente. No se marca una combinación como validada solo porque exista una descarga.
- La detección tiene límites de tiempo y profundidad; el modo avanzado incluye selección manual.
- Reutilizar una instalación manual significa conservarla y usar su lanzador habitual. El instalador no modifica entornos que no reconoce como portable.
- Los accesos nuevos usan nombre independiente y resuelven colisiones sin reemplazar accesos de otros portables.
- Las rutas para modelos y outputs pueden estar en discos diferentes. La selección de outputs se conserva en el estado y se incorpora a los lanzadores.

## Recuperación

Una descarga parcial se reanuda y siempre se verifica completa. Un hash incorrecto se conserva con sufijo `.invalid-*` y no se ejecuta. Una extracción fallida queda en `.cineconia-stage-*`, fuera del destino definitivo. Una carpeta ocupada nunca se renombra ni se elimina automáticamente.

Un portable cuya configuración se interrumpió puede seleccionarse en avanzado y reconfigurarse después de autorizarlo. El estado registra `base_ready`, `configuring`, `verified`, `needs_attention` o `interrupted`. No se elimina la instalación fallida. La protección de PyTorch permanece; no hay promesa de rollback universal de todas las dependencias.

## Fuera de esta candidata

No incluye actualización de drivers, Linux/macOS, descargas de modelos, marketplace, conversión automática de instalaciones manuales, reparación universal ni ejecución de cada workflow/modelo existente. La validación física de otras GPU y la selección visual manual del diálogo son parte de la aceptación antes de publicar estable.
