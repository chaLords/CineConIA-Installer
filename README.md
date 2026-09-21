# CineConIA Installer — instalador adaptativo de ComfyUI

Esta rama contiene la nueva arquitectura del instalador. La meta es que una
persona pueda ejecutar un solo BAT y que la instalacion se adapte al equipo
real, sin tener que conocer CUDA, ROCm, XPU, PyTorch o wheels.

## Inicio rapido

1. Descarga/descomprime el repositorio.
2. Ejecuta **Instalar-ComfyUI.bat**.
3. Usa la configuracion automatica recomendada o entra al modo avanzado.

Al terminar queda un unico acceso directo llamado **ComfyUI** en el escritorio.
No se crean accesos al canal, launchers promocionales ni branding de Cine con IA.

## Como decide la instalacion

### Antes de descargar

- Detecta NVIDIA, AMD o Intel.
- NVIDIA moderno usa el portable oficial NVIDIA por defecto.
- NVIDIA antiguo/driver previo a CUDA 13 usa el portable oficial nvidia_cu126.
- AMD usa el portable AMD/ROCm oficial.
- Intel usa el portable Intel XPU oficial.
- Comprueba espacio libre, curl y PowerShell.

### Descarga robusta

- curl --fail para no confundir un 404/500 con una descarga correcta.
- Reintentos automaticos.
- Archivos grandes se descargan primero como .part.
- El .7z de ComfyUI se compara con el SHA-256 que publica GitHub cuando existe.
- Si GitHub no entrega digest, se hace al menos una prueba de integridad con 7-Zip.
- Una instalacion parcial previa se conserva como respaldo antes de reinstalar.

### Despues de instalar ComfyUI

El instalador ejecuta el **python_embeded del portable** y detecta lo que
realmente quedo instalado:

- Python.
- PyTorch.
- CUDA real / ROCm-HIP / Intel XPU.
- GPU que PyTorch reconoce.
- VRAM.
- Compute capability cuando corresponde.

Desde ese momento no se “elige CUDA” por intuicion. Los aceleradores se
resuelven contra la combinacion que **realmente quedo instalada**.

## Aceleradores

### Configuracion automatica

En NVIDIA intenta SageAttention solo cuando encuentra una wheel que coincide con
la rama real de PyTorch, CUDA y Python. Triton se instala solo si existe una
regla conocida para esa rama de PyTorch.

En AMD e Intel se conserva el backend oficial del portable y no se entra en la
logica CUDA de NVIDIA.

### Modo avanzado

Permite seleccionar, cuando el equipo lo soporta:

- SageAttention.
- FlashAttention.
- Nunchaku.
- InsightFace / ONNX Runtime.

Un pip install exitoso no basta: el modulo se importa en un proceso separado.
Si el import falla, el componente no se considera operativo y no se crea su BAT.

## Lanzadores generados

Dentro de la carpeta instalada de ComfyUI pueden aparecer:

- Iniciar-ComfyUI.bat
- Iniciar-ComfyUI-Kitchen.bat (si Comfy Kitchen esta disponible)
- Iniciar-ComfyUI-SageAttention.bat (solo si Sage fue verificado)
- Iniciar-ComfyUI-FlashAttention.bat (solo si Flash fue verificado)
- Iniciar-ComfyUI-DynamicVRAM.bat (AMD)
- Actualizar-ComfyUI.bat
- Actualizar-ComfyUI-y-Nodos.bat

Los lanzadores comprueban el puerto 8188. Si ComfyUI ya esta abierto, se abre
la interfaz existente en vez de iniciar otra instancia.

## Acceso directo de escritorio

Se crea **un solo acceso**: ComfyUI.

Apunta al mejor lanzador verificado:
1. SageAttention, si realmente funciona.
2. Comfy Kitchen, si esta disponible.
3. Lanzador base como fallback.

El instalador intenta usar el favicon.ico del repositorio oficial
Comfy-Org/docs. Si no puede descargarlo, no sustituye el icono por branding
del canal.

## Git y nodos

Git se comprueba antes de clonar nodos. Si falta y winget esta disponible,
el instalador pregunta si quieres instalar Git for Windows.

Luego ofrece instalar:
https://github.com/chaLords/ComfyUI-Cine-con-IA

## Modelos

El instalador **no descarga modelos**.

Opcionalmente puede buscar otra instalacion de ComfyUI y crear
extra_model_paths.yaml para reutilizar modelos existentes sin copiarlos.

La busqueda:
- tiene limite de profundidad;
- tiene limite de directorios recorridos;
- tiene limite de resultados;
- no sobrescribe un extra_model_paths.yaml que ya exista.

## Filosofia de compatibilidad

Compatible -> instalar y verificar.
Dudoso -> omitir.
No compatible -> usar fallback.

El objetivo es que un extra opcional nunca rompa una instalacion base funcional.

## Licencia

El instalador es MIT. ComfyUI y todos los componentes externos conservan sus
propias licencias. Consulta THIRD_PARTY_NOTICES.md.
