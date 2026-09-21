<p align="center">
  <strong>Español</strong>
</p>

<h1 align="center">Instalador de Cine con IA</h1>

<p align="center">
  <strong>ComfyUI instalado y listo para vídeo, en dos clics.</strong><br>
  Sin descargar modelos · Sin marcas ajenas · Todo explicado antes de hacerlo
</p>

<p align="center">
  <a href="LICENSE"><img alt="Licencia MIT" src="https://img.shields.io/badge/licencia-MIT-blue?style=flat-square"></a>
  <img alt="Windows" src="https://img.shields.io/badge/Windows-10%20%2F%2011-0078d4?style=flat-square">
  <a href="https://www.youtube.com/@cineconia.oficial"><img alt="Canal de YouTube" src="https://img.shields.io/badge/youtube-Cine%20con%20IA-red?style=flat-square&logo=youtube&logoColor=white"></a>
</p>

---

## Qué hace

1. Descarga **ComfyUI portable** del release oficial de Comfy-Org
2. Mira tu equipo y te **recomienda** la rama de CUDA, explicándote por qué
3. Intenta instalar los aceleradores que te convienen, y **sigue sin ellos** si no existen para tu combinación
4. Instala los **nodos Cine con IA**
5. Comprueba que todo lo instalado **de verdad funciona**
6. Si ya tenías modelos en el disco, te los **enlaza** en vez de duplicarlos

## Qué NO hace

**No descarga modelos.** Ni uno. Son decenas de gigas y la elección es tuya: los bajas cuando quieras desde el nodo **Cine con IA · Modelos**, dentro de ComfyUI.

**No pone su marca en tu ComfyUI.** Ni iconos, ni avisos al arrancar, ni parches en su interfaz. El acceso directo se llama «ComfyUI» y lleva el icono de ComfyUI.

**No instala lo que no encaja.** Si no existe una versión compilada para tu combinación exacta de PyTorch y CUDA, te lo dice y sigue sin ella. Forzar una que no corresponde es como se rompen las instalaciones.

## Cómo se usa

1. Descarga este repositorio como ZIP y descomprímelo donde quieras
2. Doble clic en **`Instalar-ComfyUI.bat`**
3. Pulsa Enter

Eso es todo. Unos 2 GB de descarga y unos 10 minutos.

> **Ojo con dónde lo pones.** No lo descomprimas en `Archivos de programa`, en la raíz de `C:\` ni en carpetas del sistema: Windows te dará problemas de permisos.

## Lo que decide por ti, y por qué

### La rama de CUDA

Lo habitual es elegir CUDA por la versión del driver. Eso está mal: **CUDA no es un acelerador**, no hace tu tarjeta más rápida. Es la caja de herramientas contra la que se compila el binario.

Lo que sí cambia entre ramas es **cuántas ruedas compiladas existen**. Medido el 2026-09-20 en Windows:

| Proyecto | CUDA 12.8 | CUDA 13.0 |
|---|---|---|
| SageAttention | 12 | 6 |
| Nunchaku | 64 | 47 |

Así que salvo que tengas una **Blackwell (RTX 50xx)**, que necesita CUDA 13 porque las compilaciones de 12.8 no incluyen su arquitectura, te va a recomendar **12.8**. Puedes cambiarlo.

### El backend de atención

ComfyUI trae **Comfy Kitchen** incluido: es una dependencia fijada en su `requirements.txt`, así que ya está instalado. Se activa con `--use-ck-attention`.

Medimos SageAttention contra Kitchen en una RTX 4060 Ti con MiniMax H3, 124 fotogramas y 20 pasos:

| Backend | s/paso |
|---|---|
| SageAttention | **56,16** |
| Comfy Kitchen | ~57,5 |

SageAttention sale un **2-4% más rápido** — unos 35 segundos en un render de 19 minutos. Por eso el instalador **lo intenta**. Pero exige una rueda de terceros compilada por cada combinación de PyTorch y CUDA, y para algunas no existe: si falta, se sigue con Kitchen y no pasa nada.

*(Una tarjeta, un modelo, una resolución. En otras combinaciones habría que medir otra vez.)*

## Qué instala exactamente

| Pieza | Tamaño | Origen |
|---|---|---|
| ComfyUI portable | ~2,0 GB | Release oficial de Comfy-Org |
| Triton | ~120 MB | PyPI · `triton-windows` |
| SageAttention | ~50 MB | Releases de `woct0rdho/SageAttention` |
| Nodos Cine con IA | ~2 MB | `chaLords/ComfyUI-Cine-con-IA` |

Opcionales, si los marcas: Nunchaku (imagen en 4 bits), FlashAttention, InsightFace.

## Requisitos

- Windows 10 (1803 o superior) u 11
- GPU NVIDIA, AMD o Intel — se descarga el portable de tu fabricante
- `git`, para instalar los nodos
- Unos 10 GB libres para empezar; los modelos aparte

## Licencia

MIT. Úsalo, cámbialo, rómpelo.

Este instalador **descarga** ComfyUI, no lo incluye. ComfyUI es GPL-3.0 y pertenece a Comfy-Org. Los aceleradores pertenecen a sus autores, con sus propias licencias: están todas en [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), y el instalador te enseña cada una antes de instalar nada.

---

<p align="center">
  <a href="https://www.youtube.com/@cineconia.oficial">Tutoriales en YouTube</a> ·
  <a href="https://github.com/chaLords/ComfyUI-Cine-con-IA">Los nodos</a>
</p>
