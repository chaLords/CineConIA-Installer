# Avisos de terceros

Este instalador es MIT y **no incluye** ninguno de los programas que instala:
los descarga de sus fuentes originales cuando lo ejecutas. Cada uno pertenece
a sus autores y conserva su propia licencia.

El instalador enseña la licencia de cada pieza en pantalla antes de
instalarla, para que nadie acabe con software cuyo origen desconoce.

---

## ComfyUI

- **Origen:** <https://github.com/Comfy-Org/ComfyUI>
- **Licencia:** GPL-3.0
- **Cómo se usa:** se descarga el paquete portable oficial desde sus releases.

Este instalador **descarga** ComfyUI, no lo redistribuye. Son dos programas
separados: por eso el instalador puede ser MIT sin que la GPL-3.0 de ComfyUI
le alcance. Si algún día se empaquetara ComfyUI dentro de este repositorio,
ese conjunto tendría que pasar a GPL-3.0.

## Comfy Kitchen

- **Origen:** <https://github.com/Comfy-Org/comfy-kitchen>
- **Licencia:** Apache-2.0
- **Cómo se usa:** no se instala. Viene con ComfyUI como dependencia fijada
  en su `requirements.txt`; el instalador solo elige el flag de arranque que
  lo activa.

## Triton para Windows

- **Origen:** <https://github.com/woct0rdho/triton-windows>
- **Licencia:** MIT
- **Cómo se usa:** se instala desde PyPI (`triton-windows`), con la
  restricción de versión que corresponde a tu PyTorch.

## SageAttention

- **Origen:** <https://github.com/woct0rdho/SageAttention>
- **Licencia:** Apache-2.0
- **Cómo se usa:** se descarga la rueda de sus releases que corresponde a tu
  combinación de PyTorch, CUDA y Python. Si no existe una que encaje, no se
  instala nada y se sigue con la atención incluida en ComfyUI.

## Nunchaku (SVDQuant)

- **Origen:** <https://github.com/nunchux-ai/nunchaku>
- **Licencia:** Apache-2.0
- **Cómo se usa:** opcional, solo si marcas un perfil de imagen. Se descarga
  la rueda correspondiente de sus releases.
- Implementa SVDQuant, publicado como *spotlight* en ICLR 2025.

## FlashAttention

- **Origen del proyecto:** <https://github.com/Dao-AILab/flash-attention>
- **Licencia:** BSD-3-Clause
- **Cómo se usa:** opcional. Las ruedas para Windows las publican terceros,
  porque el proyecto original no las distribuye.

## InsightFace

- **Origen:** <https://github.com/deepinsight/insightface>
- **Licencia:** MIT
- **Cómo se usa:** opcional, desde PyPI.

## onnxruntime

- **Origen:** <https://github.com/microsoft/onnxruntime>
- **Licencia:** MIT
- **Cómo se usa:** opcional, desde PyPI (`onnxruntime-gpu`).

## 7-Zip (7zr.exe)

- **Origen:** <https://www.7-zip.org/>
- **Licencia:** LGPL-2.1
- **Cómo se usa:** se descarga al ejecutar el instalador porque Windows no
  sabe abrir archivos `.7z` por su cuenta, que es el formato en el que
  Comfy-Org publica el portable. No se redistribuye en este repositorio.

---

## Sobre ComfyUI-Easy-Install

Este proyecto nació después de usar
[Tavris1/ComfyUI-Easy-Install](https://github.com/Tavris1/ComfyUI-Easy-Install)
(MIT), y de él vienen varias ideas: la entrada de dos clics, los extras
opcionales, el enlazado de carpetas de modelos y el activador de rutas
largas de Windows.

**No se ha copiado su código.** Está escrito de cero, en Python en vez de
batch, con decisiones distintas: la rama de CUDA se recomienda por la GPU y
no por la versión del driver, las ruedas se buscan en los releases en vez de
estar escritas en una tabla fija, lo que no encaja se omite con un aviso en
vez de fallar en silencio, y lo instalado se verifica al terminar.
