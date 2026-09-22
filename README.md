# CineConIA Installer — instalador adaptativo de ComfyUI

Esta rama contiene la nueva arquitectura del instalador. La meta es que una
persona pueda ejecutar un solo BAT y que la instalacion se adapte al equipo
real, sin tener que conocer CUDA, ROCm, XPU, PyTorch o wheels.

## ¿Que archivo ejecuto primero?

Para una instalacion nueva, el orden recomendado es este:

1. **Primero: Instalar-ComfyUI.bat**
   - Instala ComfyUI.
   - Detecta la GPU y el backend apropiado.
   - Configura los aceleradores compatibles.
   - Instala los nodos Cine con IA si el usuario lo acepta.
   - Crea los lanzadores y el acceso directo de escritorio **ComfyUI**.

2. **Prueba ComfyUI una vez**
   - Abre el acceso directo **ComfyUI**.
   - Comprueba que la interfaz inicia correctamente.
   - Luego cierra ComfyUI antes de migrar modelos.

3. **Despues, solo si ya tienes modelos anteriores: Migrar-Modelos-ComfyUI.bat**
   - Busca o permite seleccionar la biblioteca antigua.
   - Permite elegir otro SSD/HDD para los modelos.
   - Primero hace una simulacion.
   - Luego puede copiar o mover de forma segura.
   - Finalmente puede enlazar la nueva biblioteca mediante extra_model_paths.yaml.

En forma resumida:

    Instalar-ComfyUI.bat
            |
            v
      Probar ComfyUI
            |
            v
       Cerrar ComfyUI
            |
            v
    ¿Ya tienes modelos?
        /         \
      No           Si
      |            |
      v            v
   Terminar   Migrar-Modelos-ComfyUI.bat

**Si empiezas desde cero y no tienes modelos antiguos, no necesitas ejecutar
Migrar-Modelos-ComfyUI.bat.**

**Si ya tenias un ComfyUI anterior y solo quieres ordenar/mover sus modelos,
tambien puedes usar Migrar-Modelos-ComfyUI.bat de forma independiente.**

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


## Migrar modelos de un ComfyUI que ya existe

Si ya tienes ComfyUI y acumulaste muchos modelos, usa **Migrar-Modelos-ComfyUI.bat**.
Sirve para consolidar una o varias bibliotecas antiguas en un disco grande sin
sobrescribir archivos ni borrar originales antes de verificar.

### Orden recomendado

1. **Cierra ComfyUI.**
2. Ejecuta **Migrar-Modelos-ComfyUI.bat**.
3. El migrador puede buscar bibliotecas existentes o puedes seleccionar manualmente
   una carpeta ComfyUI, una carpeta models o una biblioteca.
4. Puedes agregar varias instalaciones para consolidarlas en una sola.
5. Selecciona la carpeta padre del disco grande. Ejemplo:
   D:\IA\Modelos\ComfyUI
6. El resultado se organiza dentro de:
   D:\IA\Modelos\ComfyUI\models
7. Elige:
   - **Copiar:** deja intactos todos los originales.
   - **Mover seguro:** copia cada archivo, verifica SHA-256 y solo entonces elimina
     el original.
8. Primero aparece una **SIMULACION**. Muestra archivos, tamaño, duplicados,
   conflictos y elementos sin clasificar.
9. Nada cambia hasta escribir exactamente **MIGRAR**.
10. Al terminar puede actualizar extra_model_paths.yaml de los ComfyUI detectados.

### Estructura creada

La biblioteca usa las carpetas habituales de ComfyUI:

    models\
        checkpoints\
        diffusion_models\
        unet\
        text_encoders\
        clip\
        clip_vision\
        vae\
        loras\
        controlnet\
        upscale_models\
        embeddings\
        hypernetworks\
        style_models\
        gligen\
        latent_upscale_models\
        frame_interpolation\
        vae_approx\
        _sin_clasificar\

Si un archivo ya estaba dentro de una categoria conocida, conserva su categoria
y sus subcarpetas. Si no se puede clasificar con seguridad, va a
**_sin_clasificar**. El migrador no adivina tipos por el nombre del archivo.

### Duplicados y conflictos

- Un posible duplicado se confirma por **SHA-256**.
- Si el mismo nombre tiene contenido diferente, no se sobrescribe: se conserva
  con un nombre como __conflicto_2.
- En modo mover, el original se elimina solo despues de verificar la copia.
- Si aparece un error, ese original no se borra.

### extra_model_paths.yaml

Cuando el origen pertenece a un ComfyUI reconocible, el migrador ofrece enlazar
la nueva biblioteca. Si ya existe extra_model_paths.yaml:

- crea una copia .bak con fecha y hora;
- modifica solo el bloque administrado por CineConIA;
- conserva el resto del archivo.

Asi varias instalaciones de ComfyUI pueden compartir una unica biblioteca en
otro SSD/HDD sin duplicar cientos de gigabytes.

### Reporte

Cada ejecucion confirmada guarda un reporte JSON en:

    <biblioteca>\_cineconia_migracion\

Incluye origenes, destino, modo, duplicados, conflictos, errores y configuraciones
extra_model_paths.yaml actualizadas.
