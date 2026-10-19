# monitor-series

Series económicas argentinas bajadas de sus fuentes oficiales, validadas y guardadas con historial.
Una tarea de GitHub Actions corre todos los días, revisa si cambió cada archivo de origen y, si cambió,
actualiza los datos y guarda la versión nueva.

## Series disponibles

| id | Serie | Fuente | Frecuencia | Desde |
|---|---|---|---|---|
| `emae` | EMAE total: índice original, desestacionalizado y tendencia-ciclo (base 2004=100), con la variación interanual de la original y las mensuales de las otras dos | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48) | Mensual | 2004-01 |
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
| `data/todas/valores.csv` | Todas las series juntas en formato largo: `fecha`, `id_serie`, `valor`. |
| `data/todas/series.csv` | Una fila por serie: `id_serie`, nombre, tipo (nivel o variación), unidad, frecuencia, fuente, primer y último período. |

> Para abrir los CSV en un Excel configurado en español, usá *Datos > Desde texto/CSV* y elegí el punto
> como separador decimal; o abrí directamente el archivo de `data/excel/`.

## Conectar Power BI, Excel, Google Sheets o Python

Cada archivo tiene un link fijo que siempre apunta a la última versión:

```
https://raw.githubusercontent.com/rodrigotperelsztein-source/monitor-series/main/data/<archivo>
```

Por ejemplo `.../main/data/todas/valores.csv` o `.../main/data/emae.csv`.

### Power BI

Lo más cómodo es usar el formato largo: dos consultas y una relación, y las series nuevas aparecen solas.

1. *Obtener datos > Consulta en blanco > Editor avanzado* y pegar cada consulta:

**Series**
```
let
    Origen = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/rodrigotperelsztein-source/monitor-series/main/data/todas/series.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Tabla = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Tabla,
        {{"primer_periodo", type date}, {"ultimo_periodo", type date}}, "en-US")
in
    Tipos
```

**Valores**
```
let
    Origen = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/rodrigotperelsztein-source/monitor-series/main/data/todas/valores.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Tabla = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Tabla,
        {{"fecha", type date}, {"id_serie", type text}, {"valor", type number}}, "en-US")
in
    Tipos
```

2. En el modelo, relacionar `Series[id_serie]` (uno) con `Valores[id_serie]` (varios).
3. Un segmentador con `Series[serie]` elige qué series ver; un gráfico de líneas con `Valores[fecha]` en el eje y `Valores[valor]` como valor.
4. Al publicar en el servicio de Power BI, configurar la actualización programada con acceso **anónimo**
   (no hace falta gateway). Conviene programarla a la noche: el pipeline corre a la tarde.

El `"en-US"` del final de cada consulta hace que el punto se lea como separador decimal aunque
Power BI esté en español.

### Excel

*Datos > Desde la web* y pegar el link del CSV. Al cargar, en *Transformar datos*, cambiar el tipo de las
columnas numéricas con *Cambiar tipo > Usar configuración regional > Inglés (Estados Unidos)*.
Después se actualiza con *Datos > Actualizar todo*.

### Google Sheets

```
=IMPORTDATA("https://raw.githubusercontent.com/rodrigotperelsztein-source/monitor-series/main/data/emae.csv")
```

Si la hoja está en español y los números aparecen como texto, cambiar la configuración regional de la hoja a
Estados Unidos (*Archivo > Configuración*).

### Python

```python
import pandas as pd
base = "https://raw.githubusercontent.com/rodrigotperelsztein-source/monitor-series/main/data/"
valores = pd.read_csv(base + "todas/valores.csv", parse_dates=["fecha"])
tabla = valores.pivot(index="fecha", columns="id_serie", values="valor")
```

## Cómo funciona

Para cada fuente, `python -m pipeline.actualizar`:

1. **Baja el archivo** de la URL oficial.
2. **Compara su huella** (SHA-256) con la de la última versión. Si es igual, no hace nada.
3. **Lo lee buscando los encabezados por su texto**, no por posición fija, para tolerar cambios menores de formato.
4. **Valida** antes de guardar: columnas completas, meses consecutivos, sin vacíos, valores en rango,
   que no se pierda historia, que las revisiones no sean desproporcionadas y que los meses nuevos no tengan
   saltos absurdos contra el mismo mes del año anterior.
5. Si todo está bien, **guarda** el CSV, el Excel, el original y el registro de revisiones, y regenera
   los archivos de `data/todas/` con todas las series juntas.
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

**Para ver la estructura de un archivo nuevo:** pestaña *Actions* > *Inspeccionar archivo de origen* > *Run workflow*,
con la URL del archivo. La descripción (hojas, encabezados, primeras y últimas filas) queda en la rama `inspeccion`.

Cada fuente es un módulo en `pipeline/fuentes/` con:

- `ID`, `NOMBRE`, `URL`, `PAGINA`, `EXTENSION`, `FRECUENCIA`, `UNIDAD`
- `leer(contenido: bytes) -> DataFrame` con la columna `fecha` y una columna por variable
- `validar(nuevo, anterior) -> list[str]` con los errores encontrados

Después se suma a la lista `FUENTES` de `pipeline/actualizar.py`. Para los cuadros mensuales de INDEC,
`pipeline/fuentes/_indec.py` ya resuelve la lectura y la validación: alcanza con describir las columnas
(ver `emae.py` y `emae_letras.py`). En las variaciones que publica el organismo, el pipeline las recalcula
desde los índices y frena si no coinciden.

## Licencia de los datos

Los datos pertenecen a los organismos que los publican. Citá la fuente original de cada serie.
