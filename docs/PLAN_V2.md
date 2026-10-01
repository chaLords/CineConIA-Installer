# Especificación V2 — Próxima versión del instalador de ComfyUI / Cineconía

## 0. Estado del documento

Este documento es una **especificación de planificación y diseño**.

No autoriza todavía a modificar:

- el repositorio;
- el instalador actual;
- scripts `.bat`;
- scripts PowerShell;
- nodos;
- modelos;
- dependencias;
- estructura de carpetas;
- releases publicadas.

Su función es servir como documento maestro para una futura implementación por ChatGPT, Claude u otro colaborador.

Antes de escribir código, se deberá revisar el repositorio real y contrastar esta especificación con el estado actual del proyecto.

---

# 1. Resumen ejecutivo

La próxima versión del instalador de ComfyUI / Cineconía deberá estar diseñada principalmente para usuarios principiantes, pero sin limitar a usuarios avanzados.

La meta es que un usuario sin conocimientos previos pueda instalar y dejar operativo ComfyUI con la mínima cantidad posible de decisiones.

La experiencia debe seguir cuatro principios:

> **Automática para el principiante.**  
> **Transparente durante todo el proceso.**  
> **Segura frente a instalaciones existentes.**  
> **Flexible para usuarios avanzados.**

El instalador no debe ocultar lo que hace. Debe mostrar cada etapa, cada validación y cada resultado de manera visual y comprensible.

La filosofía central será:

> **Simplificar las decisiones, no ocultar los procesos.**

---

# 2. Objetivos

## 2.1. Objetivo principal

Construir una nueva versión del instalador capaz de:

- detectar automáticamente el entorno del usuario;
- preparar las dependencias necesarias;
- instalar ComfyUI;
- configurar una base recomendada de nodos;
- proteger instalaciones existentes;
- reutilizar o migrar modelos;
- verificar que el sistema realmente funciona;
- mostrar claramente cada acción ejecutada.

## 2.2. Objetivos de experiencia de usuario

El usuario principiante debe poder completar la instalación sin necesidad de comprender:

- Python;
- Git;
- CUDA;
- PyTorch;
- entornos virtuales;
- Custom Nodes;
- rutas internas de ComfyUI;
- estructura de modelos;
- versiones compatibles;
- variables de entorno.

## 2.3. Objetivos técnicos

La nueva arquitectura deberá:

- ser modular;
- ser mantenible;
- separar configuración de lógica;
- permitir actualizar compatibilidades sin reescribir todo;
- registrar errores;
- soportar múltiples discos;
- evitar sobrescrituras accidentales;
- permitir evolución futura hacia reparación, actualización y perfiles por hardware.

---

# 3. Alcance de la V2

La V2 debe cubrir como mínimo:

- Windows;
- detección automática de idioma;
- detección de hardware;
- detección de GPU;
- detección de VRAM;
- detección de instalaciones existentes;
- preparación automática del entorno;
- instalación recomendada;
- modo avanzado;
- selección gráfica de carpetas;
- migración o reutilización de modelos;
- instalación de nodos esenciales;
- verificaciones finales;
- logs.

---

# 4. Fuera de alcance por ahora

Esta especificación no obliga todavía a implementar:

- soporte Linux;
- soporte macOS;
- actualización automática de drivers;
- instalación silenciosa sin interfaz;
- sistema completo de auto-update;
- gestión de cuentas;
- descarga automática de todos los modelos posibles;
- integración con gestores externos no definidos;
- reparación completa de instalaciones dañadas;
- marketplace de nodos.

Estos puntos pueden contemplarse más adelante.

---

# 5. Filosofía de interacción

La regla principal será:

> **Cero preguntas mientras el instalador pueda decidir de manera segura.**

El instalador solo debe detenerse cuando exista una decisión que pueda afectar:

- datos;
- una instalación previa;
- modelos existentes;
- ubicación de almacenamiento;
- comportamiento irreversible.

---

# 6. Modos de instalación

## 6.1. Instalación recomendada

Será la opción por defecto.

Pensada para:

- usuarios nuevos;
- usuarios que no entienden ComfyUI;
- usuarios que quieren una instalación lista para usar.

Debe:

- tomar decisiones automáticamente;
- instalar dependencias necesarias;
- instalar nodos recomendados;
- usar perfiles de hardware;
- minimizar preguntas;
- proteger datos existentes.

## 6.2. Instalación avanzada

Pensada para usuarios experimentados.

Podrá permitir:

- seleccionar nodos;
- seleccionar componentes;
- definir rutas;
- elegir estrategias de modelos;
- reutilizar instalaciones;
- configurar múltiples discos;
- personalizar comportamiento.

## 6.3. Regla importante

Tener ComfyUI instalado no convierte automáticamente al usuario en avanzado.

La detección de instalaciones previas debe funcionar en ambos modos.

---

# 7. Idioma

El instalador no debe preguntar el idioma.

Debe detectar automáticamente:

- idioma del sistema;
- configuración regional;
- locale de Windows;
- configuración de PowerShell como referencia secundaria.

Ejemplos:

- `es-CL`
- `es-ES`
- `es-MX`

Estas variantes pueden compartir inicialmente la misma traducción al español.

Si el idioma no se reconoce:

> usar inglés como fallback.

---

# 8. Interfaz visual

La consola debe ser parte central de la experiencia.

Debe mostrar:

- pasos;
- progreso;
- resultados;
- advertencias;
- errores;
- validaciones.

Ejemplo:

```text
[1/10] Analizando el sistema...
       ✓ Windows detectado
       ✓ GPU detectada
       ✓ RAM detectada

[2/10] Preparando entorno...
       ✓ Python preparado
       ✓ PyTorch instalado
       ✓ GPU reconocida

[3/10] Buscando instalaciones previas...
       ✓ Sin conflictos

[4/10] Instalando ComfyUI...
       ████████████████████ 100%
       ✓ Instalación completada
```

---

# 9. Convención de estados

Usar de forma consistente:

- Verde → éxito.
- Amarillo → advertencia.
- Rojo → error.
- Blanco/gris → en curso o pendiente.
- Barra de progreso → procesos largos.
- Mensaje explicativo → cuando se requiera acción.

---

# 10. Diagnóstico inicial del sistema

Antes de instalar componentes pesados, el instalador debe mostrar un resumen del equipo.

Ejemplo:

```text
╔══════════════════════════════════════════════════════╗
║              INFORMACIÓN DEL SISTEMA                ║
╚══════════════════════════════════════════════════════╝

✓ Windows 11 64-bit
✓ CPU: AMD Ryzen 7 5700X
✓ RAM: 32 GB
✓ GPU: NVIDIA GeForce RTX 4060 Ti
✓ VRAM: 16 GB
✓ Bus de memoria: 128-bit
✓ PCIe: 4.0 x8
✓ Driver NVIDIA: xxxx.xx
✓ CUDA disponible
✓ Python compatible
✓ Git disponible
✓ Espacio libre: xxx GB
```

---

# 11. Información de GPU

Siempre que sea técnicamente posible, detectar:

- fabricante;
- modelo;
- VRAM;
- bus de memoria;
- PCI Express;
- generación PCIe;
- cantidad de lanes;
- driver;
- capacidad CUDA;
- compatibilidad PyTorch;
- FP16;
- BF16;
- datos relevantes para inferencia.

Si un dato no está disponible:

```text
Bus de memoria: No disponible
```

El proceso debe continuar.

---

# 12. Perfiles de hardware

El instalador debe clasificar el equipo según VRAM.

Perfiles iniciales previstos:

- 8 GB
- 12 GB
- 16 GB
- 24 GB
- 32 GB
- 48 GB
- 64 GB o superior

Estos perfiles podrán influir en:

- modelos recomendados;
- configuraciones;
- cuantización;
- CPU offload;
- resolución;
- workflows;
- advertencias de memoria.

---

# 13. Gestión automática del entorno

El usuario no debe tener que preparar manualmente:

- Python;
- Git;
- PyTorch;
- runtime CUDA;
- requirements;
- PATH;
- dependencias necesarias.

Principio:

> **El instalador prepara automáticamente un entorno controlado para ComfyUI.**

---

# 14. Python

## 14.1. Escenarios

El instalador debe contemplar que el usuario:

- no tenga Python;
- tenga una versión incompatible;
- tenga varias versiones;
- use Anaconda;
- tenga Python sin PATH;
- tenga una instalación rota.

## 14.2. Política

No depender exclusivamente del Python global.

Debe:

- detectar Python;
- validar compatibilidad;
- ignorarlo si no conviene;
- preparar un entorno propio cuando sea necesario.

## 14.3. Entorno aislado

ComfyUI debe ejecutarse sobre un entorno controlado.

Esto reduce conflictos con:

- instalaciones previas;
- versiones incompatibles;
- PATH;
- paquetes globales;
- proyectos del usuario.

---

# 15. Git

Si Git es necesario y no está disponible:

- detectarlo;
- informar;
- instalarlo o preparar una alternativa;
- continuar automáticamente cuando sea seguro.

El usuario principiante no debería tener que instalar Git manualmente.

---

# 16. CUDA, drivers y runtime

Debe distinguirse entre:

- driver NVIDIA;
- CUDA Toolkit;
- runtime CUDA usado por PyTorch.

Regla:

> No asumir que el usuario necesita instalar el CUDA Toolkit completo.

El instalador debe:

- detectar GPU;
- detectar driver;
- comprobar compatibilidad;
- instalar la variante correcta de PyTorch;
- validar que la GPU funciona.

---

# 17. Drivers

Si el driver es demasiado antiguo:

```text
✗ El driver NVIDIA es demasiado antiguo.

GPU:
NVIDIA GeForce RTX 4060 Ti

Driver actual:
xxx.xx

Se requiere una actualización antes de continuar.
```

Por ahora no se recomienda actualizar drivers de forma automática.

Debe tratarse como una acción sensible.

---

# 18. PyTorch

El instalador debe:

- seleccionar la variante correcta;
- instalar la versión validada;
- verificar que importa correctamente;
- comprobar GPU;
- comprobar CUDA;
- comprobar estabilidad básica.

Ejemplo de validación:

```text
✓ PyTorch disponible
✓ GPU detectada por PyTorch
✓ CUDA Runtime operativo
```

---

# 19. Matriz de compatibilidad

No usar automáticamente “la última versión”.

Crear una matriz de versiones validadas.

Ejemplo conceptual:

```text
Perfil:
NVIDIA moderna

Python:
versión validada

PyTorch:
versión validada

CUDA Runtime:
versión validada

Driver mínimo:
versión validada

Nodos:
compatibilidad confirmada
```

---

# 20. compatibility_matrix.json

Planificar un archivo:

```text
config/compatibility_matrix.json
```

Posibles campos:

- hardware_profile;
- python;
- pytorch;
- cuda_runtime;
- min_driver;
- supported_nodes;
- restrictions;
- notes.

Ejemplo conceptual:

```json
{
  "nvidia_modern": {
    "python": "validated_version",
    "pytorch": "validated_version",
    "cuda_runtime": "validated_version",
    "min_driver": "validated_minimum"
  }
}
```

---

# 21. Política de versiones

La versión recomendada será:

> **La combinación más estable y validada para Cineconía.**

No necesariamente:

- la versión más nueva;
- la versión más popular;
- la versión recomendada por un único componente.

La combinación debe probarse como ecosistema.

---

# 22. Validaciones reales

No basta con instalar paquetes.

Verificar:

- Python;
- entorno;
- PyTorch;
- CUDA;
- GPU;
- ComfyUI;
- nodos esenciales.

Ejemplo:

```text
✓ Python ejecuta correctamente
✓ torch importa correctamente
✓ GPU reconocida
✓ CUDA disponible
✓ ComfyUI inicia
✓ Nodos esenciales cargan
```

---

# 23. Nodos recomendados

La instalación recomendada debe instalar automáticamente una base pequeña y controlada.

Ejemplo conceptual:

```json
{
  "core": [
    "ComfyUI-Manager",
    "Cineconia-Nodes"
  ],
  "video": [
    "VideoHelperSuite"
  ]
}
```

---

# 24. recommended_nodes.json

Planificar:

```text
config/recommended_nodes.json
```

Campos posibles:

- name;
- repository;
- version;
- category;
- required;
- compatibility;
- dependencies;
- notes.

Esto evita dejar las listas rígidas dentro del script.

---

# 25. Instalación bajo demanda

Nodos especializados podrán instalarse después.

Ejemplo:

```text
Este workflow requiere un componente adicional.

[ Instalar automáticamente ]
```

Esto evita cargar la instalación inicial con nodos innecesarios.

---

# 26. Detección de ComfyUI existente

Debe ejecutarse siempre.

Buscar:

- instalaciones estándar;
- instalaciones portables;
- instalaciones personalizadas;
- instalaciones en otros discos;
- carpetas con estructura ComfyUI.

---

# 27. Protección de datos

Principio obligatorio:

> **Nunca modificar, mover, borrar o sobrescribir una instalación existente sin consentimiento explícito.**

Aplicar también a:

- modelos;
- outputs;
- workflows;
- custom nodes;
- configuraciones.

---

# 28. Flujo al detectar ComfyUI

Mostrar:

```text
✓ ComfyUI encontrado
✓ Modelos encontrados
✓ Instalación existente protegida

Se requiere una decisión del usuario.
```

---

# 29. Modo recomendado con instalación existente

Opciones simples:

```text
¿Qué deseas hacer?

[1] Usar mi instalación y modelos actuales     ← Recomendado
[2] Crear una instalación nueva e independiente
```

---

# 30. Modo avanzado con instalación existente

Opciones ampliadas:

```text
[1] Usar instalación actual
[2] Crear nueva instalación
[3] Migrar modelos
[4] Copiar modelos
[5] Reutilizar modelos desde su ubicación
[6] Elegir carpetas manualmente
```

---

# 31. Selector gráfico de carpetas

No pedir rutas manuales a principiantes.

Usar selector gráfico de Windows para:

- destino de instalación;
- destino de modelos;
- migración;
- copias;
- múltiples discos.

---

# 32. Validación de destino

Antes de usar una ruta:

- comprobar espacio;
- permisos;
- carpeta existente;
- conflictos;
- rutas protegidas;
- unidad removible;
- espacio requerido.

Advertir sobre:

- `C:\Windows`
- `C:\Program Files`
- carpetas del sistema.

---

# 33. Migración de modelos

Mantener la lógica existente para:

- mover;
- copiar;
- reutilizar;
- evitar duplicados;
- validar espacio;
- mostrar progreso.

Ejemplo:

```text
Modelos detectados: 287 GB
Espacio disponible: 742 GB
Destino: E:\AI\Models

████████████████████ 100%

✓ Migración completada
```

---

# 34. Múltiples discos

La arquitectura debe soportar:

- ComfyUI en un disco;
- modelos en otro;
- outputs en otro;
- varias bibliotecas de modelos.

Nunca asumir que todo vive en `C:`.

---

# 35. Flujo recomendado — UX

```text
INICIO
  ↓
Detectar idioma
  ↓
Analizar hardware
  ↓
Mostrar diagnóstico
  ↓
Preparar entorno técnico
  ↓
Buscar ComfyUI existente
  ↓
¿Existe?
  ├─ No → continuar
  └─ Sí → proteger y preguntar
  ↓
Seleccionar destino si hace falta
  ↓
Validar espacio
  ↓
Instalar ComfyUI
  ↓
Instalar dependencias
  ↓
Instalar nodos recomendados
  ↓
Configurar estructura
  ↓
Verificar GPU
  ↓
Verificar ComfyUI
  ↓
Resumen final
  ↓
FIN
```

---

# 36. Flujo avanzado — UX

```text
INICIO
  ↓
Detectar idioma
  ↓
Analizar hardware
  ↓
Preparar entorno técnico
  ↓
Detectar instalaciones
  ↓
Mostrar opciones avanzadas
  ↓
Elegir estrategia
  ↓
Elegir rutas
  ↓
Elegir nodos/componentes
  ↓
Configurar modelos
  ↓
Ejecutar instalación
  ↓
Verificar
  ↓
Resumen técnico
  ↓
FIN
```

---

# 37. Manejo de errores

Los errores deben tener dos niveles.

## Nivel usuario

Explicación clara.

Ejemplo:

```text
✗ No se pudo instalar Git.

Posible causa:
No hay conexión con el servidor.

Qué puedes hacer:
1. Comprueba Internet.
2. Reintenta la instalación.
```

## Nivel técnico

Código y detalle.

Ejemplo:

```text
Código:
GIT_INSTALL_FAILED
```

---

# 38. Logs

Generar logs.

Ejemplo:

```text
logs/
└── install_2026-09-30_1608.log
```

Registrar:

- sistema;
- hardware;
- rutas;
- versiones;
- comandos;
- pasos;
- errores;
- warnings;
- resultado final.

No guardar datos sensibles innecesarios.

---

# 39. Reanudación y reparación

La arquitectura debe quedar preparada para detectar:

- instalación nueva;
- instalación incompleta;
- instalación válida;
- instalación dañada.

Futuro:

```text
[ Reparar instalación ]
```

---

# 40. Arquitectura modular propuesta

Estructura conceptual:

```text
installer/
├── launcher.bat
├── installer.ps1
├── modules/
│   ├── language.ps1
│   ├── system_check.ps1
│   ├── gpu_detection.ps1
│   ├── environment_setup.ps1
│   ├── python_setup.ps1
│   ├── git_setup.ps1
│   ├── pytorch_setup.ps1
│   ├── comfy_detection.ps1
│   ├── folder_selector.ps1
│   ├── node_installer.ps1
│   ├── model_migration.ps1
│   ├── verification.ps1
│   └── ui.ps1
├── config/
│   ├── recommended_nodes.json
│   ├── hardware_profiles.json
│   ├── compatibility_matrix.json
│   └── languages/
│       ├── es.json
│       └── en.json
└── logs/
```

Esto es conceptual.

No debe reorganizarse el proyecto actual sin auditarlo primero.

---

# 41. Requisitos funcionales

La V2 debe cumplir al menos:

- RF-01: detectar idioma automáticamente.
- RF-02: detectar sistema operativo.
- RF-03: detectar CPU.
- RF-04: detectar RAM.
- RF-05: detectar GPU.
- RF-06: detectar VRAM.
- RF-07: detectar driver.
- RF-08: intentar detectar bus de memoria.
- RF-09: intentar detectar PCIe.
- RF-10: clasificar perfil de VRAM.
- RF-11: detectar Python.
- RF-12: preparar entorno Python.
- RF-13: detectar Git.
- RF-14: preparar Git si hace falta.
- RF-15: instalar PyTorch compatible.
- RF-16: validar GPU desde PyTorch.
- RF-17: detectar ComfyUI existente.
- RF-18: proteger datos existentes.
- RF-19: permitir reutilización.
- RF-20: permitir nueva instalación.
- RF-21: abrir selector gráfico de carpetas.
- RF-22: validar espacio.
- RF-23: instalar ComfyUI.
- RF-24: instalar nodos esenciales.
- RF-25: migrar modelos.
- RF-26: copiar modelos.
- RF-27: reutilizar modelos existentes.
- RF-28: mostrar progreso.
- RF-29: generar logs.
- RF-30: verificar arranque final.

---

# 42. Requisitos no funcionales

- RNF-01: interfaz comprensible.
- RNF-02: no requerir conocimientos técnicos.
- RNF-03: comportamiento seguro.
- RNF-04: no sobrescribir datos sin autorización.
- RNF-05: modularidad.
- RNF-06: mantenibilidad.
- RNF-07: capacidad de diagnóstico.
- RNF-08: tolerancia a errores.
- RNF-09: compatibilidad con múltiples discos.
- RNF-10: posibilidad de expansión futura.
- RNF-11: mensajes traducibles.
- RNF-12: configuración desacoplada del código.

---

# 43. Roadmap propuesto

## Fase 1 — Auditoría

- revisar repositorio;
- mapear scripts;
- identificar lógica existente;
- identificar duplicaciones;
- detectar deuda técnica.

## Fase 2 — Diseño

- definir flujo real;
- definir módulos;
- definir archivos JSON;
- definir matriz de compatibilidad;
- definir mensajes.

## Fase 3 — Entorno técnico

- Python;
- Git;
- PyTorch;
- driver;
- validaciones.

## Fase 4 — Instalación

- ComfyUI;
- nodos;
- carpetas;
- rutas;
- perfiles.

## Fase 5 — Instalaciones existentes

- detección;
- protección;
- reutilización;
- migración.

## Fase 6 — UX

- consola;
- estados;
- colores;
- progreso;
- selector gráfico.

## Fase 7 — Verificación

- pruebas;
- logs;
- arranque;
- GPU;
- nodos.

## Fase 8 — Release candidate

- pruebas reales;
- correcciones;
- documentación;
- release de prueba.

---

# 44. Escenarios de prueba

Probar al menos:

## Usuario nuevo

- sin Python;
- sin Git;
- sin ComfyUI.

## Python incompatible

- varias versiones;
- Anaconda;
- sin PATH.

## Git ausente

- instalación controlada.

## GPU compatible

- driver válido;
- PyTorch funcional.

## Driver antiguo

- bloqueo seguro;
- mensaje comprensible.

## ComfyUI existente

- reutilización;
- nueva copia;
- protección.

## Muchos modelos

- cientos de GB;
- copia;
- migración;
- reutilización.

## Múltiples discos

- ComfyUI en C:;
- modelos en D:;
- destino en E:.

## Poco espacio

- rechazo seguro antes de copiar.

## Fallo de Internet

- error comprensible;
- retry futuro.

## Instalación interrumpida

- detectar estado parcial.

---

# 45. Criterios de aceptación

La V2 podrá considerarse lista para pruebas avanzadas cuando:

- un usuario sin Python pueda instalar;
- un usuario sin Git pueda instalar;
- PyTorch detecte correctamente la GPU;
- ComfyUI arranque;
- nodos esenciales carguen;
- no se sobrescriban instalaciones existentes;
- el selector gráfico funcione;
- la migración valide espacio;
- los errores sean comprensibles;
- se genere log;
- el flujo recomendado requiera pocas decisiones.

---

# 46. Riesgos identificados

## Riesgo 1 — Compatibilidad de versiones

Python, PyTorch, CUDA y nodos pueden cambiar.

Mitigación:

- matriz validada;
- versiones controladas;
- pruebas antes de release.

## Riesgo 2 — Custom Nodes

Un nodo puede romper compatibilidad.

Mitigación:

- lista controlada;
- versiones aprobadas;
- instalación bajo demanda.

## Riesgo 3 — Datos del usuario

Migraciones pueden afectar archivos.

Mitigación:

- consentimiento explícito;
- validación;
- no sobrescribir;
- logs.

## Riesgo 4 — Drivers

Instalar drivers automáticamente puede ser peligroso.

Mitigación:

- detectar;
- advertir;
- no actualizar automáticamente por ahora.

## Riesgo 5 — Múltiples instalaciones

El usuario puede tener varias copias.

Mitigación:

- detectar;
- mostrar rutas;
- pedir selección cuando corresponda.

---

# 47. Decisiones ya acordadas

Quedan establecidas estas decisiones:

1. No preguntar idioma.
2. Mostrar cada proceso visualmente.
3. Usar colores de estado.
4. Detectar hardware.
5. Mostrar GPU con más detalle.
6. Incluir bus de memoria cuando sea posible.
7. Incluir PCIe cuando sea posible.
8. Detectar VRAM.
9. Crear perfiles por VRAM.
10. Ofrecer modo recomendado.
11. Ofrecer modo avanzado.
12. Detectar ComfyUI existente en ambos modos.
13. Proteger datos.
14. Usar selector gráfico de carpetas.
15. Mantener migración/copia de modelos.
16. Preparar Python automáticamente.
17. Preparar Git cuando corresponda.
18. Gestionar PyTorch.
19. No confundir CUDA Toolkit con runtime.
20. No usar siempre la última versión.
21. Mantener una matriz de compatibilidad.
22. Validar que ComfyUI realmente arranque.
23. No modificar todavía el repositorio.

---

# 48. Preguntas abiertas para una futura fase

Estas decisiones deberán resolverse durante la auditoría:

- ¿Qué versión exacta de Python usará cada perfil?
- ¿Qué versión exacta de PyTorch se fijará?
- ¿Qué runtime CUDA será el estándar?
- ¿Cuál será el driver mínimo?
- ¿Qué nodos entrarán en Core?
- ¿Qué nodos serán opcionales?
- ¿Qué estrategia exacta se usará para instalar Git?
- ¿Se usará Python portable, venv u otra variante?
- ¿Cómo se detectarán múltiples instalaciones de ComfyUI?
- ¿Cómo se almacenarán las rutas configuradas?
- ¿Cómo se hará la verificación de nodos?
- ¿Cómo se implementará reparación en una versión futura?

---

# 49. Lo que NO debe hacerse todavía

No hacer aún:

- cambios en GitHub;
- refactor;
- commits;
- releases;
- cambios de BAT;
- cambios de PowerShell;
- migraciones;
- instalación de nuevos nodos;
- reestructuración de carpetas;
- fijación definitiva de versiones.

Primero:

> **auditar, comparar, diseñar y validar.**

---

# 50. Resultado esperado

La experiencia ideal:

```text
Doble clic
   ↓
Idioma detectado
   ↓
Hardware analizado
   ↓
Entorno técnico preparado
   ↓
ComfyUI existente detectado o descartado
   ↓
Solo se pregunta si hay algo que proteger
   ↓
Destino seleccionado gráficamente si hace falta
   ↓
ComfyUI instalado
   ↓
Nodos esenciales instalados
   ↓
Modelos reutilizados o migrados
   ↓
GPU verificada
   ↓
ComfyUI inicia correctamente
   ↓
Resumen final
```

---

# 51. Principio final

La V2 debe sentirse como un instalador pensado para alguien que no conoce ComfyUI, pero construido con suficiente control y transparencia para que también inspire confianza a un usuario avanzado.

> **Menos decisiones para el usuario.**  
> **Más inteligencia en el instalador.**  
> **Más visibilidad de lo que ocurre.**  
> **Más seguridad con los datos existentes.**

---

## Nota para ChatGPT, Claude u otro colaborador

Antes de implementar:

1. leer este documento completo;
2. revisar el repositorio actual;
3. identificar qué ya existe;
4. no duplicar funciones;
5. conservar lo que funciona;
6. comparar esta especificación con el código real;
7. proponer un plan de cambios;
8. recién después comenzar la implementación.

**Este archivo es una especificación de diseño, no una orden de ejecución inmediata.**

---

# 52. Principio de evolución abierta y mejora por IA

Esta especificación no debe interpretarse como un diseño cerrado ni como el máximo nivel posible del instalador.

Debe considerarse una **base funcional, conceptual y de seguridad** sobre la cual futuras herramientas de inteligencia artificial de mayor capacidad puedan:

- analizar el repositorio completo;
- detectar debilidades de arquitectura;
- proponer soluciones superiores;
- simplificar procesos;
- mejorar rendimiento;
- reforzar seguridad;
- aumentar compatibilidad;
- reducir errores;
- mejorar experiencia de usuario;
- mejorar detección automática;
- optimizar el sistema de instalación y actualización;
- introducir nuevas técnicas que hoy no estén contempladas.

Esto incluye futuras generaciones de modelos de razonamiento, agentes de programación o sistemas de desarrollo autónomo, independientemente de su proveedor o nombre comercial.

La especificación debe poder ser utilizada como contexto base por sistemas futuros de mayor capacidad, por ejemplo modelos avanzados de OpenAI, Anthropic u otros sistemas equivalentes o superiores.

---

# 53. Regla: el plan establece mínimos, no límites

Los requisitos definidos en este documento deben entenderse como:

> **mínimos funcionales, de experiencia y de seguridad que deben conservarse, no como límites máximos de diseño.**

Una futura IA podrá modificar la arquitectura propuesta si encuentra una solución objetivamente mejor.

Por ejemplo, podrá:

- reemplazar scripts por una arquitectura más robusta;
- mejorar el sistema de detección;
- crear un instalador gráfico completo;
- introducir recuperación automática;
- añadir rollback;
- mejorar aislamiento de dependencias;
- optimizar descargas;
- mejorar gestión de versiones;
- introducir caché;
- diseñar actualizaciones incrementales;
- automatizar diagnósticos;
- mejorar gestión de modelos;
- detectar conflictos entre Custom Nodes;
- resolver automáticamente dependencias;
- crear perfiles dinámicos según hardware;
- generar estrategias diferentes según GPU;
- mejorar logs y telemetría local;
- realizar pruebas automáticas antes de aplicar cambios.

Estas mejoras estarán permitidas siempre que respeten los principios fundamentales establecidos en este documento.

---

# 54. Principios que una futura mejora no debe romper

Aunque una IA futura proponga una arquitectura distinta, deberá conservar como mínimo:

1. Protección de datos existentes.
2. No sobrescribir instalaciones sin consentimiento.
3. Transparencia sobre lo que está ocurriendo.
4. Experiencia simple para principiantes.
5. Opciones avanzadas para usuarios experimentados.
6. Detección automática del entorno cuando sea posible.
7. Compatibilidad validada antes de aplicar versiones.
8. Posibilidad de recuperación ante errores.
9. Modularidad y mantenibilidad.
10. Capacidad de diagnóstico mediante logs.
11. Respeto por instalaciones y modelos existentes.
12. Validación antes de realizar acciones destructivas.
13. Capacidad de evolución futura.

---

# 55. Libertad de rediseño técnico

Las estructuras de carpetas, nombres de módulos, ejemplos JSON y flujos descritos en este documento son orientativos.

Una IA futura podrá proponer una estructura diferente si demuestra que es:

- más simple;
- más robusta;
- más mantenible;
- más segura;
- más rápida;
- más fácil de actualizar;
- más fácil de auditar;
- más compatible.

No se debe conservar una decisión técnica únicamente porque aparece en este documento.

Debe conservarse la intención de diseño.

---

# 56. Proceso recomendado para una IA futura

Antes de implementar una actualización importante, una IA avanzada debería:

1. Leer esta especificación completa.
2. Auditar el repositorio real.
3. Identificar qué partes del plan ya existen.
4. Detectar oportunidades de mejora no previstas.
5. Revisar tecnologías actualmente disponibles.
6. Comparar varias arquitecturas posibles.
7. Identificar riesgos de cada alternativa.
8. Proponer una arquitectura recomendada.
9. Explicar qué partes del plan original mantiene, modifica o sustituye.
10. Justificar cualquier desviación importante.
11. Crear un plan de migración.
12. Implementar de forma incremental.
13. Ejecutar pruebas automáticas.
14. Comprobar compatibilidad.
15. Verificar que no se pierden datos.
16. Documentar el resultado final.

---

# 57. Revisión inteligente de tecnologías actuales

Antes de fijar versiones o dependencias, una futura implementación deberá volver a comprobar el estado actual de:

- ComfyUI;
- Python;
- PyTorch;
- CUDA;
- drivers;
- Custom Nodes;
- sistemas de paquetes;
- APIs;
- herramientas de instalación;
- sistemas de virtualización o aislamiento;
- gestores de modelos;
- nuevas alternativas técnicas disponibles.

No se debe asumir que las decisiones de compatibilidad documentadas hoy seguirán siendo las mejores en el futuro.

---

# 58. Mejora continua del instalador

El proyecto debe diseñarse pensando en futuras generaciones del instalador.

Ejemplos posibles:

```text
V2
Instalación automática y segura
        ↓
V3
Actualización y reparación inteligente
        ↓
V4
Detección automática de conflictos
        ↓
V5
Configuración adaptativa según hardware
        ↓
Versiones futuras
Instalador gestionado de forma cada vez más autónoma
```

Este esquema es conceptual.

No representa un roadmap obligatorio.

---

# 59. Posible rol de agentes de IA

En el futuro, un sistema de IA suficientemente capaz podría actuar como un agente técnico del instalador.

Podría, por ejemplo:

- analizar errores del log;
- diagnosticar dependencias;
- detectar incompatibilidades;
- proponer reparaciones;
- seleccionar versiones compatibles;
- adaptar configuraciones según hardware;
- corregir instalaciones incompletas;
- generar informes de diagnóstico;
- preparar migraciones seguras;
- sugerir optimizaciones.

Estas funciones deberán diseñarse con límites claros y mecanismos de confirmación para cualquier acción que pueda afectar datos del usuario.

---

# 60. Regla de seguridad para mejoras autónomas

Una IA futura podrá aumentar el grado de automatización, pero no deberá ganar libertad ilimitada sobre el sistema del usuario.

Las acciones potencialmente destructivas deberán mantener mecanismos de:

- validación;
- confirmación;
- backups cuando corresponda;
- rollback cuando sea posible;
- registro;
- explicación.

La inteligencia adicional debe utilizarse para reducir errores, no para eliminar controles de seguridad.

---

# 61. Jerarquía de decisiones

Cuando una futura IA analice esta especificación, deberá aplicar esta jerarquía:

```text
1. Seguridad de los datos
2. Compatibilidad
3. Funcionamiento correcto
4. Experiencia del usuario
5. Mantenibilidad
6. Rendimiento
7. Automatización adicional
8. Nuevas funciones
```

Una mejora de velocidad o automatización nunca debe justificar un mayor riesgo de pérdida de datos.

---

# 62. Documento vivo

Esta especificación debe tratarse como un **documento vivo**.

Podrá evolucionar mediante nuevas versiones:

```text
PLAN_V2
PLAN_V2.1
PLAN_V3
...
```

Cada revisión deberá documentar:

- qué cambió;
- por qué cambió;
- qué decisiones anteriores se mantienen;
- qué decisiones fueron reemplazadas;
- nuevas capacidades;
- nuevos riesgos.

---

# 63. Instrucción final para futuras IAs

Una futura IA no debe limitarse a ejecutar literalmente este documento.

Debe utilizarlo como:

> **contexto histórico + requisitos mínimos + principios de seguridad + intención de producto.**

Después deberá aplicar su propia capacidad de razonamiento para encontrar una solución mejor si existe.

La pregunta que deberá hacerse antes de implementar será:

> **“¿Puedo cumplir todos los objetivos de este plan con una solución más simple, segura, robusta y preparada para el futuro?”**

Si la respuesta es sí, deberá proponer esa mejora antes de implementarla.

---

# 64. Visión de largo plazo

La meta no es simplemente tener un instalador que funcione hoy.

La meta es construir una base que pueda evolucionar con:

- nuevas generaciones de GPUs;
- nuevos modelos generativos;
- nuevas versiones de ComfyUI;
- nuevos sistemas operativos;
- nuevas herramientas de IA;
- nuevos gestores de dependencias;
- nuevas formas de distribución.

El instalador debe evolucionar sin perder su principio original:

> **hacer que una herramienta técnicamente compleja sea accesible para una persona que empieza desde cero.**


