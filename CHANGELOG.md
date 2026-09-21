# Changelog

## v2 adaptativa — 2026-09-21

### Hardware y portable
- Deteccion NVIDIA/AMD/Intel.
- Seleccion del portable oficial por fabricante.
- Fallback NVIDIA nvidia_cu126 para drivers/arquitecturas antiguas.

### Entorno real
- Deteccion posterior de Python, PyTorch, CUDA, ROCm/HIP, Intel XPU, VRAM y GPU.
- Extras resueltos contra ese entorno real, no contra una CUDA supuesta.

### Aceleradores
- SageAttention solo si existe wheel exacta y el import funciona.
- Triton solo con reglas conocidas por rama de PyTorch.
- FlashAttention y Nunchaku en modo avanzado.
- Fallos opcionales no rompen ComfyUI base.

### Lanzadores
- BAT base.
- BAT Kitchen, Sage y Flash solo cuando aplican.
- BAT Dynamic VRAM para AMD.
- BAT de actualizacion de ComfyUI y ComfyUI + nodos.
- Control de puerto 8188.

### Escritorio
- Un unico acceso llamado ComfyUI.
- Sin branding promocional.
- Apunta al mejor backend verificado.
- Intenta usar icono oficial de Comfy-Org/docs.

### Robustez
- curl --fail, reintentos y descargas .part.
- Verificacion SHA-256 del release cuando GitHub publica digest.
- Prueba 7-Zip como fallback.
- Recuperacion de carpetas de instalacion incompletas.
- Deteccion/instalacion opcional de Git mediante winget.
- Busqueda de modelos con limites y calculo recursivo de tamano.


### Migrador seguro de modelos existentes
- Añadido Migrar-Modelos-ComfyUI.bat y src/migrar_modelos.py.
- Puede consolidar una o varias bibliotecas.
- Simula todo antes de modificar archivos y exige la confirmacion MIGRAR.
- Ofrece copiar o mover mediante copia + SHA-256 + borrado posterior.
- Detecta duplicados exactos y conserva conflictos sin sobrescribir.
- Mueve elementos no clasificables a _sin_clasificar.
- Puede actualizar extra_model_paths.yaml creando antes una copia de seguridad.
- Genera un reporte JSON de cada migracion.
