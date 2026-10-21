# Seguridad

Este repositorio publica **datos públicos** (estadísticas oficiales y cálculos sobre ellas). No guarda
credenciales, no recibe datos de quienes lo usan y no necesita acceso a ninguna red interna.

## Qué hace y qué no hace

| | |
|---|---|
| Quién escribe | Solo el workflow *Actualizar series* (GitHub Actions) y los responsables del repositorio. |
| Qué escribe | Solo archivos dentro de `data/`; el workflow frena si hay cambios en otra carpeta. |
| Qué baja | Archivos de organismos públicos (INDEC, CAMMESA, Secretaría de Agricultura, Secretaría de Transporte, Seguridad Social) y el catálogo de Monitor Argy. Corre en los servidores de GitHub, no en equipos de la empresa. |
| Qué publica | CSV y Excel con números, fechas y nombres de series; JSON con metadatos; una página estática (`docs/`). |
| Qué hace quien consume | Solo **lee** por HTTPS archivos públicos. No envía datos, no usa usuario ni contraseña, no ejecuta código del repositorio. |

## Medidas en el repositorio

- **Acciones de GitHub fijadas por commit** (no por etiqueta, que se puede mover) y revisadas por Dependabot.
- **Dependencias de Python verificadas por huella**: `requirements.txt` lista cada paquete con su SHA-256 y el
  workflow instala con `--require-hashes --only-binary=:all:` (no compila ni ejecuta código de instalación).
  Las versiones se eligen con al menos dos semanas de publicadas.
- **Permisos mínimos**: los workflows arrancan sin permisos (`permissions: {}`) y solo el trabajo que guarda datos
  pide escritura sobre el contenido.
- **Sin credenciales mientras se procesan archivos de afuera**: el paso que baja y lee archivos corre sin token;
  el token de GitHub solo existe en el último paso, que hace el commit de `data/`.
- **Binario de X-13 verificado**: `bin/x13as` se ejecuta solo si coincide con su huella SHA-256
  (`pipeline/desest.py`).
- **Sin inyección de fórmulas**: los textos de `data/todas/series.csv` que empiezan con `=`, `+`, `-` o `@` se
  escapan para que una planilla no los tome como fórmulas.
- **Páginas sin terceros**: `docs/index.html` y `docs/explorar.html` no cargan scripts, fuentes ni imágenes externas;
  una política de seguridad de contenido (CSP) solo les permite leer `raw.githubusercontent.com`. No usan cookies ni
  analítica. La librería de gráficos (Apache ECharts 5.5.1, licencia Apache-2.0) está copiada en `docs/vendor/` con
  su huella SHA-256 en `docs/vendor/SHA256SUMS`, y solo se ejecutan scripts del mismo sitio.
- **Validación de datos**: cada fuente se controla antes de guardarse (períodos consecutivos, rangos, sumas,
  revisiones desproporcionadas). Si algo no cierra, no se toca esa fuente.

## Recomendaciones para usarlo dentro de una empresa

1. **Copia propia**: hacer un *fork* en la cuenta u organización de GitHub de la empresa, o bajar los CSV a un
   almacenamiento interno, y que las herramientas lean de ahí.
2. **Versión fija** para reportes que tienen que poder repetirse: usar una etiqueta o un commit en lugar de `main`.
3. **Power BI / Excel**: conexión anónima; orígenes `raw.githubusercontent.com` y `monitorargy.com` como
   **Público**; no usar "ignorar los niveles de privacidad"; tener estas consultas aparte de las que leen datos
   internos.
4. **Monitor Argy** es un tercero: si no se quiere depender de él, usar solo las series del repositorio.

## Configuración de GitHub (la hace el dueño del repositorio)

- Verificación en dos pasos en la cuenta.
- *Settings > Rules*: proteger `main` (sin force push ni borrado).
- *Settings > Actions > General*: permitir solo acciones de GitHub (`actions/*`); permisos del token por defecto
  en **solo lectura**; no permitir que Actions cree o apruebe pull requests; pedir aprobación para workflows de
  colaboradores externos.
- *Settings > Advanced Security*: activar alertas y actualizaciones de seguridad de Dependabot, escaneo de
  secretos con protección al subir, y reporte privado de vulnerabilidades.
- *Settings > Pages*: forzar HTTPS.
- Revisar periódicamente las aplicaciones con acceso a la cuenta (*Settings > Applications*).

## Reportar un problema

Usar *Security > Report a vulnerability* en GitHub (reporte privado). No abrir un issue público con detalles.
