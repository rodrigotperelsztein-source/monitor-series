# monitor-series

Series económicas argentinas bajadas de sus fuentes oficiales, validadas y guardadas con historial.
Una tarea de GitHub Actions corre todos los días, revisa si cambió cada archivo de origen y, si cambió,
actualiza los datos y guarda la versión nueva.

**Monitor Argy.** Las páginas de este repositorio también disponibilizan las series de
[Monitor Argy](https://monitorargy.com), un sitio que publica indicadores macroeconómicos argentinos con una API
abierta. Esas series no se procesan acá: se leen de su API tal como las publica (con el prefijo `ma:` en el selector),
y su origen es Monitor Argy y los organismos que cita en cada serie. Además, la desestacionalización propia del EMAE por
sector replica su método. Gracias a Monitor Argy por abrir sus datos.

## Series disponibles

| id | Serie | Fuente | Frecuencia | Desde |
|---|---|---|---|---|
| `canastas` | Canasta básica alimentaria (CBA, línea de indigencia) y total (CBT, línea de pobreza), GBA: por adulto equivalente con variaciones mensual e interanual, para los tres hogares tipo y la inversa del coeficiente de Engel. Solo por la API del INDEC | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-43-149) | Mensual | 2016-04 |
| `gas_entregado` | **ENARGAS**: gas natural entregado a usuarios finales (miles de m³ de 9.300 kcal), total y por tipo de usuario (residencial, comercial, entes oficiales, industria, centrales, GNC, subdistribuidores, RTP, exportaciones); GNC por día, var. interanual y por área de licencia (Metrogas, Naturgy BAN, Camuzzi Pampeana y Sur, Litoral, Ecogas Centro y Cuyana, Gasnor, GasNEA, Redengas). Se lee la base de la tabla dinámica de la planilla | [ENARGAS](https://www.enargas.gob.ar/secciones/transporte-y-distribucion/datos-operativos.php) | Mensual | 1993-01 |
| `emae` | EMAE total: índice original, desestacionalizado y tendencia-ciclo (base 2004=100), con la variación interanual de la original y las mensuales de las otras dos | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48) | Mensual | 2004-01 |
| `emae_letras` | EMAE por sector de actividad (letras A a O e impuestos netos de subsidios), serie original, base 2004=100 | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48) | Mensual | 2004-01 |
| `emae_letras_desest` | EMAE por sector, **desestacionalización propia** (X-13ARIMA-SEATS con calendario argentino) de las letras A, C, D, E, F, G, I y J, con su variación mensual. INDEC no las publica; ver [Desestacionalización propia](#desestacionalización-propia) | Cálculo propio sobre `emae_letras` | Mensual | 2004-01 |
| `ipc` | IPC: nivel general, 12 divisiones, núcleo, regulados, estacionales, bienes y servicios, para el total nacional y las 6 regiones; índice (dic-2016=100), variación mensual e interanual (378 series) | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31) | Mensual | 2016-12 |
| `ipi` | IPI manufacturero: nivel general (original, desestacionalizado y tendencia-ciclo, con variaciones), divisiones y subclases (original) y divisiones (desestacionalizadas, con variación mensual); base 2004=100 | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-6-14) | Mensual | 2016-10 |
| `ipi_minero` | IPI minero: nivel general (original, desestacionalizado de INDEC y tendencia-ciclo, con variaciones), 46 aperturas por categoría, división, grupo y producto (original), y extracción de petróleo y gas (convencional y no convencional) y de carbonato de litio en unidades físicas; base 2016=100 | [INDEC](https://www.indec.gob.ar/Nivel4/Tema/3/7/172) | Mensual | 2017-01 |
| `ipi_minero_desest` | IPI minero: 16 aperturas y 6 series de petróleo y gas en unidades físicas, desestacionalizadas con X-13 (propia), con variación mensual | Cálculo propio sobre `ipi_minero` | Mensual | 2017-01 |
| `isac` | ISAC: indicador sintético de la construcción (original, desestacionalizado y tendencia-ciclo, con variaciones) e insumos para la construcción (original y desestacionalizados); base 2004=100 | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-3-42) | Mensual | 2012-01 |
| `ripte` | RIPTE: remuneración imponible promedio de los trabajadores estables, en pesos corrientes, con su variación mensual, el índice base 07/1994=100 y el índice no decreciente | [Subsecretaría de Seguridad Social](https://www.argentina.gob.ar/trabajo/seguridadsocial/ripte) | Mensual | 1994-07 |
| `ripte_real` | RIPTE real, deflactado por el IPC nacional: a precios de diciembre de 2016 (como Monitor Argy) y a precios del último IPC publicado, con variación mensual e interanual | Cálculo propio sobre `ripte` e `ipc` | Mensual | 2016-12 |
| `salarios` | Índice de salarios: sector privado registrado, público, total registrado, privado no registrado e índice total (base oct-2016=100), con variaciones mensual e interanual calculadas desde los índices | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-31-61) | Mensual | 2015-10 (no registrado y total, 2016-10) |
| `salarios_real` | Índice de salarios real: cada índice deflactado por el IPC nacional (como Monitor Argy), con variaciones mensual e interanual | Cálculo propio sobre `salarios` e `ipc` | Mensual | 2016-12 |
| `remuneraciones_provincias` | Remuneración promedio de los asalariados registrados del sector privado por provincia y total país, por todo concepto (incluye aguinaldo), pesos corrientes. Hoja "Total" de la planilla del OEDE (SIPA); el nombre del archivo cambia y se busca en la página | [OEDE, Secretaría de Trabajo](https://www.argentina.gob.ar/trabajo/estadisticas/oede-estadisticas-provinciales) | Mensual | 1995-01 |
| `remuneraciones_provincias_real` | La anterior deflactada por el IPC nacional, a precios del último IPC publicado (se reescala con cada IPC nuevo), y la variación interanual real del total país | Cálculo propio sobre `remuneraciones_provincias` e `ipc` | Mensual | 2016-12 |
| `remuneraciones_provincias_desest` | `remuneraciones_provincias` desestacionalizada (X-13 en logaritmos, modelo y outliers automáticos, sin efectos de calendario, desde 2007-01): reparte el aguinaldo de junio y diciembre. Más la variación mensual del total país | Cálculo propio sobre `remuneraciones_provincias` | Mensual | 2007-01 |
| `remuneraciones_provincias_real_desest` | `remuneraciones_provincias_real` desestacionalizada con el mismo método, a precios del último IPC, con la variación mensual real del total país | Cálculo propio sobre `remuneraciones_provincias_real` | Mensual | 2016-12 |
| `salarios_ramas` | Remuneración promedio de los asalariados registrados privados por rama de actividad (17 sectores, más petróleo y gas, refinación, venta de combustibles y transporte terrestre), total del país, y la de petróleo y gas en 8 provincias; pesos corrientes. El total del país de cada rama pondera las provincias por su empleo en la rama | [OEDE, SIPA](https://www.argentina.gob.ar/trabajo/estadisticas/oede-estadisticas-provinciales) | Mensual | 1996-01 |
| `empleo_ramas` | Puestos de trabajo asalariados registrados privados por rama (las mismas ramas), total del país, con la participación de cada rama en el total; y los de petróleo y gas en 8 provincias | [OEDE, SIPA](https://www.argentina.gob.ar/trabajo/estadisticas/oede-estadisticas-provinciales) | Trimestral | 1996-T1 |
| `salarios_ramas_real` | `salarios_ramas` a precios del último IPC, con variación interanual real | Cálculo propio sobre `salarios_ramas` e `ipc` | Mensual | 2016-12 |
| `sube` | SUBE: transacciones (usos) por **día**: total, AMBA, interior, colectivos, trenes, subte, lanchas y colectivos del AMBA. Los últimos meses son preliminares (la fecha desde la que lo son está en `data/meta/sube.json`); la cobertura del interior crece con los años, así que el total y el interior no son del todo comparables entre años | [Secretaría de Transporte](https://datos.transporte.gob.ar/dataset/sube-cantidad-de-transacciones-usos-por-fecha) | Diaria | 2020-01-01 |
| `sube_mensual` | SUBE por mes (solo meses completos): transacciones del mes, promedio diario y variación interanual de cada serie de `sube` | Cálculo propio sobre `sube` | Mensual | 2020-01 |
| `sube_desest` | SUBE por mes **desestacionalizada** (X-13, propia): total, AMBA, interior, colectivo, tren y subte, con su variación mensual. Ver [SUBE desestacionalizada](#sube-desestacionalizada) | Cálculo propio sobre `sube_mensual` | Mensual | 2020-01 |
| `petroleo` | Petróleo **Brent** y **WTI**: precio spot de cierre de cada día y diferencial, en dólares por barril. Historia de las planillas de la EIA (semanales) más el último cierre de su página diaria, que se baja los días hábiles a las 10:10 | [EIA](https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm) (datos de Refinitiv) | Diaria | 1986-01 (WTI), 1987-05 (Brent) |
| `petroleo_mensual` | Brent y WTI: promedio del mes, variación mensual e interanual, diferencial (solo meses cerrados) | Cálculo propio sobre `petroleo` | Mensual | 1986-01 |
| `refinados` | Precios internacionales de **naftas y gasoil** (spot EE.UU., dólares por galón): nafta convencional NY y Costa del Golfo, RBOB Los Ángeles, heating oil NY, gasoil ULSD NY y Costa del Golfo, desde 1986/2006; RBOB NY, RBOB Golfo y heating oil Golfo solo desde oct-2026 (página diaria). Los futuros NYMEX RBOB/HO no se publican libremente desde abril de 2024 | [EIA](https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm) (datos de Refinitiv) | Diaria | 1986-06 |
| `refinados_mensual` | Promedio del mes de las series de `refinados` con historia, con variación mensual e interanual | Cálculo propio sobre `refinados` | Mensual | 1986-06 |
| `acciones_energia` | Acciones de YPF (YPF), Vista Energy (VIST), Pampa Energía (PAM) y TGS (TGS) en Nueva York: cierre diario en dólares, sin ajustar por dividendos (Nasdaq da los últimos 10 años; desde ahí se acumula) | [Nasdaq](https://www.nasdaq.com/market-activity/stocks/ypf/historical) | Diaria | 2016-10 |
| `acciones_energia_mensual` | Las mismas acciones: cierre de fin de mes, con variación mensual e interanual | Cálculo propio sobre `acciones_energia` | Mensual | 2016-10 |
| `came` | **CAME**: ventas minoristas pyme (desde 2018-09) y producción industrial pyme (IPIP, desde 2025-03), variación % interanual. CAME no publica tablas: se leen sus informes de prensa mensuales; la historia se reconstruyó desde su archivo | [CAME](https://www.redcame.org.ar/estadisticas-pyme/78/ndice-de-ventas-minoristas) | Mensual | 2018-09 |
| `estimaciones_agricolas` | **Secretaría de Agricultura**: superficie implantada y producción estimada de trigo, maíz, soja y girasol para la campaña en curso (informe mensual de Estimaciones Agrícolas, en PDF), más una producción con rendimiento tendencial (mediana de las últimas cinco campañas del informe semanal). Se revisa del 12 a fin de mes | [Estimaciones Agrícolas](https://www.magyp.gob.ar/sitio/areas/estimaciones/estimaciones/informes/) | Mensual | 2026-10 |
| `itcrm` | **BCRA**: tipo de cambio real multilateral (ITCRM) y bilaterales con Brasil, Estados Unidos, China, zona del euro y otros 10 socios, base 17-12-2015=100. Si sube, el peso se deprecia en términos reales. Los últimos meses son provisorios (inflación estimada) | [BCRA, ITCRM](https://www.bcra.gob.ar/indices-de-tipo-de-cambio-multilateral/) | Diaria | 1997-01 |
| `itcrm_mensual` | Los mismos índices, promedio mensual publicado por el BCRA, con variación mensual e interanual | [BCRA, ITCRM](https://www.bcra.gob.ar/indices-de-tipo-de-cambio-multilateral/) | Mensual | 1997-01 |
| `precios_mayoristas` | Precios mayoristas (SIPM): IPIM, IPIB e IPP (dic-2015=100), nivel general, nacionales e importados, primarios, manufacturados y energía eléctrica, petróleo crudo y gas natural y productos refinados del petróleo; índice y variaciones mensual e interanual del INDEC. Solo por la API del INDEC | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-32) | Mensual | 2015-12 |
| `rem` | **BCRA**: Relevamiento de Expectativas de Mercado (mediana): inflación mensual, a 12 meses y del año; TAMAR; tipo de cambio; PIB trimestral (trimestre anterior, actual y siguiente) y anual; desocupación; exportaciones e importaciones; resultado primario. Una fila por encuesta, con horizontes contados desde el mes de la encuesta | [BCRA, REM](https://www.bcra.gob.ar/PublicacionesEstadisticas/Relevamiento_Expectativas_de_Mercado.asp) | Mensual | 2016-06 |
| `ventas_combustibles` | Ventas al mercado de **gasoil y naftas grado 2 y grado 3** (y gasoil y naftas en total), por empresa (YPF, Shell, Axion, Trafigura, DAPSA, Delta/Gulf, Refinor, resto) y total del mercado; cada serie también **sin usinas eléctricas ni bunker internacional**. También por canal de venta (al público, transporte de carga, agro, transporte de pasajeros, otras empresas), total del mercado. Incluye ventas a otras empresas del sector. Se leen los registros guardados en las tablas dinámicas. Se revisa del 20 a fin de cada mes | [Secretaría de Energía](https://www.argentina.gob.ar/economia/energia/hidrocarburos/refinacion-y-comercializacion-de-petroleo-gas-y-derivados-tablas-dinamicas) (SESCO, Res. 1104/04) | Mensual | 2010-01 |
| `ventas_combustibles_desest` | Ventas de gasoil y naftas del total del mercado **desestacionalizadas** (X-13, propia): gasoil total, G2, G3 y total sin usinas ni bunker; naftas total, G2 y G3; y gasoil y naftas (G2 + G3) de YPF, Shell, Axion, Trafigura (desde 2019) y Refinor; con variación mensual. Se quitan días de la semana y feriados. DAPSA y Delta/Gulf no se ajustan (sin estacionalidad estable) | Cálculo propio sobre `ventas_combustibles` | Mensual | 2010-01 |
| `camiones_puertos` | Entrada **diaria** de camiones con granos a puertos, fábricas y molinos: total, por zona portuaria (Rosario y aledaños, Dársena Buenos Aires–Entre Ríos, Necochea, Bahía Blanca), por producto (trigo, maíz, sorgo, cebada, soja, girasol) y vagones. Los días sin informe figuran en cero | [Secretaría de Agricultura](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/logistica/_archivos/000023_Posici%C3%B3n%20de%20Camiones%20y%20Vagones/000020_Entrada%20diaria%20de%20camiones%20y%20vagones%20a%20puertos,%20f%C3%A1bricas%20y%20molinos%20(por%20zona%20portuaria%20y%20por%20producto).php), con datos de Williams Entregas | Diaria | 2024-01-01 |
| `camiones_puertos_mensual` | Lo mismo por mes (solo meses completos), con variación interanual | Cálculo propio sobre `camiones_puertos` | Mensual | 2024-01 |
| `cammesa_balance` | Balance mensual de energía del Mercado Eléctrico Mayorista (GWh): demanda de distribuidoras, grandes usuarios, exportación, bombeo, consumos internos y pérdidas; generación térmica, nuclear, renovable, hidráulica e importación. `demanda_mercado` (distribuidoras + grandes usuarios) es la "demanda eléctrica" de Monitor Argy, con variación interanual. El archivo de CAMMESA trae desde 2023; la historia se va acumulando | [CAMMESA](https://cammesaweb.cammesa.com/informe-sintesis-mensual/) | Mensual | 2023-01 |
| `cammesa_gu_actividad` | Demanda **diaria** de los grandes usuarios del MEM (GUMA) por actividad, en MW medios del día: alimentación, comercios y servicios (cargas y puertos, comercio y servicios, industria de la alimentación, servicios públicos y transporte); industrias (automotriz, derivados de petróleo, construcción, madera y papel, metálicos no automotores, textil, químicas, gran siderurgia); petróleo y minerales (extracción de minerales y de petróleo); Aluar; total. Incluye si el día es hábil. Datos provisorios de CAMMESA, que se reemplazan cada semana | [CAMMESA](https://cammesaweb.cammesa.com/2026/10/16/covid-19-comportamiento-de-la-demanda-de-energia-electrica-en-el-mem/), Base de datos GU Semanal, hoja "Base Detalle diaria GUMAs ACT" | Diaria | 2022-01-01 |
| `cammesa_gu_actividad_mensual` | Lo mismo por mes (solo meses completos): media de días hábiles (el indicador de CAMMESA) con variación interanual, y media de todos los días | Cálculo propio sobre `cammesa_gu_actividad` | Mensual | 2022-01 |
| `cammesa_diaria` | Demanda eléctrica **diaria** del MEM en MW medios del día: total, grandes usuarios (autogeneradores + GUMAs) y distribuidoras, con la temperatura media de GBA y si el día es hábil. Datos provisorios de CAMMESA, que se reemplazan cada semana | [CAMMESA](https://cammesaweb.cammesa.com/2026/10/16/covid-19-comportamiento-de-la-demanda-de-energia-electrica-en-el-mem/), Base de datos GU Semanal, hoja "Base diaria" | Diaria | 2022-01-01 |
| `supermercados` | Encuesta de supermercados: índice de ventas a precios constantes (original, desestacionalizado y tendencia-ciclo, con variaciones) y ventas totales a precios corrientes y constantes (millones de $) | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-1-34) | Mensual | 2017-01 |
| `bcra` | **BCRA** (API pública de estadísticas v4): reservas, tipo de cambio mayorista y minorista, bandas cambiarias, base monetaria, M2, depósitos, préstamos por línea, tasas (TAMAR, BADLAR, plazo fijo, adelantos, personales), pases, CER, UVA, ICL y factores de explicación de la base monetaria | [BCRA, API](https://www.bcra.gob.ar/PublicacionesEstadisticas/Principales_variables.asp) | Diaria | 1996-01 |
| `bcra_mensual` | Las variables de `bcra` por mes (fin de mes, promedio o suma según la variable), con var. interanual; solo meses completos | [BCRA, API](https://www.bcra.gob.ar/PublicacionesEstadisticas/Principales_variables.asp) | Mensual | 1996-01 |
| `bcra_real` | Saldos en pesos de `bcra_mensual` (base monetaria, M2, depósitos, préstamos por línea y préstamos comerciales) deflactados por el IPC nacional, a precios de dic-2016, con var. interanual | [BCRA, API](https://www.bcra.gob.ar/PublicacionesEstadisticas/Principales_variables.asp) | Mensual | 2016-12 |
| `comercio_exterior` | **INDEC** (API): exportaciones por rubro e importaciones por uso económico, total y con Brasil, China, Estados Unidos y la Unión Europea, millones de USD | [INDEC, ICA](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-2-40) | Mensual | 1986-01 |
| `comex_indices` | **INDEC**: índices de valor, precio y cantidad de exportaciones e importaciones (2004=100) y términos del intercambio | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-2-41) | Mensual | 2004-01 |
| `balanza_pagos` | **INDEC**: balanza de pagos (cuenta corriente, bienes, servicios, rentas, cuenta financiera, inversión directa, reservas), millones de USD | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-35-45) | Trimestral | 2006-T1 |
| `cuentas_nacionales` | **INDEC**: PIB, consumo privado y público, inversión, exportaciones e importaciones a precios de 2004 y corrientes, deflactor del PIB y valor agregado por sector (letras A a P), con var. interanual | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-47) | Trimestral | 2004-T1 |
| `capacidad_instalada` | **INDEC**: utilización de la capacidad instalada en la industria, nivel general y 12 bloques (incluida la refinación del petróleo), % | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-6-15) | Mensual | 2016-01 |
| `mayoristas` | **INDEC**: autoservicios mayoristas, índice de ventas a precios constantes (original y desestacionalizado) y ventas en pesos | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-1-168) | Mensual | 2017-01 |
| `shoppings` | **INDEC**: centros de compras, índice de ventas a precios constantes y ventas por rubro en pesos | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-1-36) | Mensual | 2017-01 |
| `electrodomesticos` | **INDEC**: comercios de electrodomésticos, ventas totales y por rubro en pesos | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-1-37) | Mensual | 2020-01 |
| `issp` | **INDEC**: indicador sintético de servicios públicos (2004=100), nivel general y 7 componentes | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-11-53) | Mensual | 2012-01 |
| `turismo` | **INDEC**: turistas residentes que viajaron al exterior y no residentes que llegaron, total y por vía, miles | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-13-55) | Mensual | 2022-01 |
| `icc` | **INDEC** (API): índice del costo de la construcción en el GBA, nivel general, materiales, mano de obra y gastos generales, con variaciones | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-33) | Mensual | 2015-11 |
| `canasta_crianza` | **INDEC** (API): canasta de crianza por edad (bienes y servicios, cuidado y total), pesos por mes | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-43-149) | Mensual | 2020-01 |
| `pobreza` | **INDEC** (API, EPH): pobreza e indigencia en personas y hogares, 31 aglomerados | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-46-152) | Semestral | 2016-S2 |
| `mercado_trabajo` | **INDEC** (API, EPH): tasas de actividad, empleo, desocupación, subocupación y empleo informal, 31 aglomerados | [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-31-58) | Trimestral | 2016-T2 |
| `adefa` | **ADEFA** (vía Ministerio de Economía): producción, exportaciones y ventas a concesionarios de automóviles y utilitarios, unidades | [ADEFA](https://www.adefa.org.ar/es/estadisticas-mensuales) | Mensual | 1993-01 |
| `adimra` | **ADIMRA**: índice de producción industrial metalúrgica (2015=100), original y desestacionalizado | [ADIMRA](https://www.adimra.org.ar/datos) | Mensual | 2016-01 |
| `acero` | **Cámara Argentina del Acero**: producción de acero crudo, hierro primario y laminados, miles de toneladas (del PDF que publica la Cámara) | [CAA](https://www.acero.org.ar/estadisticas-locales/) | Mensual | 2016-01 |
| `cemento` | **AFCP** (vía Ministerio de Economía): despacho de cemento al mercado interno, miles de toneladas | [AFCP](https://www.afcp.org.ar/despacho-mensual) | Mensual | 1994-01 |
| `construya` | **Grupo Construya**: Índice Construya de despachos de insumos para la construcción, original y desestacionalizado | [Construya](https://www.grupoconstruya.com.ar/servicios/indice_construya) | Mensual | 2017-01 |
| `patentamientos` | **DNRPA** (datos abiertos del Ministerio de Justicia): inscripciones iniciales de automotores y motos, total y por provincia | [DNRPA](https://datos.jus.gob.ar/dataset/estadistica-de-tramites-de-automotores) | Mensual | 2000-01 |
| `patentamientos_desest` | `patentamientos` (total de autos y de motos) desestacionalizado con X-13 | [DNRPA](https://datos.jus.gob.ar/dataset/estadistica-de-tramites-de-automotores) | Mensual | 2000-01 |
| `empleo_sipa` | **Secretaría de Trabajo** (SIPA): trabajo registrado total y por modalidad, y asalariados privados, original y desestacionalizado | [Trabajo](https://www.argentina.gob.ar/trabajo/estadisticas/situacion-y-evolucion-del-trabajo-registrado) | Mensual | 2009-01 |
| `utdt` | **Universidad Torcuato Di Tella**: Índice Líder, Índice de Confianza del Consumidor (nacional, regiones y subíndices) e Índice de Confianza en el Gobierno | [UTDT](https://www.utdt.edu/ver_contenido.php?id_contenido=27166&id_item_menu=44662) | Mensual | 1993-01 |
| `leche` | **Secretaría de Agricultura** (Dirección Nacional de Lechería): producción primaria de leche, millones de litros | [Lechería](https://www.magyp.gob.ar/sitio/areas/ss_lecheria/estadisticas/_01_primaria/index.php) | Mensual | 2015-01 |
| `faena` | **Secretaría de Agricultura** (vía Ministerio de Economía): faena de vacunos, porcinos y ovinos, cabezas | [Agricultura](https://www.magyp.gob.ar/sitio/areas/bovinos/informacion_sectorial/) | Mensual | 1990-01 |
| `clima_amba` | **Open-Meteo** (reanálisis ERA5 de Copernicus/ECMWF, CC BY 4.0): temperatura máxima, mínima y media y lluvia diarias de CABA, del AMBA (promedio de un punto por partido) y de sus zonas norte, oeste y sur. Son celdas de modelo, no estaciones | [Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) | Diaria | 2024-11-01 |
| `clima_amba_mensual` | `clima_amba` por mes: temperatura media, máximas y mínimas promedio, lluvia acumulada y días con lluvia | [Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) | Mensual | 2024-11 |
| `clima_amba_pronostico` | **Open-Meteo**: pronóstico diario de temperatura, lluvia y probabilidad de lluvia para CABA y el AMBA, próximos 16 días (se reemplaza cada día) | [Open-Meteo](https://open-meteo.com/en/docs) | Diaria | hoy + 16 días |
| `imig` | **Secretaría de Hacienda**: resultado fiscal del Sector Público Nacional base caja (ingresos, gasto primario por tipo, resultado primario, intereses y resultado financiero), millones de $ | [Hacienda](https://www.argentina.gob.ar/economia/sechacienda/infoestadistica) | Mensual | 2016-01 |
| `recaudacion` | **ARCA**: recaudación total, DGI, DGA y seguridad social (desde 1997) y por impuesto: IVA (DGI y aduana), ganancias, débitos y créditos, combustibles, internos, bienes personales, derechos de exportación e importación (desde 2017), millones de $ | [ARCA](https://www.arca.gob.ar/institucional/estudios/recaudacion/series.asp) | Mensual | 1997-01 |
| `recaudacion_real` | `recaudacion` deflactada por el IPC nacional, a precios de diciembre de 2016, con var. interanual | [ARCA](https://www.arca.gob.ar/institucional/estudios/recaudacion/series.asp) | Mensual | 2016-12 |
| `provincias` | **Ministerio de Economía (DNAP)**: ejecución presupuestaria de las provincias, consolidado (ingresos, tributarios propios y nacionales, regalías, personal, inversión, resultado primario y financiero) y por provincia (ingresos, regalías y resultados), millones de $ por año | [DNAP](https://www.argentina.gob.ar/economia/sechacienda/coordinacion-fiscal-provincial/ejecucion-presupuestaria-provincial/ejecuciones) | Anual | 2005 |
| `deuda` | **Secretaría de Finanzas**: deuda bruta de la Administración Central por instrumento (títulos en pesos, CER y moneda extranjera, organismos internacionales, letras), millones de USD a fin de mes | [Finanzas](https://www.argentina.gob.ar/economia/finanzas/datos-mensuales) | Mensual | 2019-01 |

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
| `data/series/<id_serie>.csv` | Una serie sola (`fecha`, `valor`), para traer solo las que se necesitan. |
| `data/monitorargy/catalogo.json` | Catálogo de series de Monitor Argy (se actualiza cada noche), para el selector. |
| `data/monitorargy/series/<id>.csv` | Copia sin cambios de una selección de series de Monitor Argy (lista en `pipeline/monitorargy.py`), actualizada cada noche. |
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

### Explorar y graficar en la web

La página **[Explorar](https://rodrigotperelsztein-source.github.io/monitor-series/explorar.html)** grafica hasta 8
series del repositorio: líneas, áreas, barras, barras apiladas o torta; valores originales, índice base 100,
variación interanual o contra el período anterior; agrupación mensual, trimestral o anual; selector de período;
tarjetas con el último dato y su variación; lectura automática del gráfico; descarga en CSV o PNG y link para
compartir la vista. Usa Apache ECharts 5.5.1, alojado en el propio repositorio (`docs/vendor/`).

### Power BI: elegir solo algunas series (recomendado)

`data/todas/series.csv` clasifica cada serie para buscarla y filtrarla: `categoria` (Actividad económica, Precios,
Salarios, Transporte, Agro y puertos, Electricidad, Combustibles, Petróleo y precios internacionales),
`organismo_corto` (la fuente), `dato` (Nivel, Variación mensual, interanual o acumulada) y `ajuste` (Original,
Desestacionalizada, Tendencia-ciclo o Real). Las dos páginas usan esos campos en sus filtros.

La página **[Selector de series](https://rodrigotperelsztein-source.github.io/monitor-series/)** muestra el catálogo
completo (las series de este repositorio y las de Monitor Argy), con buscador y filtros. Se tildan las series y la
página arma la lista para pegar en el parámetro `SeriesElegidas` de Power BI; la consulta `Datos` baja solo esas
(cada serie del repositorio tiene su archivo en `data/series/<id_serie>.csv`; las de Monitor Argy, prefijo `ma:`,
salen de su API). La primera vez, la misma página da el código de las dos consultas.

Para cambiar de series: elegir en la página, copiar la lista, pegarla en *Transformar datos > Administrar
parámetros > SeriesElegidas* y actualizar.

### Power BI: todas las series

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

1. **Baja el archivo** de la URL oficial. El IPC, el EMAE total, el índice de salarios, las canastas básicas y los
   precios mayoristas salen del [Catálogo API-INDEC](https://api.indec.gob.ar) (ver abajo); si la API no responde,
   los tres primeros usan el archivo de siempre del sitio de INDEC.
2. **Compara su huella** (SHA-256) con la de la última versión. Si es igual, no hace nada.
3. **Lo lee buscando los encabezados por su texto**, no por posición fija, para tolerar cambios menores de formato.
4. **Valida** antes de guardar: columnas completas, meses consecutivos, sin vacíos, valores en rango,
   que no se pierda historia, que las revisiones no sean desproporcionadas y que los meses nuevos no tengan
   saltos absurdos contra el mismo mes del año anterior.
5. Si todo está bien, **guarda** el CSV, el Excel, el original y el registro de revisiones, y regenera
   los archivos de `data/todas/` con todas las series juntas.
   Si algo falla, **no toca nada de esa fuente** y la tarea termina en error.

### API del INDEC

La API pide un token personal que vence a los 12 meses. Está en el secreto `INDEC_API_TOKEN` del repositorio y solo
llega a un paso del workflow que baja las tablas necesarias (`python -m pipeline.indec_api bajar`) a una carpeta
local que no se guarda; el procesamiento corre después, sin token. Para renovarlo: en api.indec.gob.ar, perfil →
regenerar token; en GitHub, Settings → Secrets and variables → Actions → editar `INDEC_API_TOKEN`. Con el token
vencido, la corrida avisa en el registro y las canastas y los precios mayoristas no se actualizan.

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

### SUBE desestacionalizada

`sube_desest` se recalcula cada vez que cambia `sube_mensual` (transacciones de los meses completos), con el
mismo programa y código. Especificaciones en `pipeline/fuentes/sube_desest.py`; diagnósticos en
[`data/meta/sube_desest.json`](data/meta/sube_desest.json). Diferencias con el EMAE:

- **feriados y días de la semana se quitan** de la serie (un feriado baja mucho los viajes del mes y no es un
  cambio de tendencia); Pascua no resultó significativa;
- empieza en 2020-01 e incluye la pandemia, separada con outliers; con pocos años de datos, los meses
  recientes se revisan más que en series largas;
- los paros quedan en la serie (outliers AO): una caída por huelga se ve como caída;
- total, AMBA e interior se ajustan por separado: AMBA + interior no suma exactamente el total.

| Serie | Modelo | Transf. | Outliers |
|---|---|---|---|
| total | (0 1 1)(0 1 1) | niveles | LS 2020-03; AO 2020-04; TC 2022-01 |
| AMBA | (0 1 1)(0 1 1) | niveles | AO 2020-03; LS 2020-04 |
| interior | (0 1 1)(0 1 1) | niveles | AO 2020-04 |
| colectivo | (1 1 0)(0 1 1) | niveles | LS 2020-03; AO 2020-04 |
| tren | (0 1 1)(0 1 1) | niveles | LS 2020-03, 2020-04, 2021-03; TC 2021-04; AO 2021-05, 2021-10, 2022-01, 2025-02, 2025-10, 2026-07 |
| subte | (0 1 1)(0 1 1) | log | TC 2020-03, 2020-05, 2022-01; LS 2020-04 |

## Cuándo corre

La programación sigue el calendario de difusión de INDEC, que publica a las 16:00:

| Horario (Buenos Aires) | Qué hace |
|---|---|
| Días hábiles, 13 veces entre 16:23 y 20:37 | **Modo calendario.** Si INDEC prevé publicar ese día alguna de las series, baja solo esas, hasta que entre el dato nuevo. Si no hay nada previsto o ya entró, termina en segundos y no guarda nada. Si falla la descarga (la página de INDEC suele saturarse a las 16), no cuenta como error y se reintenta en la siguiente. |
| Todas las noches 21:47 y 01:17 | **Control completo.** Actualiza el calendario (semestre actual y siguiente, cuando INDEC lo publica), revisa todas las fuentes para atrapar revisiones o publicaciones fuera de calendario, y **termina en error** si una publicación prevista no entró. El segundo horario es de respaldo. |
| Días hábiles 10:12, 11:38 y 13:19 | **Petróleo y combustibles internacionales** (`petroleo`, `refinados`): cierre del día anterior de la EIA. |

La SUBE se actualiza casi todos los días y entra en el control de cada noche; solo se baja el archivo del
año en curso (unos 50 MB), y la historia de años anteriores queda en `data/sube.csv`.

El RIPTE no está en el calendario de INDEC: se publica sin fecha fija (en general, unos dos meses después
del mes de referencia) y entra en el control de cada noche.

GitHub no garantiza el horario de las tareas programadas: con carga alta las demora (se vieron atrasos de 3 a 4 horas)
o las saltea, sobre todo en horas redondas. Por eso hay varios horarios, en minutos poco usados.

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

## Seguridad

Datos públicos, solo lectura. La única credencial externa es el token de la API del INDEC, que solo ve el paso que
baja esas tablas. Las medidas (acciones fijadas por commit, dependencias verificadas
por huella, workflows sin permisos por defecto, binario de X-13 verificado, página sin terceros) y las
recomendaciones para usarlo dentro de una empresa están en [`SECURITY.md`](SECURITY.md).

## Licencia de los datos

Los datos pertenecen a los organismos que los publican. Citá la fuente original de cada serie.
