# Contrato API Backend DSS para Frontend

Fecha de análisis: 2026-08-05  
Backend analizado: FastAPI `0.1.0` expuesto desde `app.main`

Este contrato describe la API HTTP que el frontend puede consumir. Está basado en los routers reales registrados en `backend/app/api_v1.py`.

## Configuración base

- Base URL local recomendada para el frontend: `http://127.0.0.1:8000`
- Prefijo API: `/api/v1`
- Healthcheck fuera del prefijo: `/health`
- No hay autenticación implementada actualmente.
- El backend devuelve JSON.
- Los UUID se serializan como `string`.
- Los `Decimal` se serializan como `string` en las respuestas. En requests conviene enviarlos como `string` para evitar errores de precisión.
- Las fechas son `datetime` ISO 8601.

Variables relevantes:

```env
VITE_API_MODE=live
VITE_API_BASE_URL=http://127.0.0.1:8000
```

En backend:

```env
APP_NAME=price-dss-backend
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///price_dss_demo.db
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

Nota: el backend permite CORS para `GET`, `POST` y `PATCH`.

## Formatos comunes

### Colección simple

```ts
type CollectionResponse<T> = {
  items: T[]
  count: number
}
```

### Colección paginada

```ts
type PaginatedResponse<T> = {
  items: T[]
  count: number
  pagination: {
    page: number
    page_size: number
    count: number
    total: number
  }
}
```

### Error

```ts
type ApiError = {
  detail: string | unknown[]
  error: {
    code: 'http_error' | 'validation_error'
    message: string
    details: string | unknown[]
  }
}
```

Ejemplo:

```json
{
  "detail": "Ciudad no encontrada.",
  "error": {
    "code": "http_error",
    "message": "Ciudad no encontrada.",
    "details": "Ciudad no encontrada."
  }
}
```

Para formularios, mostrar preferentemente `error.message`.

## Endpoints disponibles

| Método | Endpoint | Uso frontend |
|---|---|---|
| GET | `/health` | Verificar backend online |
| GET | `/api/v1/catalog/products` | Catálogo/buscador de productos |
| GET | `/api/v1/catalog/categories` | Filtros o etiquetas de catálogo |
| GET | `/api/v1/catalog/brands` | Filtros o etiquetas de marcas |
| GET | `/api/v1/locations/cities` | Selector de ciudad/origen |
| GET | `/api/v1/supermarkets` | Selector/filtro supermercado |
| GET | `/api/v1/branches` | Sucursales por ciudad/supermercado |
| GET | `/api/v1/prices/current` | Precios vigentes |
| GET | `/api/v1/prices/history` | Historial por producto fuente |
| GET | `/api/v1/prices/compare` | Comparar precios por productos |
| POST | `/api/v1/basket/validate` | Validar canasta temporal |
| POST | `/api/v1/decisions/ranking` | Ranking DSS |
| GET | `/api/v1/ingestion/sources` | Admin fuentes scraping |
| POST | `/api/v1/ingestion/sources` | Crear fuente scraping |
| PATCH | `/api/v1/ingestion/sources/{source_id}` | Editar fuente scraping |
| GET | `/api/v1/ingestion/runs` | Auditoría scraping |
| POST | `/api/v1/ingestion/sources/{source_id}/runs` | Iniciar corrida scraping |
| GET | `/api/v1/ingestion/schedules` | Listar planes automáticos |
| POST | `/api/v1/ingestion/schedules` | Crear plan automático |
| PATCH | `/api/v1/ingestion/schedules/{schedule_id}` | Editar o desactivar plan |
| POST | `/api/v1/ingestion/schedules/{schedule_id}/run-now` | Ejecutar plan inmediatamente |
| GET | `/api/v1/ingestion/schedule-executions` | Historial del scheduler |
| POST | `/api/v1/ingestion/runs/{run_id}/succeed` | Marcar corrida exitosa |
| POST | `/api/v1/ingestion/runs/{run_id}/fail` | Marcar corrida fallida |

## Catálogo

### `GET /api/v1/catalog/products`

Lista o busca productos activos.

Query params:

| Nombre | Tipo | Default | Reglas |
|---|---:|---:|---|
| `q` | `string` | `null` | Máx. 120 chars |
| `category_id` | `UUID` | `null` | Opcional |
| `page` | `number` | `1` | `>= 1` |
| `page_size` | `number` | `20` | `1..100` |

Respuesta:

```ts
type ProductResponse = {
  id: string
  normalized_name: string
  category_id: string | null
  category_name: string | null
  brand_id: string | null
  brand_name: string | null
  description: string | null
  unit_measure: string | null
  net_content: string | null
  internal_code: string | null
}
```

```ts
PaginatedResponse<ProductResponse>
```

Ejemplo:

```http
GET /api/v1/catalog/products?q=coca&page_size=10
```

Nota frontend: si `q` está presente, el backend usa búsqueda por límite (`page_size`). No asumir todavía paginación global perfecta para búsqueda; usarlo como buscador/autocomplete.

### `GET /api/v1/catalog/categories`

Respuesta:

```ts
type ProductCategoryResponse = {
  id: string
  name: string
  description: string | null
  parent_category_id: string | null
}

CollectionResponse<ProductCategoryResponse>
```

### `GET /api/v1/catalog/brands`

Query params:

| Nombre | Tipo | Default |
|---|---:|---:|
| `active_only` | `boolean` | `true` |

Respuesta:

```ts
type BrandResponse = {
  id: string
  name: string
  description: string | null
}

CollectionResponse<BrandResponse>
```

## Localización y supermercados

### `GET /api/v1/locations/cities`

Respuesta:

```ts
type CityResponse = {
  id: string
  province_id: string
  province_name: string | null
  name: string
  postal_code: string | null
  latitude: string | null
  longitude: string | null
}

CollectionResponse<CityResponse>
```

### `GET /api/v1/supermarkets`

Respuesta:

```ts
type SupermarketResponse = {
  id: string
  name: string
  website_url: string | null
}

CollectionResponse<SupermarketResponse>
```

### `GET /api/v1/branches`

Query params:

| Nombre | Tipo | Default | Reglas |
|---|---:|---:|---|
| `city_id` | `UUID` | `null` | Opcional |
| `supermarket_id` | `UUID` | `null` | Opcional |
| `page` | `number` | `1` | `>= 1` |
| `page_size` | `number` | `20` | `1..100` |

Respuesta:

```ts
type BranchResponse = {
  id: string
  supermarket_id: string
  supermarket_name: string | null
  city_id: string
  city_name: string | null
  name: string
  address: string
  latitude: string
  longitude: string
}

PaginatedResponse<BranchResponse>
```

Ejemplo:

```http
GET /api/v1/branches?city_id={cityId}&supermarket_id={supermarketId}&page_size=100
```

## Precios

### `GET /api/v1/prices/current`

Devuelve precios actuales. “Actual” significa el último precio disponible por producto fuente y sucursal.

Query params:

| Nombre | Tipo | Default | Reglas |
|---|---:|---:|---|
| `product_id` | `UUID` | `null` | Producto normalizado |
| `product_source_id` | `UUID` | `null` | Producto fuente |
| `branch_id` | `UUID` | `null` | Filtro ubicación |
| `city_id` | `UUID` | `null` | Filtro ubicación |
| `supermarket_id` | `UUID` | `null` | Filtro supermercado |
| `limit` | `number` | `100` | `1..500` |

Reglas:

- Puede llamarse sin filtros; devuelve precios actuales globales hasta `limit`.
- `product_source_id` no debe combinarse con `product_id`.
- Los filtros de ubicación pueden reducir la respuesta.

Respuesta:

```ts
type PriceResponse = {
  id: string
  product_source_id: string
  product_id: string | null
  product_name: string | null
  product_source_name: string | null
  branch_id: string
  branch_name: string | null
  branch_address: string | null
  supermarket_id: string | null
  supermarket_name: string | null
  city_id: string | null
  city_name: string | null
  amount: string
  currency: string
  observed_at: string
  available: boolean
  promotion: boolean
}

CollectionResponse<PriceResponse>
```

Ejemplos:

```http
GET /api/v1/prices/current?city_id={cityId}&limit=100
GET /api/v1/prices/current?product_id={productId}&supermarket_id={supermarketId}
GET /api/v1/prices/current?branch_id={branchId}
```

### `GET /api/v1/prices/history`

Historial de precios para un producto fuente.

Query params:

| Nombre | Tipo | Default | Reglas |
|---|---:|---:|---|
| `product_source_id` | `UUID` | requerido | Obligatorio |
| `branch_id` | `UUID` | `null` | Opcional |
| `limit` | `number` | `100` | `1..500` |

Respuesta:

```ts
CollectionResponse<PriceResponse>
```

### `GET /api/v1/prices/compare`

Compara precios actuales para uno o más productos normalizados.

Query params:

| Nombre | Tipo | Default | Reglas |
|---|---:|---:|---|
| `product_ids` | `UUID[]` | requerido | Al menos 1 |
| `branch_id` | `UUID` | `null` | Opcional |
| `city_id` | `UUID` | `null` | Opcional |
| `supermarket_id` | `UUID` | `null` | Opcional |
| `limit` | `number` | `100` | `1..500` |

Enviar arrays como query repetida:

```http
GET /api/v1/prices/compare?product_ids={id1}&product_ids={id2}&city_id={cityId}
```

Respuesta:

```ts
CollectionResponse<PriceResponse>
```

## Canasta temporal

### `POST /api/v1/basket/validate`

Valida y consolida una canasta temporal. No persiste datos.

Body:

```ts
type BasketLineRequest = {
  product_id: string
  quantity: string
}

type BasketRequest = {
  items: BasketLineRequest[]
}
```

Reglas:

- `items`: mínimo 1, máximo 100.
- `quantity`: decimal `> 0`, máximo 12 dígitos y 3 decimales.
- No puede repetirse el mismo `product_id`.

Ejemplo:

```json
{
  "items": [
    { "product_id": "00000000-0000-0000-0000-000000000041", "quantity": "2" },
    { "product_id": "00000000-0000-0000-0000-000000000042", "quantity": "1" }
  ]
}
```

Respuesta:

```ts
type BasketValidateResponse = CollectionResponse<{
  product_id: string
  quantity: string
}> & {
  total_items: number
  product_ids: string[]
}
```

## Ranking DSS

### `POST /api/v1/decisions/ranking`

Calcula ranking multicriterio para una canasta temporal.

Body:

```ts
type RankingWeightsRequest = {
  price: string
  distance: string
  saving: string
}

type RankingRequest = {
  items: BasketLineRequest[]
  origin_latitude?: string | null
  origin_longitude?: string | null
  city_id?: string | null
  branch_ids?: string[] | null
  weights?: RankingWeightsRequest
}
```

Reglas:

- Debe enviarse `city_id` o el par completo `origin_latitude` + `origin_longitude`.
- Si se envían coordenadas, deben venir ambas.
- `weights` por defecto: `{ price: "0.6", distance: "0.3", saving: "0.1" }`.
- Los pesos no pueden ser negativos.
- Los pesos deben sumar exactamente `1`.
- No repetir productos en `items`.

Recomendación frontend: convertir sliders porcentuales a strings decimales.

```ts
const asWeight = (value: number) => (value / 100).toFixed(2)

const body = {
  city_id,
  items: basket.map((item) => ({
    product_id: item.product.id,
    quantity: String(item.quantity),
  })),
  weights: {
    price: asWeight(priceWeight),
    distance: asWeight(distanceWeight),
    saving: asWeight(100 - priceWeight - distanceWeight),
  },
}
```

Respuesta:

```ts
type RankingBranch = {
  id: string
  supermarket_id: string
  supermarket_name: string
  city_id: string
  name: string
  address: string
  latitude: string
  longitude: string
}

type RankingResult = {
  position: number
  branch: RankingBranch
  total_cost: string
  distance_km: string
  saving: string
  score: string
  missing_products_count: number
}

type IncompleteBranch = {
  branch: RankingBranch
  missing_products: Array<{
    id: string
    normalized_name: string
  }>
}

type RankingResponse = {
  count: number
  incomplete_count: number
  weights: {
    price: string
    distance: string
    saving: string
  }
  observed_at: string | null
  ranking: RankingResult[]
  incomplete_branches: IncompleteBranch[]
}
```

Ejemplo:

```json
{
  "city_id": "00000000-0000-0000-0000-000000000001",
  "items": [
    { "product_id": "00000000-0000-0000-0000-000000000041", "quantity": "1" }
  ],
  "weights": {
    "price": "0.60",
    "distance": "0.30",
    "saving": "0.10"
  }
}
```

Nota frontend: la respuesta de ranking trae `city_id` en la sucursal, no `city_name`. Para mostrar ciudad, mapear con `/api/v1/locations/cities`.

## Ingestion / scraping admin

Estos endpoints sirven para administración y auditoría de fuentes de scraping. No deberían exponerse en una landing pública sin autenticación.

### Tipos

```ts
type ScrapingSourceResponse = {
  id: string
  supermarket_id: string
  name: string
  base_url: string
  scraper_key: string
  branch_id: string | null
  active: boolean
  created_at: string | null
}

type ScrapingRunResponse = {
  id: string
  scraping_source_id: string
  status: string
  started_at: string
  finished_at: string | null
  items_scraped: number
  items_loaded: number
  error_message: string | null
}

type ScrapingScheduleResponse = {
  id: string
  scraping_source_id: string
  name: string
  queries: string[]
  city: string
  interval_minutes: number
  retry_delay_minutes: number
  result_limit: number
  timeout_seconds: number
  enabled: boolean
  next_run_at: string
  locked_until: string | null
  consecutive_failures: number
  created_at: string | null
  updated_at: string | null
}

type ScheduledRefreshExecutionResponse = {
  id: string
  schedule_id: string
  scraping_run_id: string | null
  status: "running" | "succeeded" | "failed"
  scheduled_for: string
  started_at: string
  finished_at: string | null
  error_message: string | null
}
```

### `GET /api/v1/ingestion/sources`

Query params:

| Nombre | Tipo | Default |
|---|---:|---:|
| `active_only` | `boolean \| null` | `null` |

Respuesta:

```ts
CollectionResponse<ScrapingSourceResponse>
```

### `POST /api/v1/ingestion/sources`

Body:

```ts
type CreateScrapingSourceRequest = {
  supermarket_id: string
  name: string
  base_url: string
  active: boolean
}
```

Respuesta `201`:

```ts
ScrapingSourceResponse
```

### `PATCH /api/v1/ingestion/sources/{source_id}`

Body:

```ts
type UpdateScrapingSourceRequest = {
  name?: string | null
  base_url?: string | null
  active?: boolean | null
}
```

Respuesta:

```ts
ScrapingSourceResponse
```

`PATCH` esta habilitado en CORS para el frontend local.

### Scheduler automatico

`POST /api/v1/ingestion/schedules` crea un plan por fuente con `queries`, `city`,
`interval_minutes`, `retry_delay_minutes`, `result_limit`, `timeout_seconds`,
`next_run_at` opcional y `enabled`. `PATCH /api/v1/ingestion/schedules/{schedule_id}`
acepta esos campos de forma parcial.

`GET /api/v1/ingestion/schedules` acepta `enabled_only`. La ejecucion manual se
realiza con `POST /api/v1/ingestion/schedules/{schedule_id}/run-now` y devuelve
`ScheduledRefreshExecutionResponse`.

`GET /api/v1/ingestion/schedule-executions` acepta `schedule_id` opcional y
`limit` entre 1 y 500. Devuelve
`CollectionResponse<ScheduledRefreshExecutionResponse>`.

### `GET /api/v1/ingestion/runs`

Query params:

| Nombre | Tipo | Default | Reglas |
|---|---:|---:|---|
| `source_id` | `UUID` | `null` | Opcional |
| `limit` | `number` | `100` | `1..500` |

Respuesta:

```ts
CollectionResponse<ScrapingRunResponse>
```

### `POST /api/v1/ingestion/sources/{source_id}/runs`

Inicia una corrida de scraping para una fuente.

Respuesta `201`:

```ts
ScrapingRunResponse
```

### `POST /api/v1/ingestion/runs/{run_id}/succeed`

Body:

```ts
type CompleteScrapingRunRequest = {
  items_scraped: number
  items_loaded: number
}
```

Reglas: ambos `>= 0`.

Respuesta:

```ts
ScrapingRunResponse
```

### `POST /api/v1/ingestion/runs/{run_id}/fail`

Body:

```ts
type FailScrapingRunRequest = {
  error_message: string
}
```

Reglas: `error_message` entre 1 y 2000 caracteres.

Respuesta:

```ts
ScrapingRunResponse
```

## Mapeo recomendado para el frontend actual

El backend usa nombres en inglés y `snake_case`. El frontend actual puede mapearlos a nombres de UI en español.

```ts
const mapProduct = (product: ProductResponse) => ({
  id: product.id,
  nombre: product.normalized_name,
  marca: product.brand_name ?? product.brand_id,
  categoria: product.category_name ?? product.category_id,
  unidad_medida: product.unit_measure,
  contenido_neto: product.net_content,
  codigo_interno: product.internal_code,
})

const mapCity = (city: CityResponse) => ({
  id: city.id,
  nombre: city.name,
  provincia: city.province_name ?? city.province_id,
  latitud: city.latitude === null ? null : Number(city.latitude),
  longitud: city.longitude === null ? null : Number(city.longitude),
})

const mapBranch = (branch: BranchResponse) => ({
  id: branch.id,
  nombre: branch.name,
  direccion: branch.address,
  supermercado: branch.supermarket_name ?? branch.supermarket_id,
  ciudad: branch.city_name ?? branch.city_id,
  latitud: Number(branch.latitude),
  longitud: Number(branch.longitude),
})

const mapPrice = (price: PriceResponse) => ({
  id: price.id,
  producto: price.product_name ?? price.product_source_name ?? price.product_source_id,
  producto_fuente: price.product_source_name ?? price.product_source_id,
  sucursal: price.branch_name ?? price.branch_id,
  direccion: price.branch_address ?? '',
  supermercado: price.supermarket_name ?? price.supermarket_id ?? '',
  ciudad: price.city_name ?? price.city_id ?? '',
  precio: price.amount,
  moneda: price.currency,
  fecha_relevamiento: price.observed_at,
  disponible: price.available,
  promocion: price.promotion,
})
```

## Secuencia recomendada por pantalla

### Landing `/`

- No necesita backend.
- CTAs apuntan a `/comparar` y `/datos`.

### Comparador `/comparar`

1. `GET /api/v1/locations/cities`
2. `GET /api/v1/catalog/products?page_size=100`
3. Usuario arma canasta local.
4. Opcional: `POST /api/v1/basket/validate` antes de ranking.
5. `POST /api/v1/decisions/ranking`
6. Para mostrar ciudad en ranking, reutilizar cache de ciudades.

### Datos `/datos`

1. `GET /health`
2. `GET /api/v1/catalog/products?page_size=100`
3. `GET /api/v1/locations/cities`
4. `GET /api/v1/supermarkets`
5. `GET /api/v1/branches?city_id={cityId?}&supermarket_id={supermarketId?}&page_size=100`
6. `GET /api/v1/prices/current?city_id={cityId?}&supermarket_id={supermarketId?}&limit=500`

`prices/current` no es paginado; usar `limit`.

## Desalineaciones / cuidados detectados

1. No hay auth. No exponer ingestion admin en producción sin permisos.
2. Los decimales deben tratarse como strings en contrato externo.
3. En ranking, los pesos deben sumar exactamente `1`; evitar floats crudos.
4. El frontend no debe asumir que `city_name` viene en `RankingBranch`; debe resolverlo por `city_id`.
6. Las colecciones de precios son `CollectionResponse`, no `PaginatedResponse`.
7. La búsqueda de productos con `q` funciona como autocomplete por `page_size`; no confiar todavía en paginación global exacta para esa búsqueda.
