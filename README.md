# monitor-series

Series económicas argentinas bajadas de sus fuentes oficiales, validadas y guardadas con historial.
Una tarea de GitHub Actions corre todos los días, revisa si cambió cada archivo de origen y, si cambió,
actualiza los datos y guarda la versión nueva.

## Series disponibles

| id | Serie | Fuente | Frecuencia | Desde |
|---|---|---|---|---|
| `emae` | EMAE total: índice original, desestacionalizado y tendencia-ciclo (base 2004=100), con la variación interanual de la original y las mensuales de las otras dos | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48) | Mensual | 2004-01 |
| `emae_letras` | EMAE por sector de actividad (letras A a O e impuestos netos de subsidios), serie original, base 2004=100 | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48) | Mensual | 2004-01 |
| `emae_letras_desest` | EMAE por sector, **desestacionalización propia** (X-13ARIMA-SEATS con calendario argentino) de las letras A, C, D, E, F, G, I y J, con su variación mensual. INDEC no las publica; ver [Desestacionalización propia](#desestacionalización-propia) | Cálculo propio sobre `emae_letras` | Mensual | 2004-01 |
| `ipc` | IPC: nivel general, 12 divisiones, núcleo, regulados, estacionales, bienes y servicios, para el total nacional y las 6 regiones; índice (dic-2016=100), variación mensual e interanual (378 series) | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31) | Mensual | 2016-12 |
| `ipi` | IPI manufacturero: nivel general (original, desestacionalizado y tendencia-ciclo, con variaciones), divisiones y subclases (original) y divisiones (desestacionalizadas, con variación mensual); base 2004=100 | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-6-14) | Mensual | 2016-01 |
| `isac` | ISAC: indicador sintético de la construcción (original, desestacionalizado y tendencia-ciclo, con variaciones) e insumos para la construcción (original y desestacionalizados); base 2004=100 | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-3-42) | Mensual | 2012-01 |
| `ripte` | RIPTE: remuneración imponible promedio de los trabajadores estables, en pesos corrientes, con su variación mensual, el índice base 07/1994=100 y el índice no decreciente | [Subsecretaría de Seguridad Social](https://www.argentina.gob.ar/trabajo/seguridadsocial/ripte) | Mensual | 1994-07 |
| `ripte_real` | RIPTE real, deflactado por el IPC nacional: a precios de diciembre de 2016 (como Monitor Argy) y a precios del último IPC publicado, con variación mensual e interanual | Cálculo propio sobre `ripte` e `ipc` | Mensual | 2016-12 |
| `salarios` | Índice de salarios: sector privado registrado, público, total registrado, privado no registrado e índice total (base oct-2016=100), con variaciones mensual e interanual calculadas desde los índices | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-31-61) | Mensual | 2015-10 (no registrado y total, 2016-10) |
| `salarios_real` | Índice de salarios real: cada índice deflactado por el IPC nacional (como Monitor Argy), con variaciones mensual e interanual | Cálculo propio sobre `salarios` e `ipc` | Mensual | 2016-12 |
| `sube` | SUBE: transacciones (usos) por **día**: total, AMBA, interior, colectivos, trenes, subte, lanchas y colectivos del AMBA. Los últimos meses son preliminares (la fecha desde la que lo son está en `data/meta/sube.json`); la cobertura del interior crece con los años, así que el total y el interior no son del todo comparables entre años | [Secretaría de Transporte](https://datos.transporte.gob.ar/dataset/sube-cantidad-de-transacciones-usos-por-fecha) | Diaria | 2020-01-01 |
| `sube_mensual` | SUBE por mes (solo meses completos): transacciones del mes, promedio diario y variación interanual de cada serie de `sube` | Cálculo propio sobre `sube` | Mensual | 2020-01 |
| `supermercados` | Encuesta de supermercados: índice de ventas a precios constantes (original, desestacionalizado y tendencia-ciclo, con variaciones) y ventas totales a precios corrientes y constantes (millones de $) | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-1-34) | Mensual | 2017-01 |

El estado de cada serie está en [`data/catalogo.csv`](data/catalogo.csv): último período, fecha de descarga,
próxima publicación según el calendario de INDEC y si está **al día**, **se publica hoy** o **demorado**.

## Dónde están los datos

| Archivo | Contenido |
|---|---|
| `data/<id>.csv` | La serie: columna `fecha` (primer día del período, AAAA-MM-DD) y una columna por variable. Punto decimal, UTF-8. |
| `data/excel/<id>.xlsx` | Lo mismo en Excel, con los nombres completos de cada columna. |
| `data/meta/<id>.json` | Fuente, URL del archivo, huella del archivo, fecha de descarga y último período. |
| `data/revisiones/<id>.csv` | Cada valor que el organismo corrigió hacia atrás: período, serie, valor anterior y nuevo. |
| `data/raw/<id>/` | El archivo original tal como se bajó, una copia por cada versión con datos distintos. |
| `data/todas/valores.csv` | Todas las series juntas en formato largo: `fecha`, `id_serie`, `valor`. |
| `data/calendario/indec.csv` | Calendario de difusión de INDEC (fecha y título de cada publicación), leído del PDF semestral. |
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

## Desestacionalización propia

`emae_letras_desest` se recalcula sola cada vez que cambia `emae_letras`, en la misma corrida de GitHub
Actions. Usa el programa oficial de la Oficina del Censo de EE.UU., X-13ARIMA-SEATS 1.1 (compilación 57),
que está en `bin/x13as`; el código es `pipeline/desest.py` y las especificaciones,
`pipeline/fuentes/emae_letras_desest.py`.

**Método** (el mismo que usa Monitor Argy, calibrado contra sus series publicadas):

- modelo regARIMA con especificación fija por letra (orden ARIMA, transformación y outliers);
- días de la semana: regresores estándar de X-13, que se quitan de la serie;
- feriados: cantidad de feriados nacionales en días hábiles del mes (con traslados; sin Jueves Santo,
  puentes turísticos ni feriados únicos), centrada por mes calendario; Pascua: `easter[8]`;
- el efecto de feriados y Pascua se estima pero **queda en la serie desestacionalizada**, como en Monitor Argy;
- descomposición X-11 (tabla D11).

**Especificaciones:**

| Letra | Modelo | Transf. | Outliers | Origen |
|---|---|---|---|---|
| A agro | (2 0 0)(0 1 1) | log | LS 2009-04, 2009-07, 2018-04, 2018-07, 2023-04, 2023-07 | Monitor Argy |
| C minería | (0 1 1)(0 1 1) | niveles | AO 2008-05, 2009-08, 2010-12; LS 2011-04, 2020-04 | Monitor Argy |
| D industria | (3 1 1)(0 1 1) | niveles | LS 2020-03, 2020-06, 2024-07 | Monitor Argy |
| F construcción | (0 1 2)(0 1 1) | niveles | LS 2020-03, 2020-07, 2020-10, 2024-01; AO 2020-04, 2020-05, 2021-05 | Monitor Argy |
| E electricidad, gas y agua | (0 1 2)(0 1 1) | log | — | propia |
| G comercio | (0 1 3)(0 1 1) | log | TC 2020-03, 2020-04; LS 2024-07 | propia |
| I transporte y comunicaciones | (1 1 0)(0 1 1) | niveles | LS 2020-03, 2020-07; TC 2020-04 | propia |
| J intermediación financiera | (0 1 0)(0 1 1) | log | AO 2025-09 | propia |

Las propias salen de la selección automática de X-13 (modelo, transformación, outliers y prueba AIC de
días de la semana y Pascua: en las cuatro, Pascua no resultó significativa) sobre 2004-01 a 2026-07, con
controles de calidad (M7, Q, estacionalidad residual y autocorrelación de los residuos, Ljung-Box).
En comercio el modelo automático dejaba autocorrelación y se eligió el de mejor AICc sin ella.
Quedan fijas; conviene revisarlas una vez por año.

**Diferencia con Monitor Argy** en A, C, D y F (2004-01 a 2026-07): en la variación mensual, entre 0,06 y
0,2 puntos porcentuales en promedio (minería 0,06; agro 0,16; construcción 0,17; industria 0,20). No es cero:
Monitor Argy no publica su lista exacta de feriados y la diferencia viene, sobre todo, de ahí.

Como en cualquier desestacionalización, con cada dato nuevo se reestima el modelo y se revisan los meses
anteriores (no se registran en `data/revisiones/`). El modelo, los coeficientes de feriados, Pascua y días de
la semana, los outliers y los indicadores de calidad de cada letra quedan en
[`data/meta/emae_letras_desest.json`](data/meta/emae_letras_desest.json).

## Cuándo corre

La programación sigue el calendario de difusión de INDEC, que publica a las 16:00:

| Horario (Buenos Aires) | Qué hace |
|---|---|
| Días hábiles 16:40, 17:10, 17:40, 18:10 y 18:40 | **Modo calendario.** Si INDEC prevé publicar ese día alguna de las series, baja solo esas, hasta que entre el dato nuevo. Si no hay nada previsto, termina en segundos. El primer intento es 40 minutos después de las 16 porque a esa hora la página de INDEC suele saturarse; si falla la descarga, no cuenta como error y se reintenta en la siguiente. |
| Todas las noches 21:47 | **Control completo.** Actualiza el calendario (semestre actual y siguiente, cuando INDEC lo publica), revisa todas las fuentes para atrapar revisiones o publicaciones fuera de calendario, y **termina en error** si una publicación prevista para el día no entró. |

La SUBE se actualiza casi todos los días y entra en el control de cada noche; solo se baja el archivo del
año en curso (unos 50 MB), y la historia de años anteriores queda en `data/sube.csv`.

El RIPTE no está en el calendario de INDEC: se publica sin fecha fija (en general, unos dos meses después
del mes de referencia) y entra en el control de cada noche.

GitHub puede demorar las tareas programadas, a veces más de una hora, según su carga.

Para que una fuente siga el calendario, su módulo define `CALENDARIO` con el comienzo del título con que
figura en el PDF de INDEC (por ejemplo, `"Estimador mensual de actividad económica"`).

## Uso

**Correrlo a mano en GitHub:** pestaña *Actions* > *Actualizar series* > *Run workflow*.
Se puede elegir el modo (*completo* o *calendario*); la opción *forzar* procesa el archivo aunque no haya cambiado.

**Correrlo en tu computadora:**

```bash
pip install -r requirements.txt
python -m pipeline.actualizar               # control completo
python -m pipeline.actualizar --modo calendario   # solo lo que INDEC publica hoy
python -m pipeline.actualizar emae_letras   # una sola
python -m pipeline.actualizar --forzar
```

**Si falla:** GitHub marca la ejecución en rojo en la pestaña *Actions* y, según tu configuración de
notificaciones, te avisa por mail. El detalle del error figura en el paso *Bajar, validar y procesar*.

## Agregar una serie nueva

**Para ver la estructura de un archivo nuevo:** pestaña *Actions* > *Inspeccionar archivo de origen* > *Run workflow*,
con la URL del archivo. La descripción (hojas, encabezados, primeras y últimas filas) queda en la rama `inspeccion`.

Cada fuente es un módulo en `pipeline/fuentes/` con:

- `ID`, `NOMBRE`, `URL`, `PAGINA`, `EXTENSION`, `FRECUENCIA`, `UNIDAD`, `ORGANISMO`, `CALENDARIO`
- `COLUMNAS` (las series, con `Columna`) o, si dependen del archivo, `columnas(contenido)`
- `leer(contenido, columnas) -> DataFrame` con la columna `fecha` y una columna por serie
- `validar(nuevo, anterior, columnas) -> list[str]` con los errores encontrados
- opcional, `urls(hoy)` si el nombre del archivo cambia (p. ej. lleva el año): se prueba cada URL en orden

Los cuadros de INDEC con varias filas de encabezado se describen por el "camino" de encabezados de cada
columna, por ejemplo `"Serie original | Variación porcentual | respecto al mismo mes"` (ver `ipi.py`).
Para cuadros anchos (divisiones, insumos), `columnas_por_encabezado` arma una serie por columna; si INDEC
agrega, quita o renombra una, la actualización frena.

Después se suma a la lista `FUENTES` de `pipeline/actualizar.py`. Para los cuadros mensuales de INDEC,
`pipeline/fuentes/_indec.py` ya resuelve la lectura y la validación: alcanza con describir las columnas
(ver `emae.py` y `emae_letras.py`). En las variaciones que publica el organismo, el pipeline las recalcula
desde los índices y frena si no coinciden.

## Licencia de los datos

Los datos pertenecen a los organismos que los publican. Citá la fuente original de cada serie.
