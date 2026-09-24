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
  image_url?: string | null
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
  substitutions?: SubstitutionSelection[]
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
  basket_type?: 'original' | 'substituted'
  substitutions?: SubstitutionCandidate[]
  posicion: number
  sucursal: Branch
  total: string
  distancia_km: string
  ahorro: string
  puntaje: string
}

export interface IncompleteBranch {
  accepted_substitutions?: boolean
  distance_km?: string
  covered_products_count?: number
  total_products_count?: number
  substitutions?: SubstitutionCandidate[]
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
  substitutions(request: SuggestionsRequest): Promise<SuggestionsResponse>
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

export interface SubstitutionSelection {
  branch_id: string
  original_product_id: string
  replacement_product_id: string
}

export interface SubstitutionCandidate {
  original_product_id: string
  original_name?: string
  product: {
    id: string
    normalized_name: string
    brand_name: string | null
    image_url?: string | null
    unit_measure: string | null
    net_content: string | null
    base_quantity?: string | null
    base_unit?: string | null
    pack_size?: number | null
  }
  quantity: string
  unit_price: string
  subtotal: string
  currency: string
  observed_at: string
  price_branch_id: string
  inferred_from_chain: boolean
  compatibility_reason: string
}

export interface SuggestionsRequest {
  branch_id: string
  items: RankingRequest['items']
  max_price_age_days?: number
}

export interface SuggestionsResponse {
  branch_id: string
  evaluated_at: string
  items: Array<{
    original: SubstitutionCandidate['product']
    quantity: string
    reason: 'missing' | 'stale' | 'suspect'
    candidates: SubstitutionCandidate[]
    diagnostics?: SubstitutionDiagnostics
  }>
}

export interface SubstitutionDiagnostics {
  code: 'available' | 'insufficient_attributes' | 'no_chain_products' | 'no_compatible_products' | 'no_suitable_prices'
  compatible_products: number
  stale_products: number
  suspect_products: number
  max_price_age_days: number
}
