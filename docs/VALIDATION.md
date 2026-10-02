# Validación de 3.0.0-rc.2

Rama de pruebas; no es una declaración de compatibilidad universal.

## rc.2 — instalación recomendada completa (1 de octubre de 2026)

Mismo equipo que la rc.1 (Windows 11 Pro, Ryzen 7 5700X, 31,9 GB, RTX 4060 Ti 16 GB, driver 616.92). Se ejecutó `ComfyUI-Setup.bat --destination C:\cia-rc2-test\ComfyUI --no-shortcut` en una carpeta nueva, con `CIA_SKIP_MODELS=1` para no tocar las bibliotecas de modelos del equipo.

| Elemento | Resultado |
|---|---|
| Pasos | 14 de 14 (`[1/14]` a `[14/14]`), resumen final con las fases del inicio, 6 min 22 s en total |
| Búsqueda previa | Encontró las tres instalaciones existentes y no las modificó |
| Descarga | Portable v0.38.0 NVIDIA (1,9 GB) y `7zr.exe` 26.03 desde GitHub, SHA-256 correctos |
| Extracción | 58.293 archivos, 4,1 GB en 3 min 12 s; caché y paquete eliminados al terminar |
| Aceleradores | Triton 3.8.0 y SageAttention 2.2.0 instalados sin preguntas y verificados en GPU |
| Nodos | Manager clásico, Cine con IA, Crystools, KJNodes, VideoHelperSuite, GGUF, SelfLift, escalador H3, rgthree y Custom-Scripts: 10 paquetes cargados en el arranque de comprobación |
| GPU | Multiplicación FP16 en CUDA correcta (`fp16_matmul: true`, PyTorch 2.14.0+cu130) |
| Estado | `install-state.json` en `verified`, todos los nodos `ok` |
| Lanzador principal | `Iniciar-ComfyUI-SageAttention.bat` |
| Actualización | `git pull --ff-only` correcto en los nodos instalados; el Manager, fijado en un commit anterior, avanzó a la rama actual |

La salida se redirigió a un archivo para registrarla, así que la barra en vivo no se dibujó: con salida redirigida solo se muestran los resúmenes, igual que en 2.7.0. Que los procesos hijos heredan la consola se comprueba en las pruebas automáticas (`Invoke-Console`).

## rc.1 — prueba física aislada (30 de septiembre de 2026)

Se descargó el portable oficial ComfyUI v0.38.0 NVIDIA, se comparó su SHA-256 con el manifiesto y se extrajo en una carpeta nueva, fuera de las instalaciones habituales. La prueba no enlazó modelos ni creó accesos en el escritorio.

| Elemento | Resultado |
|---|---|
| Sistema | Windows 11 Pro x64, AMD Ryzen 7 5700X, RAM 31.9 GB |
| GPU | NVIDIA RTX 4060 Ti, 16 GB, driver 616.92 |
| Diagnóstico | Compute 8.9, PCIe máximo 4.0 x8; ancho del bus de memoria no disponible |
| Python aislado | 3.13.14 |
| PyTorch | 2.14.0+cu130, CUDA 13.0, BF16 disponible |
| Operación real | Multiplicación FP16 de matrices en GPU, sincronización y resultado comprobados |
| ComfyUI | Arranque `--quick-test-for-ci` correcto, sin servidor persistente ni navegador |
| Nodos | Manager clásico, Cine con IA y VideoHelperSuite cargados en el resumen final |
| Dependencias | Sin conflictos nuevos relevantes; faltan tres paquetes multimedia de ejemplos del portable oficial, ya reconocidos y registrados por la base |
| Git ausente | MinGit 2.56.0 descargado, hash comprobado, extraído localmente y `git --version` correcto al simular ausencia de Git global |
| Detección | Identificó las dos instalaciones habituales y la copia de pruebas, sin modificarlas |

ComfyUI-Manager notificó un fallo de acceso a su registro remoto durante el arranque de comprobación y pasó a modo local. Los tres paquetes de nodos cargaron; esto no verifica la disponibilidad de su servicio externo ni la instalación de cualquier nodo del catálogo.

No se generaron imágenes/videos ni se descargaron modelos. La importación de un paquete Cine con IA no prueba todos sus nodos ni todos los workflows; los componentes opcionales siguen disponibles en modo avanzado.

## Pruebas automáticas

Ejecutar `python -B -m unittest discover -s tests -v` en Windows con Python 3.12 o 3.13. La suite cubre migración, conservación de archivos, conflictos, restricciones PyTorch, arranque, progreso PowerShell/Python, idiomas, versiones fijadas, selección CUDA, drivers, rutas protegidas/solapadas/ocupadas, falta de espacio, cancelación y autorización de mantenimiento.

La suite original tenía 69 pruebas; la rc.1 llegó a 102 y la rc.2 a 125. Las nuevas cubren el catálogo recomendado, la biblioteca de modelos nueva y su reinstalación, los nodos fijados sobre su rama, la URL versionada de 7-Zip, los mensajes de error en ambos idiomas, OneDrive, tildes, la carpeta propuesta y su numeración, volver a elegir tras un rechazo, la prueba de escritura sin restos, la limpieza de la caché, los enlaces en la búsqueda, el aviso de driver y el paso de argumentos a procesos hijos. Los resultados y el ZIP de esta rama quedan en GitHub Actions. Las pruebas de bootstrap ejecutan Windows PowerShell 5.1, sin depender de Pester ni paquetes externos.

## Límites pendientes de aceptación

- AMD, Intel XPU y NVIDIA anterior a Turing: paquetes y política fijados; no se dispone de esas GPU para verificar su ejecución física en esta sesión.
- Selector gráfico y carpeta propuesta: se comprueban rutas, cancelación y nueva elección por pruebas; la elección interactiva (Enter / C) y la barra en vivo en una consola real deben revisarse al probar el ZIP.
- No se ha probado una imagen de Windows completamente nueva sin Visual C++ ni winget. El fallo del requisito bloquea la configuración; MinGit ausente sí se probó de forma aislada.
- Los aceleradores y grupos opcionales conservan la resolución por compatibilidad del instalador previo. La validación física de esta candidata se concentra en el modo recomendado.

## Fuentes para la matriz

- [Portable oficial de ComfyUI](https://docs.comfy.org/installation/comfyui_portable_windows).
- [Release ComfyUI v0.38.0](https://github.com/Comfy-Org/ComfyUI/releases/tag/v0.38.0): archivos, tamaños y SHA-256.
- [Compatibilidad menor de CUDA](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html).
- [Git for Windows 2.56.0](https://github.com/git-for-windows/git/releases/tag/v2.56.0.windows.1).
- [7-Zip 26.03](https://github.com/ip7z/7zip/releases/tag/26.03): `7zr.exe`, SHA-256 publicado por GitHub.

Actualizar la matriz exige verificar descargas y repetir las pruebas de hardware aplicables; no cambiar a una versión nueva solo por ser la más reciente.
