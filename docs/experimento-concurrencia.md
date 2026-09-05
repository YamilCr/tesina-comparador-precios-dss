# Experimento de concurrencia

Este protocolo compara el flujo real de ingestion en dos modalidades:

- `sequential`: refresca cada fuente, incluyendo staging y ETL, una despues de otra.
- `concurrent`: extrae las fuentes en paralelo con limite de concurrencia y persiste
  cada resultado mediante la cola ETL controlada.

Ambos modos usan los mismos adaptadores, consultas, limite de resultados, base de
datos y validaciones de calidad. El benchmark no modifica la configuracion de las
fuentes; cada ejecucion queda auditada en `scraping_run` y `producto_extraido`.

## Preparacion

1. Aplicar la base y el seed: `uv run alembic upgrade head` y
   `uv run python scripts/seed_initial_data.py`.
2. Configurar al menos dos fuentes activas, de cadenas diferentes cuando sea
   posible, con una sucursal destino valida para su propio supermercado.
3. Elegir entre una y cinco consultas estables, con una ciudad y limite fijo.
4. No ejecutar otras actualizaciones de esas mismas fuentes durante el experimento.

Se puede verificar la configuracion con:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ingestion/sources |
  Select-Object -ExpandProperty items |
  Format-Table id, name, scraper_key, branch_id, active
```

Una fuente sin `branch_id` no es apta para este experimento, porque el ETL no puede
cargar su historial de precios. El comando falla antes de iniciar corridas en ese
caso.

Las fuentes cuyo payload indique `location_verified=false` pueden participar en la
medicion tecnica de concurrencia y ETL, pero no deben utilizarse para afirmar que el
precio corresponde a una sucursal determinada. Carrefour valida Comodoro Rivadavia
mediante una sesion VTEX y su codigo postal `9000`; el fallback solo se conserva para
ciudades que todavia no tienen un objetivo regional configurado.

La Anonima permite medir tambien paralelismo de navegador: su adaptador usa un pool
Playwright de hasta dos paginas para las consultas de una misma fuente. Para incluirla
en el experimento se debe instalar Chromium y mantener fija la sucursal 47 de
Comodoro Rivadavia durante todas las repeticiones.

## Ejecucion

Desde `backend/`, repetir cinco veces cada modo y descartar una vuelta de calentamiento:

```powershell
uv run python scripts/benchmark_scraping_concurrency.py `
  --source-id <UUID_FUENTE_1> `
  --source-id <UUID_FUENTE_2> `
  --source-id <UUID_FUENTE_3> `
  --source-id <UUID_FUENTE_4> `
  --query "coca cola" `
  --query "leche" `
  --city "Comodoro Rivadavia" `
  --limit 5 `
  --repetitions 5 `
  --warmups 1 `
  --max-concurrency 4
```

El comando alterna el orden de los modos y genera tres CSV: resultados agregados,
detalle por fuente y resumen estadistico. Los artefactos finales usados por la
tesis se versionan en `backend/reports/`.

## Variables registradas

Cada fila del CSV conserva:

- `duration_ms`: tiempo total de la iteracion, desde el inicio de la actualizacion
  hasta completar la carga o registrar los fallos de todas las fuentes.
- `successful_sources` y `failed_sources`: fuentes que terminaron correctamente y
  fallos parciales sin cancelar otras fuentes.
- `items_scraped`, `items_loaded`, `items_rejected`, `items_duplicates` e
  `items_unmatched`: calidad y efecto ETL del mismo conjunto de consultas.
- `execution_order`: posicion del modo en la repeticion, para controlar el posible
  efecto del orden.
- `run_ids` y `errors`: trazabilidad hacia la auditoria de ingestion.

El resumen agrega media, mediana, desvio estandar, p95, minimos, maximos,
throughput, tasa de exito, speedup y reduccion por fuente.

La mejora porcentual se calcula como:

```text
((promedio_secuencial - promedio_concurrente) / promedio_secuencial) * 100
```

## Interpretacion

El resultado debe compararse para ejecuciones con igual cantidad de fuentes,
consultas, limite, ciudad y nivel de concurrencia. Los catalogos externos cambian
y la red no es determinista: el experimento demuestra el comportamiento del sistema
en ese contexto, no un tiempo universal de cada supermercado. Reportar tambien las
fuentes fallidas y los indicadores ETL evita atribuir a la concurrencia una mejora
que en realidad provenga de menor volumen de datos o de respuestas incompletas.

## Resultado del 26 de agosto de 2026

El experimento de cuatro cadenas completo cinco repeticiones por modo sin fallos.
La media secuencial fue `6427,6 ms` y la concurrente `3855,6 ms`: speedup `1,67x`
y reduccion del `40,0%`. Cada ejecucion proceso 39 items. La Anonima fue el camino
critico por el costo de Playwright, por lo que incorporar mas fuentes HTTP puede
aumentar el beneficio agregado mientras no superen su duracion.
