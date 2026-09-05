# Backend DSS Comparador de Precios

## Objetivo

Backend de un sistema de apoyo a decisiones (DSS) para comparar precios de
supermercados segun la ubicacion del usuario. El MVP permite buscar productos,
armar una canasta temporal, consultar precios por sucursal, calcular distancias y
generar un ranking multicriterio.

## Arquitectura

El proyecto usa un monolito modular con principios de Clean Architecture y
Arquitectura Hexagonal. Cada modulo mantiene separadas sus capas:

- `domain`: entidades, objetos de valor, puertos y servicios de dominio.
- `application`: casos de uso, comandos y DTOs.
- `infrastructure`: SQLite/PostgreSQL, SQLAlchemy, scrapers, ETL y scheduler.
- `interfaces`: entradas externas como HTTP y CLI.

El dominio no depende de FastAPI, SQLAlchemy, SQLite, PostgreSQL ni herramientas externas.
Las dependencias apuntan hacia el dominio.

## Modulos

| Modulo | Responsabilidad |
| --- | --- |
| `catalog` | Productos, categorias, marcas y productos por fuente. |
| `supermarkets` | Supermercados, sucursales, ciudades y provincias. |
| `prices` | Precios actuales, snapshots e historial. |
| `basket` | Canasta temporal de usuario anonimo. |
| `geo` | Coordenadas y calculo de distancia. |
| `decision` | Modelo multicriterio DSS. |
| `ingestion` | Fuentes, scraping, auditoria, ETL e identidad canonica. |

## Alcance del MVP

Incluido:

- Catalogo, supermercados, sucursales y precios.
- Canasta temporal no persistida.
- Ranking DSS en memoria.
- Seed inicial para datos de prueba.
- Auditoria minima de ingestion con `scraping_source` y `scraping_run`.
- Scrapers piloto para Carrefour, Chango Mas, Jumbo, La Coope, La Anonima y Maxiconsumo.
- ETL auditable con staging, deduplicacion, normalizacion e historial idempotente.
- Identidad canonica conservadora y revision asistida.
- Actualizacion concurrente bajo demanda y benchmark reproducible.
- Scheduler persistente con historial, leases y reintentos ante fallos.
- Calidad operativa de precios previa al ranking.
- Mapa y geolocalizacion opcional desde el navegador.

Excluido por ahora:

- Usuarios, autenticacion, roles y permisos.
- Canastas guardadas.
- Rankings persistidos.
- Despliegue y validacion integral sobre PostgreSQL.
- Cobertura nacional y confirmacion de ubicacion para todos los catalogos publicos.

## Estado de etapas

- Estructura base, modulos principales y arquitectura Clean/Hexagonal: completo.
- Entidades de dominio del core: completo.
- Entidades agregadas para cerrar huecos: `PriceSnapshot`, `ScrapingSource` y `ScrapingRun`.
- Modelos SQLAlchemy y migraciones del core: completo.
- Tablas de auditoria de ingestion: completo con `scraping_source` y `scraping_run`.
- Administracion de fuentes y corridas de ingestion: completo mediante API v1.
- Puertos, repositorios SQLAlchemy, Unit of Work, seed y ranking DSS: completo para el core.
- Endpoints minimos v1: completo.
- Scrapers reales limitados para Carrefour, Chango Mas, Jumbo, La Coope, La Anonima y
  Maxiconsumo, con
  auditoria automatica: completo como piloto.
- ETL de staging, calidad, deduplicacion, identidad canonica y carga idempotente de historial: completo.
- Validacion de ubicacion y sucursal: mecanismo de confirmacion implementado
  para Carrefour; parcial para los catalogos publicos y las coordenadas piloto
  restantes.

## Desarrollo local

Desde la carpeta `backend`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

La documentacion automatica de FastAPI queda en `http://127.0.0.1:8000/docs`.
El health check esta en `GET /health`:

```json
{
  "status": "ok",
  "service": "price-dss-backend"
}
```

## Base de datos para demo

Para la demo se usa SQLite por defecto. Desde `backend/`, la URL recomendada es:

```powershell
$env:DATABASE_URL = "sqlite+aiosqlite:///./price_dss_demo.db"
```

Si no configuras `DATABASE_URL`, el backend usa esa base SQLite local por default.
El archivo `price_dss_demo.db` se crea siempre en `backend/`, aunque ejecutes un
comando desde otra carpeta del repositorio. Las URLs SQLite relativas definidas
en `.env` tambien se resuelven contra `backend/` para que migraciones, seed y
scraper usen la misma base.

## Migraciones

Alembic recibe la misma `DATABASE_URL` async del backend y la adapta al driver
sincronico de migraciones. Para SQLite:

```powershell
$env:DATABASE_URL = "sqlite+aiosqlite:///./price_dss_demo.db"
```

```bash
uv run alembic upgrade head
uv run alembic downgrade -1
```

Migraciones actuales:

- `0001`: esquema inicial del DSS de precios.
- `0002`: tablas `scraping_source` y `scraping_run`.
- `0003`: staging `producto_extraido` para calidad, deduplicacion y trazabilidad ETL.
- `0004`: sucursal destino opcional para cada fuente de scraping.
- `0005`: clave de adaptador (`scraper_key`) administrable por fuente.
- `0006`: GTIN validado e indexado por publicacion para identidad multicadena.
- `0007`: cola auditable de revision asistida para conflictos de identidad.
- `0008`: verificacion auditable de coordenadas de sucursales.
- `0009`: planes del scheduler e historial de ejecuciones automaticas.

## Seed inicial

Aplica migraciones y carga datos de prueba:

```bash
uv run alembic upgrade head
uv run python scripts/seed_initial_data.py
```

El seed es idempotente y carga Chubut, Comodoro Rivadavia, Rada Tilly,
supermercados, sucursales, categorias, marcas, productos, productos fuente,
precios y la configuracion inicial de los pilotos de Jumbo y La Coope.

## Unit of Work

La unidad de trabajo agrupa repositorios que comparten una sesion y centraliza
`commit` y `rollback`. Los repositorios solo hacen `flush`.

```python
async with get_unit_of_work() as uow:
    products = await uow.products.search_by_name("coca")
    await uow.commit()
```

## Casos de uso de lectura y ranking

La capa `application` contiene casos de uso iniciales para buscar productos,
listar categorias, listar marcas, listar supermercados, listar sucursales,
consultar precios actuales, consultar historial y comparar precios por
producto. Estos casos de uso dependen de `UnitOfWorkPort`, devuelven DTOs y no
dependen de FastAPI, SQLAlchemy ni Pydantic.

El ranking DSS se calcula en memoria desde
`decision/application/use_cases/GenerateRankingUseCase`. Recibe un
`GenerateRankingCommand`, construye una canasta temporal, consulta datos por
puertos, calcula distancias con `geo` y ordena alternativas con el modelo de
suma ponderada del dominio `decision`.

No persiste rankings ni canastas. Las sucursales que no cubren todos los
productos se devuelven como incompletas y quedan fuera del ranking principal.

### Calidad operativa de precios

Antes de exponer precios actuales o calcular un ranking se aplica una politica
de calidad en memoria. El historial permanece sin cambios para conservar la
auditoria completa.

- Vigencia: por defecto se excluyen precios con mas de 14 dias.
- Anomalia: se requiere un minimo de dos observaciones anteriores y se compara
  el valor actual con su mediana historica.
- Umbral conservador: se excluyen valores menores a `0.4x` o mayores a `2.5x`
  de esa mediana.
- Promociones: un precio marcado explicitamente como promocional no se descarta
  por la regla de anomalia.
- Cobertura: cada producto faltante informa `missing`, `stale` o `suspect`.

`GET /api/v1/prices/current` acepta `max_age_days` (1 a 90) y `as_of`.
`POST /api/v1/decisions/ranking` acepta `max_price_age_days` (1 a 90) y
`as_of`. La fecha opcional permite reproducir experimentos; si se omite se usa
el momento actual. Ambas respuestas incluyen un bloque `quality` con precios
aptos y exclusiones por antiguedad o anomalia.

## Endpoints v1

- `GET /health`
- `GET /api/v1/catalog/products`
- `GET /api/v1/catalog/categories`
- `GET /api/v1/catalog/brands`
- `GET /api/v1/locations/cities`
- `GET /api/v1/supermarkets`
- `GET /api/v1/branches`
- `GET /api/v1/prices/current`
- `GET /api/v1/prices/history`
- `GET /api/v1/prices/compare`
- `POST /api/v1/basket/validate`
- `POST /api/v1/decisions/ranking`
- `GET|POST /api/v1/ingestion/sources`
- `PATCH /api/v1/ingestion/sources/{source_id}`
- `GET /api/v1/ingestion/runs`
- `POST /api/v1/ingestion/sources/{source_id}/runs`
- `POST /api/v1/ingestion/sources/{source_id}/refresh`
- `POST /api/v1/ingestion/sources/refresh-concurrently`
- `GET|POST /api/v1/ingestion/schedules`
- `PATCH /api/v1/ingestion/schedules/{schedule_id}`
- `POST /api/v1/ingestion/schedules/{schedule_id}/run-now`
- `GET /api/v1/ingestion/schedule-executions`
- `POST /api/v1/ingestion/runs/{run_id}/succeed`
- `POST /api/v1/ingestion/runs/{run_id}/fail`

Los routers HTTP viven en `interfaces/http` y no consultan SQLAlchemy
directamente.

## Contrato HTTP

Las colecciones no paginadas devuelven:

```json
{
  "items": [],
  "count": 0
}
```

Las colecciones paginadas devuelven:

```json
{
  "items": [],
  "count": 0,
  "pagination": {
    "page": 1,
    "page_size": 20,
    "count": 0,
    "total": 0
  }
}
```

Los errores mantienen `detail` por compatibilidad y agregan un contrato
estructurado:

```json
{
  "detail": "Mensaje de error",
  "error": {
    "code": "http_error",
    "message": "Mensaje de error",
    "details": "Mensaje de error"
  }
}
```

## Contrato con frontend

El backend publica campos tecnicos en ingles, por ejemplo `normalized_name`,
`amount`, `observed_at`, `branch` e `incomplete_branches`.

El frontend mantiene nombres orientados a la UI en castellano, como `nombre`,
`precio`, `fecha_relevamiento`, `sucursal` e `incomplete`. La traduccion entre
ambos contratos vive en `frontend/src/services/api.ts`. En modo
`VITE_API_MODE=live`, ese cliente adapta las respuestas de `/api/v1` al contrato
que usan las vistas Vue. En modo mock se mantienen los datos locales de
demostracion.

## Ingestion y scraping

La base ya incluye tablas de auditoria para ingestion:

- `scraping_source`: fuente externa asociada a un supermercado.
- `scraping_run`: ejecucion de scraping, estado, contadores y errores.

El piloto incluye adaptadores HTTP reales para los catalogos publicos de Carrefour,
Chango Mas, Jumbo, La Coope en Casa y Maxiconsumo, mas un adaptador Playwright para
La Anonima. La clave
`scraper_key` queda asociada a la fuente configurada,
por lo que el flujo no acepta un selector manual que pueda contradecirla. Cada
adaptador resuelve consultas en paralelo, con un maximo de tres solicitudes HTTP
simultaneas y reintentos acotados.

La operacion de actualizacion guarda primero los datos extraidos en staging y luego
ejecuta la validacion, normalizacion, deduplicacion y carga del historial de precios.
Al refrescar varias fuentes, la extraccion de red se ejecuta concurrentemente con
`asyncio.TaskGroup`, `Semaphore`, timeout por fuente y una `asyncio.Queue`; el
consumidor procesa la persistencia ETL de a una fuente para conservar transacciones
y auditoria consistentes. Una falla de fuente queda auditada y no cancela las demas.

Para supermercados que dependan de JavaScript, la infraestructura incluye un pool
acotado y reutilizable de paginas Playwright. La Anonima es la primera cadena real
que utiliza esa infraestructura. El navegador se instala solo para esas fuentes:

```bash
uv sync --extra browser
uv run playwright install chromium
```

La Anonima utiliza concretamente ese pool con `scraper_key=la_anonima`: abre hasta
dos paginas reutilizables, ejecuta consultas en paralelo y extrae los atributos
estructurados de cada tarjeta. Las cookies del piloto usan el identificador tecnico
`47` del sitio y el codigo postal `9000`; ese valor no se presenta como numero
publico de la sucursal. El adaptador rechaza otras ciudades hasta que tengan una
configuracion de ubicacion verificada.

En Windows, si el servidor ASGI fue iniciado con un event loop Selector (por
ejemplo, bajo ciertos modos de recarga), el adaptador ejecuta Playwright en un
hilo dedicado con loop Proactor. De esta forma el driver puede crear sus
subprocesos sin cambiar el modelo concurrente del resto del backend.

Antes de pasar a staging, el piloto de La Coope exige que todos los terminos
significativos de la consulta aparezcan en el nombre o la marca. Esto evita que
la busqueda amplia del proveedor cargue articulos ajenos a la frase solicitada.

Chango Mas usa la API publica VTEX de Mas Online. El adaptador crea una sesion
de checkout, confirma el codigo postal `9000`, reutiliza el canal de venta resuelto
y conserva solo ofertas con precio y stock positivos. La auditoria marca estos
resultados con `price_basis=online_delivery_postal_code_9000`. Esa confirmacion
demuestra cobertura de entrega en Comodoro, no inventario de una tienda fisica;
la asociacion con `Hiper - Enrique Girolamo` es el destino configurado del piloto.

Maxiconsumo se extrae como HTML estatico porque su pagina Magento entrega las
tarjetas completas sin ejecutar JavaScript. La URL base identifica la sucursal de
Comodoro Rivadavia y el adaptador rechaza otras ciudades. El importe auditado es
el `Precio unitario por bulto cerrado` publicado por el sitio; el payload conserva
`price_basis=unit_price_closed_case` para no confundirlo con el precio minorista.

## Geografia y mapa

La migracion `0008` agrega a `sucursal` la marca
`coordenadas_verificadas`, la fuente consultada y la fecha de verificacion. El
seed actualiza de forma idempotente las direcciones y puntos del piloto para
21 sucursales de Carrefour, Jumbo, La Anonima, La Coope, Chango Mas,
Maxiconsumo y Diarco en Comodoro Rivadavia y Rada Tilly. Diarco solo tiene
catalogo geografico por el momento; Maxiconsumo ya posee una fuente estatica
asociada a su sucursal de Comodoro. Una sucursal sin la marca de
verificacion puede seguir existiendo para administracion, pero el caso de uso
de ranking no calcula distancias ni la recomienda.

El frontend consulta `/api/v1/branches?city_id=...` antes de calcular y envia
solo los `branch_ids` verificados de la ciudad elegida. Como origen utiliza el
centro de la ciudad o, si el usuario concede permiso al navegador, las
coordenadas de `navigator.geolocation`. El componente
`frontend/src/components/RankingMap.vue` representa el origen, la alternativa
recomendada, las alternativas completas y las sucursales sin cobertura sobre
OpenStreetMap mediante Leaflet.

El adaptador de Carrefour crea una sesion VTEX, adjunta el codigo postal de
Comodoro Rivadavia al `orderForm` y reutiliza esa sesion para consultar el catalogo.
Solo conserva ofertas con precio positivo y stock disponible. Cuando Carrefour
confirma el codigo postal, el payload queda marcado con `location_verified=true`.
Si la confirmacion falla o se solicita una ciudad sin configuracion regional, el
fallback queda marcado con `location_verified=false` y no debe presentarse como un
precio confirmado para una sucursal determinada.

Tras aplicar la migracion y el seed, obtene el identificador de la fuente:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ingestion/sources
```

Luego, desde `backend/`, ejecuta el piloto con pocas consultas:

```powershell
uv run python -m app.modules.ingestion.interfaces.cli.run_scraping `
  --source-id <UUID_DE_LA_FUENTE_JUMBO> `
  --city "Comodoro Rivadavia" `
  --query "coca cola" `
  --query "leche" `
  --limit 5
```

Para La Coope, usa el identificador de `La Coope public catalog pilot`:

```powershell
uv run python -m app.modules.ingestion.interfaces.cli.run_scraping `
  --source-id <UUID_DE_LA_FUENTE_LA_COOPE> `
  --city "Comodoro Rivadavia" `
  --query "fernet" `
  --query "gancia" `
  --limit 5
```

Tambien puede ejecutarse desde la raiz del repositorio sin cambiar de carpeta:

```powershell
uv run --directory backend python -m app.modules.ingestion.interfaces.cli.run_scraping `
  --source-id <UUID_DE_LA_FUENTE_JUMBO> `
  --city "Comodoro Rivadavia" `
  --query "coca cola" `
  --limit 5
```

Los endpoints publicos usados no reciben una sucursal ni una localidad. El campo
`city` delimita el alcance declarado del piloto, pero los precios extraidos no deben
presentarse como precios confirmados de Comodoro Rivadavia hasta validar la seleccion
de ubicacion del sitio y asociarlos a una sucursal durante el ETL.

Si se configura una `DATABASE_URL` diferente, aplica `alembic upgrade head` y el
seed sobre esa misma base antes de ejecutar el scraper.

## ETL y calidad

Cada corrida exitosa conserva sus items en `producto_extraido`. El proceso ETL:

- valida codigo externo, nombre y precio positivo dentro de un limite razonable;
- marca duplicados dentro de la misma corrida sin descartarlos de la auditoria;
- reutiliza una publicacion existente por supermercado y codigo externo;
- resuelve identidad por publicacion conocida, GTIN valido o equivalencia estructural
  no ambigua de marca, variante y presentacion;
- crea un producto nuevo solo cuando no existe una coincidencia canonica confiable;
- inserta una observacion de precio por producto fuente, sucursal y fecha sin
  duplicar el historial al reejecutarse.

Las unidades comparables se llevan a una base comun (`2,25 L = 2250 ml =
2250 cm3`, `1 kg = 1000 g`). Los codigos internos de una cadena no se aceptan
como GTIN: solo se usan GTIN-8/12/13/14 con digito verificador valido. Si dos
productos canonicos son compatibles con la misma publicacion, el item queda sin
fusionar para evitar falsos positivos.

Ademas del checksum, el ETL exige que el scraper declare
`identifier_type=gtin`; los identificadores declarados como `internal` nunca se
promueven a GTIN. La evidencia historica de staging permite completar marcas y
GTIN faltantes mediante una operacion auditable:

```powershell
uv run python scripts/enrich_product_catalog.py
uv run python scripts/enrich_product_catalog.py --apply
```

La primera ejecucion genera el CSV de simulacion. Solo se aplican marcas con una
unica clave normalizada por producto y GTIN que apuntan a un solo producto activo.
Los codigos asociados a productos distintos quedan reportados como conflictos y
requieren revision manual.

La revision asistida persiste esos casos y agrega candidatos semanticos solamente
cuando coinciden marca y cantidad bajo alias controlados (`sin azucar=zero` y
`liviano=light`). El escaneo nunca fusiona productos:

```powershell
uv run python scripts/review_product_identity.py scan
uv run python scripts/review_product_identity.py list --status pending
```

Cada decision exige una nota de auditoria. Aprobar reasigna las publicaciones,
conserva sus precios y desactiva el producto origen; rechazar conserva el catalogo
sin cambios y evita que la misma propuesta vuelva a generarse:

```powershell
uv run python scripts/review_product_identity.py approve `
  --review-id <UUID> --note "Evidencia verificada"

uv run python scripts/review_product_identity.py reject `
  --review-id <UUID> --note "Empaque incompatible"
```

Para auditar y corregir productos historicos creados antes de estas reglas, el
comando se ejecuta primero sin modificar datos y genera un CSV:

```powershell
uv run python scripts/reconcile_product_identity.py
```

Luego de revisar las sugerencias se pueden aplicar. La operacion reasigna
`producto_fuente`, conserva todo el historial de `precio` y desactiva solamente
productos debiles que quedan sin publicaciones:

```powershell
uv run python scripts/reconcile_product_identity.py --apply
```

Cuando dos o mas supermercados ya cargaron productos separados con exactamente
la misma identidad estructural, se puede consolidar el catalogo. El comando exige
la misma marca/variante y cantidad normalizada, ademas de publicaciones en al
menos dos cadenas. Tambien se ejecuta primero como simulacion:

```powershell
uv run python scripts/consolidate_product_catalog.py
```

Despues de revisar el CSV, `--apply` conserva cada `producto_fuente` y su historial,
los reasigna al producto superviviente, completa unidad/contenido y desactiva los
productos duplicados que quedaron sin publicaciones:

```powershell
uv run python scripts/consolidate_product_catalog.py --apply
```

La fuente puede tener una sucursal destino configurada; en ese caso el ETL la usa
por defecto. Tambien se puede indicar una sucursal activa de la misma cadena como
override puntual:

La sucursal piloto de La Coope tiene una direccion oficial validada, pero conserva
temporalmente las coordenadas de referencia de Comodoro Rivadavia hasta geocodificar
el local. Su distancia en el ranking no debe tomarse como una medicion real.

```powershell
uv run python -m app.modules.ingestion.interfaces.cli.run_etl `
  --run-id <UUID_DE_LA_CORRIDA>
```

```powershell
uv run python -m app.modules.ingestion.interfaces.cli.run_etl `
  --run-id <UUID_DE_LA_CORRIDA> `
  --branch-id <UUID_DE_SUCURSAL_DE_LA_MISMA_CADENA>
```

Usa `--no-create-products` para dejar productos sin coincidencia exacta en estado
`unmatched` en vez de crear un producto normalizado. La fuente debe tener una
sucursal real validada antes de que sus precios se utilicen en la UI o el ranking.

## Actualizacion administrativa

El backend tambien ofrece una operacion unica para extraer y cargar una fuente
configurada, pensada para una futura vista administrativa y no para el flujo de
compras publico. Recibe hasta cinco consultas y un limite maximo de veinte
resultados por consulta:

```powershell
$body = @{
  queries = @("gancia")
  city = "Comodoro Rivadavia"
  limit = 5
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -Body $body `
  http://127.0.0.1:8000/api/v1/ingestion/sources/<UUID_DE_FUENTE>/refresh
```

La respuesta incluye la corrida auditada y el resumen de calidad/carga del ETL.

Para actualizar varias fuentes en paralelo, enviá sus identificadores. El limite
de concurrencia se aplica a las fuentes y cada una conserva su resultado, aun si
otra falla:

```powershell
$body = @{
  source_ids = @("<UUID_JUMBO>", "<UUID_LA_COOPE>")
  queries = @("gancia", "leche")
  city = "Comodoro Rivadavia"
  limit = 5
  max_concurrency = 2
  timeout_seconds = 20
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -Body $body `
  http://127.0.0.1:8000/api/v1/ingestion/sources/refresh-concurrently
```

La API de administracion permite crear, listar y activar/desactivar fuentes,
iniciar una corrida por fuente y finalizarla como exitosa o fallida. Solo se
permite una corrida abierta por fuente; estas operaciones no ejecutan scraping.

## Actualizacion automatica

La migracion `0009` agrega un plan persistente por fuente y un historial de
ejecuciones programadas. FastAPI inicia un worker asincrono que consulta planes
vencidos, los reclama mediante un lease en base de datos y ejecuta el mismo flujo
auditado de scraping y ETL usado por la API manual. No se crean planes activos en
el seed: su frecuencia y consultas deben definirse de forma explicita.

Variables operativas disponibles en `.env`:

- `INGESTION_SCHEDULER_ENABLED`: inicia o no el worker con FastAPI.
- `INGESTION_SCHEDULER_POLL_SECONDS`: frecuencia de consulta de planes vencidos.
- `INGESTION_SCHEDULER_BATCH_SIZE`: maximo de planes reclamados por ciclo.
- `INGESTION_SCHEDULER_MAX_CONCURRENCY`: trabajos externos simultaneos.
- `INGESTION_SCHEDULER_LEASE_SECONDS`: vencimiento del reclamo ante una caida.

Para crear un plan diario, usa el identificador de una fuente activa:

```powershell
$body = @{
  source_id = "<UUID_DE_FUENTE>"
  name = "Actualizacion diaria"
  queries = @("leche", "coca cola", "arroz")
  city = "Comodoro Rivadavia"
  interval_minutes = 1440
  retry_delay_minutes = 5
  result_limit = 10
  timeout_seconds = 60
  enabled = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -Body $body `
  http://127.0.0.1:8000/api/v1/ingestion/schedules
```

El primer disparo queda previsto para un intervalo despues del alta. Puede
ejecutarse inmediatamente y consultar ambos niveles de auditoria:

```powershell
Invoke-RestMethod -Method Post `
  http://127.0.0.1:8000/api/v1/ingestion/schedules/<UUID_PLAN>/run-now

Invoke-RestMethod `
  "http://127.0.0.1:8000/api/v1/ingestion/schedule-executions?schedule_id=<UUID_PLAN>"

Invoke-RestMethod `
  "http://127.0.0.1:8000/api/v1/ingestion/runs?source_id=<UUID_FUENTE>"
```

Una falla queda registrada y no cancela otros planes del lote. El siguiente
intento aplica backoff exponencial acotado (`1x`, `2x`, `4x`, `8x`) sobre
`retry_delay_minutes`, sin superar el intervalo regular. Una ejecucion exitosa
restablece el contador y agenda el intervalo normal.

## Benchmark de concurrencia

El comando experimental compara el refresco completo secuencial contra el
concurrente, alterna el orden de cada repeticion y genera un CSV con tiempos,
resultados ETL, fallos parciales y referencias a las corridas auditadas. Requiere
al menos dos fuentes activas que tengan una sucursal destino configurada:

```powershell
uv run python scripts/benchmark_scraping_concurrency.py `
  --source-id <UUID_FUENTE_1> `
  --source-id <UUID_FUENTE_2> `
  --source-id <UUID_FUENTE_3> `
  --source-id <UUID_FUENTE_4> `
  --query "coca cola" `
  --query "leche" `
  --repetitions 5 `
  --warmups 1 `
  --max-concurrency 4
```

El protocolo, las variables registradas y la interpretacion de resultados estan
en [docs/experimento-concurrencia.md](../docs/experimento-concurrencia.md).

## Validacion experimental

El paquete integral analiza el benchmark, calcula cobertura por cadena desde la
base, evalua el matcher contra un ground truth versionado y recorre el simplex de
pesos del DSS:

```powershell
uv run python scripts/run_experimental_validation.py `
  --benchmark-csv reports/tesis_benchmark_4_cadenas_20260826.csv `
  --output-dir reports/experimental_validation_20260826
```

Genera CSV detallados, resumen JSON e informe Markdown. La metodologia,
resultados y amenazas de validez estan en
[docs/validacion-experimental.md](../docs/validacion-experimental.md).

## Pruebas

La suite incluye pruebas unitarias de dominio/modelo DSS y pruebas de integracion
HTTP livianas con un Unit of Work falso en memoria.

```bash
uv run --extra dev pytest -q
uv run python -m compileall -q app scripts
```

## Validacion local con SQLite

Desde `backend/`:

```bash
copy .env.example .env
uv run alembic upgrade head
uv run python scripts/seed_initial_data.py
uv run python scripts/smoke_api_v1.py
```

El smoke test valida health check, catalogo, ubicaciones, supermercados,
sucursales, precios vigentes, canasta temporal y ranking DSS contra datos reales.

## PostgreSQL opcional

El proyecto conserva compatibilidad con PostgreSQL para etapas posteriores. Desde
la raiz del repositorio se puede levantar el servicio:

```bash
docker compose up -d postgres
```

Y usar:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://dss_user:dss_password@localhost:5432/price_dss"
```
