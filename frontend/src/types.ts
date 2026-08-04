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
}

export interface CurrentPrice {
  id: string
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
  items: Array<{ product_id: string; quantity: string }>
  weights: RankingWeights
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
  productos_faltantes: Array<{ id: string; nombre: string }>
}

export interface RankingResponse {
  origen: { id: string; nombre: string }
  pesos: { precio: string; distancia: string; ahorro: string }
  fecha_relevamiento: string | null
  ranking: RankedBranch[]
  incomplete: IncompleteBranch[]
}

export interface PriceFilters {
  productId?: string
  cityId?: string
  branchId?: string
  supermarketId?: string
}

export interface DataClient {
  health(): Promise<{ status: string; service: string }>
  products(query?: string): Promise<Paginated<Product>>
  categories(): Promise<{ items: Category[] }>
  cities(): Promise<{ items: City[] }>
  supermarkets(): Promise<{ items: Supermarket[] }>
  branches(cityId?: string, supermarketId?: string): Promise<Paginated<Branch>>
  currentPrices(filters?: PriceFilters): Promise<Paginated<CurrentPrice>>
  ranking(request: RankingRequest): Promise<RankingResponse>
}
