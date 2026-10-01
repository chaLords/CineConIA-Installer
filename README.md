# CineConIA · Instalador seguro de ComfyUI

**3.0.0-rc.1 — versión de prueba del PLAN V2.** La versión estable 2.7.0 sigue en `main`; esta rama no cambia ninguna release publicada.

[Descargar esta rama de prueba](https://github.com/chaLords/CineConIA-Installer/archive/refs/heads/feature/instalador-v2-seguro.zip) · [English](README.en.md) · [Plan y alcance](docs/IMPLEMENTACION_V2.md) · [Pruebas](docs/VALIDATION.md)

## Para comenzar

1. Descarga y descomprime el ZIP. Necesitas Windows x64, Internet y unos 20 GB libres en el destino, más espacio para tus modelos.
2. Ejecuta **Instalar-ComfyUI.bat** o **ComfyUI-Setup.bat**.
3. Si detecta otra instalación, elige conservarla o crear una independiente. Para una nueva, selecciona una carpeta: dentro se creará `ComfyUI-CineConIA-V2`.
4. El instalador comprueba el equipo, descarga el paquete fijado, prepara dependencias, instala los nodos esenciales y verifica GPU y arranque.
5. Abre **ComfyUI - CineConIA V2**. Un acceso directo de otra instalación nunca se reemplaza.

Cancelar el selector sale sin instalar. Una carpeta ocupada se rechaza: selecciona otra vacía. No necesitas instalar Python, Git ni CUDA Toolkit manualmente.

## Qué hace el modo recomendado

- Detecta el idioma de Windows: español o inglés, sin preguntarlo.
- Muestra Windows, CPU, RAM, GPU, VRAM, driver, compute capability y PCIe cuando el equipo lo informa. Un dato desconocido aparece como «No disponible»; nunca se inventa.
- Usa el Python y PyTorch aislados del portable oficial. No modifica Python, Conda ni el PATH global.
- Usa Git existente o prepara **MinGit local**, con versión y SHA-256 fijados. Si falta Visual C++ Runtime, intenta prepararlo mediante winget; si no puede, explica el requisito y se detiene.
- Instala **ComfyUI-Manager clásico, Cine con IA y VideoHelperSuite**, fijados a revisiones concretas.
- Mantiene el backend de atención oficial. SageAttention, FlashAttention, Nunchaku y demás extras quedan disponibles en modo avanzado.
- Protege las versiones de PyTorch durante la instalación de nodos.
- Comprueba una operación FP16 real en la GPU, el arranque de ComfyUI y la carga de los nodos. No genera imágenes ni descarga modelos.
- Si encuentra modelos previos, ofrece enlazarlos donde están o abrir el migrador con simulación y confirmación.

## Modo avanzado

Ejecuta **ComfyUI-Advanced-Setup.bat**. Permite seleccionar manualmente una instalación, configurar de nuevo un portable con autorización explícita, elegir aceleradores y grupos de nodos, enlazar varias bibliotecas y guardar los resultados en otro disco.

Las instalaciones manuales y de otros gestores se detectan y se conservan. La configuración sobre una instalación existente está limitada a portables con `python_embeded` y `ComfyUI`; una instalación manual no se convierte ni se migra automáticamente.

Para autorizar la configuración de un portable existente debes escribir `CONFIRMAR`. Esto permite instalar dependencias/nodos y generar lanzadores; no equivale a autorizar mover modelos. El migrador solicita su propia confirmación.

## Compatibilidad y versiones

El paquete recomendado queda fijado a **ComfyUI v0.38.0**, con SHA-256 por variante en `config/compatibility_matrix.json`. Las descargas no siguen `latest`.

| Perfil | Regla |
|---|---|
| NVIDIA moderna | CUDA 13, Python 3.13, compute capability ≥7.5 y driver ≥580 |
| NVIDIA compatible con CUDA 12.6 | Compute capability ≥5.0 y <10.0; driver ≥528.33; Python 3.12 |
| AMD / Intel | Portable oficial correspondiente; debe superar la validación real de GPU |

Para NVIDIA, el instalador elige automáticamente una combinación admitida por GPU y driver. Una elección manual incompatible se bloquea. No instala ni actualiza drivers y nunca continúa como si una GPU inutilizable estuviera lista.

**Validado físicamente:** Windows 11, RTX 4060 Ti 16 GB, driver 616.92, Python 3.13.14, PyTorch 2.14.0+cu130. AMD, Intel y NVIDIA antiguas tienen reglas y paquetes fijados, pero necesitan pruebas en su hardware antes de declarar una release estable. Consulta [el alcance de validación](docs/VALIDATION.md).

## Modelos, discos y protección

- El destino debe ser local, fijo, vacío y escribible. Se rechazan carpetas del sistema, rutas solapadas con una instalación detectada y enlaces/junctions en el destino.
- La búsqueda de instalaciones tiene límites de tiempo y profundidad. Si no encuentra la tuya, usa la selección manual avanzada.
- La extracción ocurre en una carpeta temporal nueva del mismo disco. Un fallo conserva los archivos para diagnóstico; no borra ni renombra instalaciones anteriores.
- Las bibliotecas enlazadas se escriben en un bloque administrado de `extra_model_paths.yaml`, con respaldo de la configuración anterior.
- **ComfyUI-Model-Migrator.bat** conserva el flujo de simulación, comprobación de espacio, copia, comparación SHA-256 y confirmación antes de mover. Puede usar el Python de un portable si no tienes Python global.
- Los modelos nunca se descargan automáticamente.

## Diagnóstico y recuperación

```text
ComfyUI-Setup.bat --diagnose
ComfyUI-Setup.bat --advanced
ComfyUI-Setup.bat --destination "D:\IA\ComfyUI-Prueba"
ComfyUI-Setup.bat --cuda 12.6
ComfyUI-Setup.bat --lang en
```

`--diagnose` solo inspecciona y guarda el registro del instalador. `--no-shortcut` genera lanzadores sin tocar el escritorio. Las descargas interrumpidas se reanudan y se comprueba el hash completo antes de ejecutarlas.

Registros: `logs/` junto al instalador y `_cineconia/instalacion-<fecha>.log` dentro del portable. `_cineconia/install-state.json` distingue base preparada, configuración, verificado, incidencias e interrupción; también registra las versiones detectadas. Para reintentar la configuración, usa el modo avanzado y autoriza ese portable. No se promete rollback de todos los paquetes: la protección de PyTorch intenta recuperar la base y se detiene si no puede.

## Desarrollo

```text
python -B -m unittest discover -s tests -v
```

El inicio está en `src/bootstrap.ps1`; el configurador y migrador siguen en Python. Políticas: `config/compatibility_matrix.json`, `config/recommended_nodes.json` y `config/hardware_profiles.json`. La configuración está separada de la lógica.

Los tests de Windows se ejecutan en GitHub Actions con Python 3.12 y 3.13. Esta rama genera un ZIP de prueba como artefacto; no publica ni reemplaza la release estable.

[Cine con IA · YouTube](https://www.youtube.com/@cineconia.oficial) · [Discord](https://discord.gg/hXKJ78cEua). Proyecto independiente, no afiliado a Comfy Org. Consulta [LICENSE](LICENSE) y [avisos de terceros](assets/THIRD_PARTY_NOTICES.md).
