export interface Pagination {
  page: number
  page_size: number
  total: number
}

export interface Paginated<T> {
  items: T[]
  pagination: Pagination
}

export interface Product {
  id: string
  nombre: string
  marca: string | null
  categoria: string | null
  unidad_medida: string | null
  contenido_neto: string | null
  codigo_interno: string | null
}

export interface Category {
  id: string
  nombre: string
}

export interface City {
  id: string
  nombre: string
  provincia: string
  latitud: number | null
  longitud: number | null
}

export interface Supermarket {
  id: string
  nombre: string
}

export interface Branch {
  id: string
  nombre: string
  direccion: string
  supermercado: string
  ciudad: string | null
  latitud: number
  longitud: number
  coordenadas_verificadas: boolean
  fuente_coordenadas: string | null
}

export interface CurrentPrice {
  id: string
  productId: string | null
  producto: string
  producto_fuente: string
  sucursal: string
  direccion: string
  supermercado: string
  ciudad: string
  precio: string
  moneda: string
  fecha_relevamiento: string
  disponible: boolean
  promocion: boolean
  calidad: 'fresh' | 'stale' | 'suspect'
  motivo_calidad: string | null
  antiguedad_dias: number
}

export interface BasketItem {
  product: Product
  quantity: number
}

export interface RankingWeights {
  price: number
  distance: number
  saving: number
}

export interface RankingRequest {
  city_id: string
  branch_ids?: string[]
  origin_latitude?: number
  origin_longitude?: number
  items: Array<{ product_id: string; quantity: string }>
  weights: RankingWeights
}

export interface RankingOrigin {
  id: string | null
  nombre: string
  latitud: number
  longitud: number
  fuente: 'city' | 'user'
}

export interface RankedBranch {
  posicion: number
  sucursal: Branch
  total: string
  distancia_km: string
  ahorro: string
  puntaje: string
}

export interface IncompleteBranch {
  sucursal: Branch
  productos_faltantes: Array<{
    id: string
    nombre: string
    motivo: 'missing' | 'stale' | 'suspect'
  }>
}

export interface RankingQuality {
  fecha_evaluacion: string
  antiguedad_maxima_dias: number
  precios_aptos: number
  precios_vencidos: number
  precios_sospechosos: number
}

export interface RankingResponse {
  origen: RankingOrigin
  pesos: { precio: string; distancia: string; ahorro: string }
  fecha_relevamiento: string | null
  ranking: RankedBranch[]
  incomplete: IncompleteBranch[]
  calidad: RankingQuality
}

export interface PriceFilters {
  productId?: string
  cityId?: string
  branchId?: string
  supermarketId?: string
}

export interface ScrapingSource {
  id: string
  nombre: string
  scraperKey: string
  branchId: string | null
  active: boolean
}

export interface LiveRefreshRequest {
  source_ids: string[]
  queries: string[]
  city: string
  limit: number
  max_concurrency: number
  timeout_seconds: number
}

export interface LiveRefreshSourceResult {
  sourceId: string
  sourceName: string
  status: string
  durationMs: number
  scraped: number
  loaded: number
  rejected: number
  errorMessage: string | null
}

export interface LiveRefreshResponse {
  results: LiveRefreshSourceResult[]
}

export interface DataClient {
  health(): Promise<{ status: string; service: string }>
  products(query?: string): Promise<Paginated<Product>>
  categories(): Promise<{ items: Category[] }>
  cities(): Promise<{ items: City[] }>
  supermarkets(): Promise<{ items: Supermarket[] }>
  branches(cityId?: string, supermarketId?: string): Promise<Paginated<Branch>>
  currentPrices(filters?: PriceFilters): Promise<Paginated<CurrentPrice>>
  scrapingSources(): Promise<{ items: ScrapingSource[] }>
  refreshPrices(request: LiveRefreshRequest): Promise<LiveRefreshResponse>
  ranking(request: RankingRequest): Promise<RankingResponse>
}
