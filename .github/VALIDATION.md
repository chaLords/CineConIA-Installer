# Validación de v2.5.0

Fecha: 26 de septiembre de 2026.

## Prueba real de instalación

- Portable oficial ComfyUI v0.37.0 NVIDIA, descargado en una carpeta de pruebas nueva.
- Archivo de origen verificado con el SHA-256 publicado por Comfy Org.
- Windows 11, RTX 4060 Ti de 16 GB, driver 616.92.
- Python 3.13.14, PyTorch 2.13.0+cu130, CUDA 13.0.
- Se instalaron y cargaron los 14 paquetes: Manager, Cine con IA, Crystools,
  KJNodes, VideoHelperSuite, GGUF, SelfLift, H3 Latent Upscaler, rgthree,
  Custom-Scripts, Essentials, Comfyroll, WAS y ControlNet Aux.
- Triton y SageAttention instalados; SageAttention superó una operación real
  de atención en la GPU. ONNX Runtime también se importó correctamente.
- ComfyUI superó el arranque de comprobación. Se verificó el resumen de
  importaciones de los 14 paquetes; los tiempos de prestartup no cuentan como
  carga de un nodo.
- `pip check` sin conflictos relevantes. Se conservó el PyTorch del portable.
- Segunda ejecución del orquestador completada con código 0: los 14 paquetes
  preparados, sin cambios en torch, torchvision ni torchaudio. En esa prueba se
  suprimieron solamente la búsqueda de modelos del usuario y el acceso de escritorio.
- La prueba no generó imágenes/videos ni descargó modelos para ejecutarlos.

## Pruebas automáticas

La suite de 41 pruebas `python -B -m unittest discover -s tests -v` cubre:

- Dependencias fallidas, carpetas incompletas y reejecución del instalador.
- Restricciones de PyTorch y recuperación fallida tras cambiar de versión.
- Comprobación de arranque, errores de importación y tiempo límite.
- Copia y movimiento con archivos de prueba: duplicados, conflictos, fallo de
  una segunda copia, destino alterado y fallo al guardar el reporte.
- Ningún original eliminado si falla la fase de copia/verificación; verificación
  de toda la operación antes de comenzar las eliminaciones.
- Biblioteca recordada fuera de la profundidad de búsqueda, disco no disponible
  y dos ComfyUI enlazados sin duplicar archivos ni perder otras configuraciones.
- Idiomas, parámetros de traducción y saltos de línea de los BAT.

GitHub Actions ejecuta la suite en Windows con Python 3.12 y 3.13.
El ZIP de distribución se inspecciona aparte: solo archivos de ejecución,
icono y licencias; sin README, diagramas, pruebas ni configuración de GitHub.

## Alcance y pendientes

- No se realizaron pruebas físicas en AMD/ROCm, Intel/XPU ni NVIDIA antigua/CUDA 12.6.
- Nunchaku es opcional. Al revisar los releases no había wheel para
  PyTorch 2.13 + CUDA 13 + Python 3.13; había wheels para PyTorch 2.9, 2.10 y
  2.11. No se validó su cambio de versión ni una inferencia Nunchaku real.
- Tampoco se ejecutaron los perfiles avanzados FlashAttention e InsightFace.
- Cargar un paquete no garantiza todos sus workflows, modelos o funciones.
- Los nodos y los portables se descargan de proyectos externos que pueden cambiar.
