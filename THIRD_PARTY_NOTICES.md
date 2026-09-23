# Avisos de terceros

Este instalador es MIT y descarga componentes desde sus fuentes correspondientes.

## ComfyUI
- Origen: https://github.com/Comfy-Org/ComfyUI
- Licencia: GPL-3.0
- Uso: portable oficial de NVIDIA, AMD o Intel.

## Icono del acceso directo
- Origen: https://github.com/Comfy-Org/docs (favicon.ico)
- Uso: identidad visual de ComfyUI en el acceso ComfyUI.
- Si falla la descarga, no se usa un icono promocional alternativo.

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
- Wheels Windows: actualmente kingbri1/flash-attention.
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

## 7-Zip
- Origen: https://www.7-zip.org/
- Licencia: LGPL-2.1
- 7zr.exe se descarga para extraer el portable.

## Influencia de ComfyUI-Easy-Install

Se tomaron ideas generales de experiencia de usuario de
Tavris1/ComfyUI-Easy-Install (MIT): BAT de entrada, lanzadores por flags,
actualizacion y reutilizacion de modelos.

No se copia su codigo. Esta implementacion mantiene las decisiones principales
en Python, evita branding de terceros/canal en el escritorio y resuelve extras
contra el entorno real instalado.
