# Changelog

## v3.0.0 — 2026-10-01

Un instalador nuevo, pensado para que quien instala ComfyUI por primera vez solo tenga que pulsar Enter.

- Casi sin preguntas: el modo recomendado instala lo que 2.7.0 instalaba aceptando cada respuesta por defecto (Manager clásico, Cine con IA, monitor, nodos de video, extras de interfaz y SageAttention en NVIDIA). Lo opcional pasa a **ComfyUI-Advanced-Setup.bat**.
- Respeta lo que ya tienes: antes de descargar busca instalaciones de ComfyUI y nunca las modifica.
- Propone dónde instalar: `ComfyUI` en el SSD con más espacio libre, y Enter lo acepta. Si una carpeta no sirve (OneDrive, tildes o eñes, del sistema, ocupada), explica el motivo y deja elegir otra.
- Tus modelos, fuera de ComfyUI: encuentra sola la biblioteca central aunque borres ComfyUI, y si todavía no tienes modelos propone una carpeta en el disco que elijas.
- Versiones comprobadas: ComfyUI v0.38.0, 7-Zip, Git portátil y los nodos de terceros se descargan en versiones fijas con SHA-256 o commit, y se pueden actualizar después. Cine con IA llega siempre en su última versión.
- Sin instalar Git a mano: si falta, usa una copia portátil dentro de la instalación.
- Prueba real en la GPU y arranque de ComfyUI antes de dar la instalación por buena.
- Errores explicados en tu idioma, con qué hacer.
- Aviso de driver NVIDIA antiguo, y GPU comprobada antes de pedir carpeta.
- Mismo acceso **ComfyUI**, misma barra de progreso y mismos 14 pasos que 2.7.0.

Validación: 125 pruebas automáticas, instalación recomendada completa en RTX 4060 Ti y prueba del autor con su biblioteca de modelos en otro disco. El detalle de las versiones de prueba está debajo.

## v3.0.0-rc.2 — 2026-10-01 (rama de pruebas)

Correcciones de la revisión de la rc.1.

- README: vuelve el de la versión estable, con logo, insignias, botón de descarga, Discord y YouTube, y suma una sección con las novedades de la versión 3.
- La barra de progreso de v2.7.0 vuelve a verse en descarga, extracción, pip y git. El inicio en PowerShell pasaba la salida de Python y de `progreso.ps1` por una tubería: los dos creían que no había consola, no dibujaban la barra y Python retenía sus mensajes durante minutos. Ahora heredan la consola.
- El modo recomendado instala lo mismo que las respuestas por defecto de 2.7.0, sin preguntar: Manager clásico, Cine con IA, monitor, nodos de video (KJNodes, VideoHelperSuite, GGUF, SelfLift, escalador H3), extras de interfaz (rgthree, Custom-Scripts) y SageAttention en NVIDIA. Los nodos de la comunidad siguen en el modo avanzado.
- Los nodos de terceros siguen fijados a un commit, pero quedan sobre su rama: `Actualizar-ComfyUI-y-Nodos.bat` y el Manager pueden actualizarlos (antes `git pull` fallaba con el commit suelto). Cine con IA se instala siempre en su última versión.
- 7zr.exe se descarga de la release 26.03 de 7-Zip en GitHub, el mismo archivo con el mismo SHA-256. La URL sin versión cambia con cada versión de 7-Zip y habría roto todas las instalaciones.
- Errores explicados en el idioma del usuario y con la solución (driver, carpeta ocupada, espacio, descarga cortada...). El código sigue visible para soporte.
- Vuelven los avisos de 2.x: las carpetas dentro de OneDrive y las rutas con tildes o eñes se rechazan explicando el motivo, y el paquete de 2 GB se elimina tras extraer.
- Carpeta propuesta: `ComfyUI` en el SSD con más espacio libre; Enter la acepta y, si ya existe, se usa `ComfyUI-2`. Una carpeta rechazada deja elegir otra en lugar de cerrar el instalador.
- La GPU y el driver se comprueban antes de preguntar la carpeta.
- "Seguir usando mi instalación" ya no pregunta cuál, porque no se modifica ninguna.
- Driver NVIDIA anterior al 580 en una tarjeta moderna: instala CUDA 12.6 y avisa de que actualizar el driver da la versión con CUDA 13; en el modo avanzado se puede abrir la página de NVIDIA y salir.
- La comprobación de escritura ya no falla al instalar en la raíz de C: (un usuario estándar puede crear carpetas allí, pero no archivos).
- Acceso directo **ComfyUI**, como en 2.x; si ya existe uno de otra instalación, **ComfyUI (2)**. El resumen dice cuál se creó.
- Pasos numerados `[n/14]` como en 2.x: las fases de equipo, descarga y extracción entran al resumen final.
- La búsqueda de instalaciones entra en las carpetas de OneDrive y solo evita enlaces y junctions reales.
- Biblioteca de modelos desde el principio: si no hay modelos previos, el instalador propone `ComfyUI-models` en el disco con más espacio (Enter) o deja elegir otra carpeta o disco. Se crea vacía con la estructura de ComfyUI, enlazada como destino de descargas (`is_default`) y registrada, así que una reinstalación la encuentra sola. No se acepta dentro de la instalación, en OneDrive, en carpetas del sistema, con tildes o en una unidad de red.
- Un ComfyUI vacío (marcadores `put_*_here` y TAESD de fábrica) ya no se ofrece como biblioteca: con una biblioteca central registrada basta un Enter para enlazarla.
- "CONFIRM" en inglés; recomendaciones distintas para cada perfil de VRAM.
- Repositorio: finales de línea LF normalizados (`* text=auto`), como en `main`.

## v3.0.0-rc.1 — 2026-09-30 (rama de pruebas)

- Inicio PowerShell sin Python global: diagnóstico, detección de instalaciones, selector de destino y validaciones antes de descargar.
- Reutilización sin cambios por defecto; configuración de un portable existente solo con autorización explícita.
- Portable ComfyUI v0.38.0 y nodos fijados por revisión/hash; matriz separada de la lógica.
- Git portátil local automático, modo recomendado sin preguntas técnicas, grupos y aceleradores opcionales en avanzado.
- Perfiles de VRAM, varias bibliotecas de modelos y carpeta de resultados en otro disco.
- Operación real de GPU, arranque y carga de nodos; estado persistente y logs fechados.
- Accesos directos independientes que preservan otras instalaciones.
- Pruebas de seguridad y compatibilidad, y validación física NVIDIA documentada.

## v2.7.0 — 2026-09-27

- Una sola barra de progreso para toda la instalación. Antes cada etapa mostraba algo distinto: la barra de `#` de curl en la descarga, el porcentaje de 7-Zip en la extracción, un giro `| / - \` en pip y git, y nada en el SHA-256 del paquete ni en las fases 2 y 3 de la migración. Ahora todas usan la misma línea: barra ámbar, porcentaje, GB hechos del total, tiempo que falta, velocidad, qué se está haciendo y con qué archivo.
- Descarga, SHA-256 y extracción (el `.bat`, antes de que exista el Python del portable) dibujan esa línea con `src/progreso.ps1`: curl sigue bajando con los mismos reintentos y reanudación, el SHA-256 se calcula por bloques y el porcentaje de 7-Zip se lee de su salida. Si las directivas del equipo no dejan correr el script, se usan curl y 7-Zip con su barra de siempre.
- Lo que no tiene un total conocido (pip, git, la prueba de arranque de ComfyUI, probar aceleradores, detectar la GPU, buscar modelos) usa la misma línea en modo "en curso": un tramo ámbar va y viene, en lugar del porcentaje va el tiempo transcurrido y al final la última línea que escribió el programa (por ejemplo, qué paquete está bajando pip).
- Migración de modelos: las tres fases y la simulación muestran la barra; cada fase cierra con su resumen ("Biblioteca verificada: 73 de 73 archivos · 71.8 GB en 5 min 12 s") y el resumen final agrega el tiempo total.
- El porcentaje también va al título de la ventana y, en Windows Terminal, al anillo de progreso de la pestaña y del icono de la barra de tareas (en modo "en curso" gira sin porcentaje); se ve aunque la ventana esté minimizada.
- La línea se adapta al ancho de la ventana: si no cabe, primero se quita la velocidad, luego los GB y al final se acorta el nombre del archivo por el medio, conservando el final (fp16, .safetensors). La barra no cambia de largo entre un dibujo y otro.
- Sin cambios en la seguridad de la migración: se hacen las mismas lecturas y comprobaciones SHA-256 que en v2.5.0; la copia va por bloques de 8 MB para poder informar el avance (copy2 de Python también copia por bloques en Windows) y conserva fechas y atributos igual que antes.
- Fuera de una consola (salida redirigida a un archivo) no se dibuja la barra, solo los resúmenes. `CINECONIA_PROGRESO=0` la desactiva.
- 21 pruebas nuevas en `tests/test_progreso.py`, entre ellas `progreso.ps1` con el PowerShell 5.1 de Windows en GitHub Actions (descarga desde un servidor local, SHA-256 bueno y malo, extracción y prueba con 7-Zip) y que el script siga en ASCII, como lo necesita PowerShell 5.1.

## v2.6.0 — 2026-09-27

- La cola de trabajos queda acoplada al panel lateral: ya no aparece el panel flotante de progreso ("Total", "Nodo actual") encima del lienzo, que repetía la barra de rgthree y el progreso del nodo Render. Solo se agregan los ajustes que falten en `ComfyUI/user/default/comfy.settings.json`, con copia `.bak` previa; lo que ya se haya elegido en ComfyUI no cambia. Para volver al panel flotante: menú "⋯" de la cola → "Historial de trabajos acoplado".
- README: bajo el botón de descarga se ve la versión del instalador que se baja. El número sale del último release, así que se actualiza solo con cada versión nueva.

## v2.5.0 — 2026-09-26

- Flujograma compacto, transparente y adaptado a GitHub claro/oscuro en ambos idiomas.
- Instalación de nodos: conservar fallos de dependencias, reparar carpetas incompletas con respaldo y volver a comprobar nodos existentes.
- Restringir versiones de PyTorch antes de instalar extras; detenerse si una recuperación falla. Comprobar GPU Intel no disponible.
- Probar aceleradores después de los nodos y comprobar el arranque real de ComfyUI y la carga de los paquetes; evitar mensajes de éxito si quedan incidencias.
- Extraer el portable en una carpeta temporal nueva sin borrar otro ComfyUI existente.
- Migración en tres fases: copiar todo, verificar el conjunto y retirar originales. Si falla la copia o verificación, conservar todos los originales. Registrar destinos y SHA-256 antes de borrarlos.
- Mostrar las carpetas finales y recordar la biblioteca central para instalaciones futuras, con aviso si el disco está desconectado. Configurarla como biblioteca preferida sin duplicar modelos.
- Conservar colores y progreso en consola. Añadir pruebas automáticas Windows/Python 3.12 y 3.13, excluidas del ZIP de descarga.
- Validación real: ComfyUI v0.37.0, Windows 11, RTX 4060 Ti, CUDA 13 y PyTorch 2.13; carga de 14 paquetes de nodos, SageAttention probado en GPU y reinstalación sin cambiar PyTorch. Alcance y pendientes en `.github/VALIDATION.md`.

## v2.4.0 — 2026-09-26

- Nuevo paso "Extras de interfaz" (por defecto si): rgthree-comfy, que dibuja la barra de progreso verde arriba de la pantalla con la cola, el porcentaje y el nodo que corre, y ComfyUI-Custom-Scripts, con el boton Show Image Feed. Ninguno trae dependencias de Python.
- Nuevo paso "Nodos de la comunidad" (por defecto no): ComfyUI Essentials, Comfyroll, WAS Node Suite y ControlNet Auxiliary Preprocessors, los que piden muchos workflows compartidos. Traen dependencias pesadas; si se omiten, ComfyUI los ofrece con el Manager al abrir un workflow que los necesite.
- La instalacion pasa de 12 a 14 pasos. Un grupo que se rechaza queda como omitido aunque ya hubiera alguno de sus nodos; solo se marca como fallo si se pidio y algo no quedo.
- Si Git se acaba de instalar, se agrega al PATH de la instalacion para que pip pueda instalar requisitos "git+https://" (los usa WAS).

## v2.3.1 — 2026-09-26

- Ya no sale en rojo el aviso de pip sobre comfyui-workflow-templates-media-*: viene asi en el portable oficial, no afecta a ComfyUI y aparecia en toda instalacion nueva. Queda solo en instalacion.log. Otros avisos de pip se muestran en ambar, no en rojo.
- Cada nodo aparece una sola vez al instalarse: la linea de sus requisitos ahora dice "requirements.txt".
- ComfyUI-Manager se resume como "clasico (boton Manager)" en vez de "OK OK (clasico)".

## v2.3.0 — 2026-09-26

- Progreso por pasos: la instalacion muestra 12 pasos numerados y cada uno cierra con su linea (listo, omitido o fallo) y un detalle: la GPU, lo instalado, "5 de 5" nodos para video...
- Al final, un resumen con todos los pasos y el tiempo total.
- pip y git corren con un indicador de una sola linea que se borra al terminar, asi no quedan barras congeladas a la mitad. Su salida completa va a ComfyUI\_cineconia\instalacion.log y, si algo falla, se muestran sus ultimas lineas.
- La barra de descarga de curl se reemplaza por la linea del paso al terminar.
- En Windows Terminal se usan los simbolos de visto y cruz; en la consola clasica, OK y X.

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
