# monitor-series

Series económicas argentinas bajadas de sus fuentes oficiales, validadas y guardadas con historial.
Una tarea de GitHub Actions corre todos los días, revisa si cambió cada archivo de origen y, si cambió,
actualiza los datos y guarda la versión nueva.

## Series disponibles

| id | Serie | Fuente | Frecuencia | Desde |
|---|---|---|---|---|
| `emae_letras` | EMAE por sector de actividad (letras A a O e impuestos netos de subsidios), serie original, base 2004=100 | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48) | Mensual | 2004-01 |

El estado de cada serie (último período, fecha de descarga) está en [`data/catalogo.csv`](data/catalogo.csv).

## Dónde están los datos

| Archivo | Contenido |
|---|---|
| `data/<id>.csv` | La serie: columna `fecha` (primer día del período, AAAA-MM-DD) y una columna por variable. Punto decimal, UTF-8. |
| `data/excel/<id>.xlsx` | Lo mismo en Excel, con los nombres completos de cada columna. |
| `data/meta/<id>.json` | Fuente, URL del archivo, huella del archivo, fecha de descarga y último período. |
| `data/revisiones/<id>.csv` | Cada valor que el organismo corrigió hacia atrás: período, serie, valor anterior y nuevo. |
| `data/raw/<id>/` | El archivo original tal como se bajó, una copia por cada versión con datos distintos. |

> Para abrir los CSV en un Excel configurado en español, usá *Datos > Desde texto/CSV* y elegí el punto
> como separador decimal; o abrí directamente el archivo de `data/excel/`.

## Cómo funciona

Para cada fuente, `python -m pipeline.actualizar`:

1. **Baja el archivo** de la URL oficial.
2. **Compara su huella** (SHA-256) con la de la última versión. Si es igual, no hace nada.
3. **Lo lee buscando los encabezados por su texto**, no por posición fija, para tolerar cambios menores de formato.
4. **Valida** antes de guardar: columnas completas, meses consecutivos, sin vacíos, valores en rango,
   que no se pierda historia, que las revisiones no sean desproporcionadas y que los meses nuevos no tengan
   saltos absurdos contra el mismo mes del año anterior.
5. Si todo está bien, **guarda** el CSV, el Excel, el original y el registro de revisiones.
   Si algo falla, **no toca nada de esa fuente** y la tarea termina en error.

## Uso

**Correrlo a mano en GitHub:** pestaña *Actions* > *Actualizar series* > *Run workflow*.
La opción *forzar* procesa el archivo aunque no haya cambiado.

**Correrlo en tu computadora:**

```bash
pip install -r requirements.txt
python -m pipeline.actualizar               # todas las fuentes
python -m pipeline.actualizar emae_letras   # una sola
python -m pipeline.actualizar --forzar
```

**Si falla:** GitHub marca la ejecución en rojo en la pestaña *Actions* y, según tu configuración de
notificaciones, te avisa por mail. El detalle del error figura en el paso *Bajar, validar y procesar*.

## Agregar una serie nueva

Cada fuente es un módulo en `pipeline/fuentes/` con:

- `ID`, `NOMBRE`, `URL`, `PAGINA`, `EXTENSION`, `FRECUENCIA`, `UNIDAD`
- `leer(contenido: bytes) -> DataFrame` con la columna `fecha` y una columna por variable
- `validar(nuevo, anterior) -> list[str]` con los errores encontrados

Después se suma a la lista `FUENTES` de `pipeline/actualizar.py`. `emae_letras.py` sirve de modelo.

## Licencia de los datos

Los datos pertenecen a los organismos que los publican. Citá la fuente original de cada serie.
