# Implementación del PLAN V2 — 3.0.0

Fecha: 30 de septiembre de 2026 (rc.1) y 1 de octubre de 2026 (rc.2 y 3.0.0). Base:
`main`, commit `74a3ff3` (2.7.0). Rama: `feature/instalador-v2-seguro`.

## Revisión de la rc.1 y correcciones de la rc.2

| Problema en la rc.1 | Corrección en la rc.2 |
|---|---|
| El README reemplazaba al de `main` y perdía logo, insignias, botón de descarga, Discord y YouTube | Se parte del README de `main` y se suman las novedades de la versión 3 |
| `\| Out-Host` redirigía la salida de Python y `progreso.ps1`: sin barra en vivo y mensajes retenidos | `Invoke-Console` lanza los procesos heredando la consola |
| El recomendado instalaba solo Manager, Cine con IA y VideoHelperSuite, sin SageAttention | Mismo conjunto que las respuestas por defecto de 2.7.0, sin preguntas |
| Nodos en commit suelto (`checkout --detach`): `git pull --ff-only` del actualizador fallaba | Clon `--filter=blob:none` y `reset --hard <commit>` sobre la rama; Cine con IA sigue su rama |
| `7zr.exe` con hash fijo en una URL sin versión | Release 26.03 de `ip7z/7zip` en GitHub, mismo SHA-256 |
| Errores como códigos en inglés | `setup.error.<CÓDIGO>` en español e inglés, con la solución; el código sigue visible |
| Sin avisos de OneDrive ni de tildes y eñes; paquete de 2 GB sin borrar | `PATH_ONEDRIVE`, `PATH_NON_ASCII`; caché en el disco de destino, eliminada tras extraer |
| Diálogo de carpeta obligatorio; carpeta ocupada cerraba el instalador | Propuesta en el SSD con más espacio, Enter acepta, nombres `ComfyUI-2`...; un rechazo permite elegir otra |
| "Usar mi instalación" preguntaba cuál, sin efecto | Solo se pregunta cuál al reconfigurar |
| Driver anterior al 580: CUDA 12.6 sin aviso | Aviso con la página de NVIDIA; en avanzado, opción de salir para actualizar |
| La prueba de escritura escribía un archivo en la carpeta padre: falla en `C:\` sin administrador | Se prueba dentro de la carpeta nueva y se borra lo creado |
| Acceso "ComfyUI - CineConIA V2" y carpeta "-V2" | Acceso **ComfyUI** (o **ComfyUI (2)**), sin marca del canal, como en 2.x |
| La búsqueda saltaba OneDrive por ser punto de reanálisis | Solo se evitan `Junction` y `SymbolicLink` (`LinkType`) |
| "CONFIRMAR" también en inglés; perfiles de VRAM repetidos | "CONFIRM" en inglés; una recomendación por perfil |
| 19 archivos con CRLF en el índice | `* text=auto` y LF normalizado |

El [plan original](PLAN_V2.md) se conserva como contexto histórico. Su indicación de no implementar todavía fue sustituida por la autorización posterior del propietario para construir y probar esta nueva rama. Tras probar la rc.2 en su equipo, el propietario autorizó el 1 de octubre de 2026 fusionarla en `main` y publicarla como 3.0.0.

## Auditoría y decisión de arquitectura

La base ya tenía Python embebido, selección de portables por GPU, protección de PyTorch, instalación de nodos, migración con simulación y SHA-256, logs, progreso y prueba de arranque. Las 69 pruebas de la base pasaron antes de editar.

Faltaban detección de instalaciones antes de descargar, selector gráfico para la instalación, límites estrictos sobre destinos, catálogo externo fijado, flujo recomendado sin preguntas técnicas, Git local automático, diagnóstico ampliado y estados de instalación.

Se mantiene Python para configuración y migración. Un bootstrap PowerShell 5.1 sustituye la lógica extensa del BAT, porque Windows ya lo incluye y debe funcionar sin Python global. El BAT solo lo invoca con rutas entre comillas y expansión retardada desactivada. Reescribir todo en PowerShell o crear una aplicación gráfica completa añadiría una segunda implementación de lógica ya probada, sin mejorar este flujo.

La V2 conceptual se numera **3.0.0-rc.1** (y rc.2 tras la revisión), porque el proyecto ya publicó 2.7.0. Se desarrolló en una rama candidata y se publicó como 3.0.0 después de la revisión y la prueba del propietario.

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
| RF-21 y RF-22 | Destino propuesto (SSD con más espacio) o selector nativo, cancelación segura, prueba de escritura, tipo de disco, espacio mínimo, OneDrive y caracteres no ASCII |
| RF-23 y RF-24 | Portable fijado, extracción en staging, nodos de terceros fijados por commit sobre su rama; recomendado igual a los valores por defecto de 2.7.0 y avanzado con grupos |
| RF-25 y RF-26 | Migrador anterior conservado con simulación, espacio, copia verificada y consentimiento separado para mover |
| RF-27 | Reutilización mediante YAML respaldado; avanzado permite varias bibliotecas |
| RF-28 y RF-29 | Progreso existente, transcript de bootstrap, registros fechados y estado JSON |
| RF-30 | ComfyUI `--quick-test-for-ci`, carga de nodos, operación real GPU y evaluación de conflictos |

## Decisiones de producto

- El modo recomendado instala, sin preguntar, lo que 2.7.0 instalaba aceptando cada respuesta por defecto: Manager clásico, Cine con IA, monitor, nodos de video, extras de interfaz y SageAttention en NVIDIA (solo recibe el acceso si supera la prueba en GPU). Los workflows del canal necesitan los nodos de video; los nodos de la comunidad, más pesados, siguen en avanzado.
- Las versiones base no siguen `latest`: el portable, 7-Zip y MinGit tienen URL con versión y hash, y los nodos de terceros tienen commit. Los nodos Cine con IA (`version: null`) siguen su rama: son del propio proyecto y cambian con los workflows del canal. Las dependencias transitivas de nodos siguen sus requirements, restringiendo el conjunto PyTorch; el resultado instalado se registra con `pip freeze`.
- Un commit fijado no impide actualizar: el nodo queda sobre su rama y los actualizadores avanzan con `git pull --ff-only`.
- Los perfiles AMD, Intel y NVIDIA antigua conservan soporte de selección y comprobación, con estado candidato hasta probarlos físicamente. No se marca una combinación como validada solo porque exista una descarga.
- La detección tiene límites de tiempo y profundidad; el modo avanzado incluye selección manual.
- Reutilizar una instalación manual significa conservarla y usar su lanzador habitual. El instalador no modifica entornos que no reconoce como portable.
- El acceso se llama **ComfyUI**, como en 2.x; si ese nombre abre otra instalación, se usa **ComfyUI (2)** sin reemplazarlo.
- El destino se propone en el SSD con más espacio libre para que la instalación recomendada solo pida Enter. Un destino rechazado explica el motivo y permite elegir otro.
- Las rutas para modelos y outputs pueden estar en discos diferentes. La selección de outputs se conserva en el estado y se incorpora a los lanzadores.

## Recuperación

Una descarga parcial se reanuda y siempre se verifica completa. Un hash incorrecto se conserva con sufijo `.invalid-*` y no se ejecuta. Una extracción fallida queda en `.cineconia-stage-*`, fuera del destino definitivo. Una carpeta ocupada nunca se renombra ni se elimina automáticamente.

Un portable cuya configuración se interrumpió puede seleccionarse en avanzado y reconfigurarse después de autorizarlo. El estado registra `base_ready`, `configuring`, `verified`, `needs_attention` o `interrupted`. No se elimina la instalación fallida. La protección de PyTorch permanece; no hay promesa de rollback universal de todas las dependencias.

## Fuera de la versión 3.0.0

No incluye actualización de drivers, Linux/macOS, descargas de modelos, marketplace, conversión automática de instalaciones manuales, reparación universal ni ejecución de cada workflow/modelo existente. La validación física de otras GPU y la selección visual manual del diálogo son parte de la aceptación antes de publicar estable.
