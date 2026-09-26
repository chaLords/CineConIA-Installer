# Changelog

## v2.2.2 — 2026-09-26

- La eleccion de CUDA pasa a ser una lista como las demas preguntas: CUDA 13 (la mas usada, ~84 % de las descargas NVIDIA del portable oficial) y CUDA 12.6, con la recomendada marcada; Enter la acepta. Reemplaza la cuenta atras de 10 segundos con la tecla C.
- Lo que la tarjeta no soporta aparece como "(no compatible con tu tarjeta)" y, si se elige, se mantiene la recomendada.

## v2.2.1 — 2026-09-25

- El grupo "nodos para video" instala tambien el escalador latente de H3 (LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler). Sin el, "Escalar y refinar" de Cine con IA no subia la resolucion: el video salia del tamano del primer pase.
- En una instalacion ya hecha, volver a ejecutar ComfyUI-Setup.bat ofrece instalar solo lo que falte.

## v2.2.0 — 2026-09-25

- Eleccion de CUDA en NVIDIA. Antes de descargar se muestra la version recomendada (CUDA 13 con Python 3.13, o CUDA 12.6 con Python 3.12) y hay 10 segundos para cambiarla con la tecla C. Tambien se puede fijar con --cuda 13 o --cuda 12.6.
- Protecciones: CUDA 13 no se instala en tarjetas con compute capability menor a 7.5 (serie 10 y anteriores), y CUDA 12.6 no se instala en la serie 50 (compute capability 10.0 o mas), que solo funciona con CUDA 13. Si no se puede leer la compute capability, se respeta la eleccion con un aviso.
- Tarjeta moderna con driver anterior al 580: ya no se baja a CUDA 12.6 sin preguntar. Se recomienda actualizar el driver (abre https://www.nvidia.com/drivers y cierra el instalador) y se puede elegir instalar CUDA 13 igual o CUDA 12.6 con el driver actual.
- El instalador muestra la version del driver NVIDIA detectado.

## v2.1.1 — 2026-09-24

- Boton de descarga en el README: baja CineConIA-Installer.zip de la ultima Release, solo con lo necesario para instalar (los .bat, src/, assets/ y LICENSE).
- Los avisos de terceros pasan a assets/THIRD_PARTY_NOTICES.md, junto al icono al que dan credito: en la raiz del ZIP solo quedan los .bat y LICENSE.
- Logo de Cine con IA con el icono de ComfyUI en la cabecera del README, y la aclaracion de que el proyecto es independiente y no esta afiliado a Comfy Org.
- GitHub Actions arma ese ZIP y lo sube a la Release cada vez que se publica una etiqueta vX.Y.Z. Tambien se puede lanzar a mano desde la pestaña Actions, por ejemplo para agregarlo a la v2.1.0.
- El "Download ZIP" del boton verde Code tambien deja fuera README, CHANGELOG y .github.

## v2.1.0 — 2026-09-22

- ComfyUI-Manager clasico: se instala como nodo en custom_nodes/comfyui-manager y los lanzadores ya no usan --enable-manager. El Manager integrado de ComfyUI 4.x con legacy UI crea el boton "Manager" pero no lo coloca en la barra de la interfaz actual, y el flag desactiva el clasico. Resultado: el boton "Manager" de siempre, como en los tutoriales.
- Sin Git se recurre al Manager integrado para no dejar al usuario sin Manager.
- Actualizar ComfyUI y nodos usa primero el cm-cli del Manager clasico.
- FlashAttention para PyTorch recientes: se busca tambien en mjun0812/flash-attention-prebuild-wheels (2.13, 2.14...). Se descartan las wheels "free-threaded" (cp313t) y se revisan hasta 100 releases por repositorio.
- Nunchaku opcional: si PyTorch es mas nuevo que el ultimo soportado, ofrece cambiarlo a esa rama con la misma CUDA (2.13 -> 2.11 con CUDA 13), guardando antes un pip freeze y volviendo atras solo si algo deja de cargar. Instala tambien el nodo ComfyUI-nunchaku. Probado: Triton 3.6, Sage, FlashAttention y Nunchaku pasan la prueba en GPU y ComfyUI carga 1324 nodos sin errores.
- Proteccion de PyTorch: antes de cada extra o nodo se anota la version y, si un requirements.txt la cambia, se restaura.
- Requisitos de nodos tolerantes a fallos: si el -r falla por un paquete, se instalan los demas uno por uno y se avisa del que falto.
- Grupo "nodos para video" con una sola pregunta: KJNodes, VideoHelperSuite, ComfyUI-GGUF y SelfLift.
- pip check al final, con los conflictos en el resumen.
- Icono del acceso directo: logo actual de ComfyUI (azul con la C amarilla), incluido en assets/ComfyUI.ico en vez de descargar el favicon antiguo.

## v2.0.0 — 2026-09-22

Primera version publicada del instalador adaptativo.

### Base adaptativa (2026-09-21)

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
- Triton se elige leyendo la version que el propio PyTorch declara en PyPI (2.11 → 3.6, 2.13 → 3.7...), con una tabla de respaldo. Una formula fija fallaba desde PyTorch 2.11.
- El Python embebido del portable no trae include/ ni libs/: Triton se importaba pero no podia compilar ningun kernel, y SageAttention fallaba. El instalador las descarga de triton-windows cuando hay Triton.
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

#### Prueba real en el equipo del autor (2026-09-22)
- Idioma automatico: sin pregunta inicial. Espanol si la interfaz o el formato regional de Windows estan en espanol.
- --lang=en nunca funcionaba: cmd separa argumentos en "=". Ahora se aceptan --lang en y --lang=en.
- Opcion de monitor de recursos (ComfyUI-Crystools), verificada con ComfyUI 0.37 y RTX 4060 Ti.
- El paso de modelos del instalador ofrece tres caminos: usarlos donde estan, llevarlos a una biblioteca central con el migrador o no hacer nada. Al migrar desde el instalador, el ComfyUI nuevo tambien queda enlazado.
- La biblioteca central aparece primera y marcada en instalaciones futuras.
- Las bibliotecas de menos de 50 MB ya no se descartan por redondeo.
