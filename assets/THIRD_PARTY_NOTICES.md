# Avisos de terceros

Este instalador es MIT y descarga componentes desde sus fuentes correspondientes.

## ComfyUI
- Origen: https://github.com/Comfy-Org/ComfyUI
- Licencia: GPL-3.0
- Uso: portable oficial de NVIDIA, AMD o Intel.

## Icono del acceso directo
- Origen: https://github.com/homarr-labs/dashboard-icons (png/comfyui.png), https://dashboardicons.com/icons/comfyui
- Licencia de la coleccion: Apache-2.0. El logo es la marca de ComfyUI (Comfy Org).
- Uso: identidad visual de ComfyUI en el acceso ComfyUI; convertido a assets/ComfyUI.ico.
- Tambien aparece junto al logo de Cine con IA en la cabecera del README (.github/assets/logo-cineconia-comfyui.png), solo para indicar que el instalador es para ComfyUI. Este proyecto no esta afiliado a Comfy Org.

## Comfy Kitchen
- Origen: https://github.com/Comfy-Org/comfy-kitchen
- Licencia: Apache-2.0
- Se usa con --use-ck-attention cuando el modulo esta disponible.

## Triton para Windows
- Origen: https://github.com/woct0rdho/triton-windows
- Licencia: MIT
- PyPI; solo se instala con una regla conocida para la rama real de PyTorch.

## Cabeceras de Python (include/libs)
- Origen: https://github.com/woct0rdho/triton-windows/releases/tag/v3.0.0-windows.post1
- Licencia: PSF License (Python)
- Solo las carpetas include y libs, añadidas a python_embeded cuando se instala Triton.

## SageAttention
- Origen: https://github.com/woct0rdho/SageAttention
- Licencia: Apache-2.0
- Se busca una wheel compatible con PyTorch, CUDA y Python reales.

## Nunchaku
- Origen: https://github.com/nunchux-ai/nunchaku
- Licencia: Apache-2.0
- Opcional en modo avanzado.

## FlashAttention
- Proyecto: https://github.com/Dao-AILab/flash-attention
- Licencia: BSD-3-Clause
- Wheels Windows: mjun0812/flash-attention-prebuild-wheels (BSD-3-Clause) para
  PyTorch recientes y kingbri1/flash-attention para las versiones anteriores.
- Opcional y verificado por import.

## InsightFace
- Origen: https://github.com/deepinsight/insightface
- Licencia: MIT

## ONNX Runtime
- Origen: https://github.com/microsoft/onnxruntime
- Licencia: MIT
- NVIDIA usa onnxruntime-gpu; otros backends usan fallback CPU en esta version.

## ComfyUI-Manager
- Origen: https://github.com/Comfy-Org/ComfyUI-Manager
- Licencia: GPL-3.0
- Version clasica, clonada en custom_nodes/comfyui-manager si el usuario lo acepta.
- Sin Git, se usa el Manager integrado de ComfyUI (manager_requirements.txt).

## Microsoft Visual C++ Redistributable
- Origen: winget, paquete Microsoft.VCRedist.2015+.x64
- Licencia: terminos de Microsoft
- Solo si falta y el usuario lo acepta; necesario para que PyTorch cargue.

## ComfyUI-Crystools
- Origen: https://github.com/crystian/ComfyUI-Crystools
- Licencia: MIT
- Opcional: monitor de recursos en la barra superior. Tras instalar sus
  dependencias se retira el paquete pynvml (envoltorio obsoleto); el modulo
  real lo aporta nvidia-ml-py.

## Nodos opcionales
Se clonan desde el repositorio de su autor solo si el usuario lo acepta:
- ComfyUI-nunchaku — https://github.com/nunchux-ai/ComfyUI-nunchaku — Apache-2.0
- ComfyUI-KJNodes — https://github.com/kijai/ComfyUI-KJNodes — GPL-3.0
- ComfyUI-VideoHelperSuite — https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite — GPL-3.0
- ComfyUI-GGUF — https://github.com/city96/ComfyUI-GGUF — Apache-2.0
- comfyui-SelfLift — https://github.com/facok/comfyui-SelfLift — sin licencia declarada en el repositorio

## 7-Zip
- Origen: https://www.7-zip.org/ (release oficial en https://github.com/ip7z/7zip)
- Licencia: LGPL-2.1
- 7zr.exe se descarga para extraer el portable, en una version fija con su
  SHA-256 (config/compatibility_matrix.json).

## Influencia de ComfyUI-Easy-Install

Se tomaron ideas generales de experiencia de usuario de
Tavris1/ComfyUI-Easy-Install (MIT): BAT de entrada, lanzadores por flags,
actualizacion y reutilizacion de modelos.

No se copia su codigo. Esta implementacion mantiene las decisiones principales
en Python, evita branding de terceros/canal en el escritorio y resuelve extras
contra el entorno real instalado.

## MinGit (Git for Windows)
- Origen: https://github.com/git-for-windows/git
- Licencia: GNU GPL v2; los archivos de licencia originales se conservan en la
  distribucion descargada.
- Solo se descarga si falta Git, y se extrae dentro de la nueva instalacion.
  URL y SHA-256 fijados en config/compatibility_matrix.json.

## Descargas con version fija
Las versiones de ComfyUI y los commits de los nodos de terceros estan en
config/*.json. El ZIP del instalador no incluye binarios de terceros. El
alcance de las pruebas de hardware esta en docs/VALIDATION.md.
