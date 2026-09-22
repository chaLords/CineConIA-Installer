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


### Bilingual interface
- Added automatic Windows language detection for Spanish and English.
- Added a manual language switch at startup.
- Added neutral entry points ComfyUI-Setup.bat and ComfyUI-Model-Migrator.bat.
- Kept the Spanish BAT names as compatibility aliases.
- Added JSON locale files under src/locales and a reusable src/i18n.py layer.
- Installer, migrator, compatibility warnings, generated launchers and update launchers now follow the selected language.
- Added README.en.md and language links in both READMEs.
- Language can be forced with --lang=es or --lang=en.


### Revision de la v2 — 2026-09-22

#### Correcciones
- src/catalogo.py tenia un error de sintaxis: el instalador descargaba y extraia ComfyUI y luego se cerraba al iniciar la parte Python.
- Actualizar-ComfyUI.bat llamaba a update_comfyui.bat desde la carpeta raiz; el script oficial usa rutas ..\ relativas y fallaba. Ahora entra en update\ y usa la version estable.
- El chequeo de espacio leia "9,5" GB como 95 en Windows en espanol. Ahora compara GB enteros.
- Los avisos "[!]" del BAT se imprimian mal con delayed expansion (por ejemplo "[T_NO_DIGEST").
- Los .bat se guardaban con saltos LF; cmd.exe falla con call/goto en esos archivos. .gitattributes fuerza CRLF, tambien en el ZIP de GitHub.
- Los lanzadores generados no activaban UTF-8 y las tildes salian corruptas.
- La verificacion SHA-256 nunca funcionaba: el "^|" dentro de las comillas de PowerShell llegaba literal y fallaba, asi que siempre se usaba la prueba de 7-Zip (una descompresion completa extra).
- Por el mismo motivo, la deteccion de GPU AMD/Intel sin nvidia-smi siempre terminaba en la pregunta manual.
- La extraccion y la prueba de 7-Zip muestran porcentaje de avance en vez de parecer congeladas.
- i18n no reconocia "Spanish_Chile" (locale de Windows) como espanol y relanzaba PowerShell en cada texto.

#### Deteccion
- NVIDIA antiguo se decide por compute capability (< 7.5 → nvidia_cu126), con lista ampliada de nombres como respaldo (GTX 9xx/7xx, TITAN V, Quadro M...).
- Aviso cuando el driver es el motivo del fallback, y cuando es tan antiguo que PyTorch podria no ver la GPU.
- Aviso si PyTorch no puede usar la GPU tras instalar, en vez de seguir con una instalacion solo CPU.
- Comprobacion de Visual C++ Redistributable (error c10.dll) con instalacion opcional por winget.
- Avisos de carpeta dentro de OneDrive y de rutas con tildes o enes. Espacio minimo realista: 15 GB.

#### Aceleradores
- Se aceptan las wheels "torchX.Y.0andhigher" de SageAttention; antes no se encontraba ninguna wheel para PyTorch 2.11+.
- Regla de Triton PyTorch 2.N → Triton 3.(N-4), aplicada solo si esa rama esta publicada en PyPI.
- SageAttention y FlashAttention se verifican ejecutando atencion real en la GPU, no solo con import.
- Repetir el instalador vuelve a verificar lo ya instalado: el acceso directo no se degrada.
- Se quitaron los perfiles H3/Wan/LTX del modo avanzado: no instalaban nada.
- Comfy Kitchen solo se elige para el acceso directo en NVIDIA.

#### ComfyUI y lanzadores
- Oferta de ComfyUI-Manager (--enable-manager) cuando la version de ComfyUI lo soporta.
- Los flags solo se escriben si existen en comfy/cli_args.py de esa version.
- Actualizar ComfyUI y nodos guarda antes un snapshot del Manager.
- La descarga del portable se reanuda si se corta, y el .7z se borra tras extraer (~2 GB).

#### Modelos
- El instalador busca modelos anteriores automaticamente y solo pregunta si encuentra algo.
- Busqueda en todos los discos locales fijos, no solo C:, D: y E:.
- Reconoce bibliotecas A1111 / Forge (Stable-diffusion, Lora, LyCORIS, ESRGAN...).
- Instalador y migrador escriben el mismo bloque administrado en extra_model_paths.yaml, con copia .bak.
- El migrador en modo mover renombra en el mismo disco: instantaneo y sin espacio extra.
- El migrador ignora los marcadores put_*_here del portable.
