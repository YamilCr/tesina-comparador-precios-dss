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
| `ingestion` | Fuentes, auditoria de scraping y futuro ETL. |

## Alcance del MVP

Incluido:

- Catalogo, supermercados, sucursales y precios.
- Canasta temporal no persistida.
- Ranking DSS en memoria.
- Seed inicial para datos de prueba.
- Auditoria minima de ingestion con `scraping_source` y `scraping_run`.

Excluido por ahora:

- Usuarios, autenticacion, roles y permisos.
- Canastas guardadas.
- Rankings persistidos.
- Scraping y ETL real.

## Estado de etapas

- Estructura base, modulos principales y arquitectura Clean/Hexagonal: completo.
- Entidades de dominio del core: completo.
- Entidades agregadas para cerrar huecos: `PriceSnapshot`, `ScrapingSource` y `ScrapingRun`.
- Modelos SQLAlchemy y migraciones del core: completo.
- Tablas de auditoria de ingestion: completo con `scraping_source` y `scraping_run`.
- Administracion de fuentes y corridas de ingestion: completo mediante API v1.
- Puertos, repositorios SQLAlchemy, Unit of Work, seed y ranking DSS: completo para el core.
- Endpoints minimos v1: completo.
- Scrapers reales limitados para Jumbo y La Coope, con auditoria automatica: completo como piloto.
- ETL de staging, calidad, deduplicacion, matching exacto y carga idempotente de historial: completo.
- Validacion de ubicacion y sucursal por cada cadena: pendiente antes de publicar precios reales por ciudad.

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

El piloto incluye adaptadores HTTP reales para los catalogos publicos de Jumbo y
La Coope en Casa. Se ejecutan manualmente, extraen pocas consultas y registran una
corrida como exitosa o fallida. Sus resultados se imprimen como JSON y `items_loaded` queda en cero:
el catalogo, matching y carga de precios siguen siendo responsabilidad de la
siguiente etapa ETL.

Antes de pasar a staging, el piloto de La Coope exige que todos los terminos
significativos de la consulta aparezcan en el nombre o la marca. Esto evita que
la busqueda amplia del proveedor cargue articulos ajenos a la frase solicitada.

Tras aplicar la migracion y el seed, obtene el identificador de la fuente:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ingestion/sources
```

Luego, desde `backend/`, ejecuta el piloto con pocas consultas:

```powershell
uv run python -m app.modules.ingestion.interfaces.cli.run_scraping `
  --source-id <UUID_DE_LA_FUENTE_JUMBO> `
  --scraper jumbo `
  --city "Comodoro Rivadavia" `
  --query "coca cola" `
  --query "leche" `
  --limit 5
```

Para La Coope, usa el identificador de `La Coope public catalog pilot` y el
selector correspondiente:

```powershell
uv run python -m app.modules.ingestion.interfaces.cli.run_scraping `
  --source-id <UUID_DE_LA_FUENTE_LA_COOPE> `
  --scraper coope `
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
- relaciona nombres con la misma clave normalizada o crea un producto valido;
- inserta una observacion de precio por producto fuente, sucursal y fecha sin
  duplicar el historial al reejecutarse.

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
  scraper = "coope"
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

La API de administracion permite crear, listar y activar/desactivar fuentes,
iniciar una corrida por fuente y finalizarla como exitosa o fallida. Solo se
permite una corrida abierta por fuente; estas operaciones no ejecutan scraping.

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
