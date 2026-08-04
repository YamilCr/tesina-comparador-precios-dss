import { mockApi } from '@/data/mock-data'
import type {
  Category,
  City,
  CurrentPrice,
  DataClient,
  Paginated,
  PriceFilters,
  Product,
  RankingRequest,
  RankingResponse,
  Supermarket,
  Branch,
} from '@/types'

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const isMockMode = (import.meta.env.VITE_API_MODE ?? 'mock') !== 'live'

interface BackendPagination {
  page?: number
  page_size?: number
  count?: number
  total?: number
}

interface BackendPaginated<T> {
  items: T[]
  pagination?: BackendPagination
  count?: number
}

interface BackendProduct {
  id: string
  normalized_name: string
  category_id: string | null
  category_name?: string | null
  brand_id: string | null
  brand_name?: string | null
  unit_measure: string | null
  net_content: string | null
  internal_code: string | null
}

interface BackendCategory {
  id: string
  name: string
}

interface BackendCity {
  id: string
  province_id: string
  province_name?: string | null
  name: string
  latitude: string | null
  longitude: string | null
}

interface BackendSupermarket {
  id: string
  name: string
}

interface BackendBranch {
  id: string
  supermarket_id: string
  supermarket_name?: string | null
  city_id: string
  city_name?: string | null
  name: string
  address: string
  latitude: string
  longitude: string
}

interface BackendPrice {
  id: string
  product_source_id: string
  product_id?: string | null
  product_name?: string | null
  product_source_name?: string | null
  branch_id: string
  branch_name?: string | null
  branch_address?: string | null
  supermarket_id?: string | null
  supermarket_name?: string | null
  city_id?: string | null
  city_name?: string | null
  amount: string
  currency: string
  observed_at: string
  available: boolean
  promotion: boolean
}

interface BackendRankingBranch {
  id: string
  supermarket_id: string
  supermarket_name: string
  city_id: string
  name: string
  address: string
  latitude: string
  longitude: string
}

interface BackendRankingResponse {
  weights: { price: string; distance: string; saving: string }
  observed_at: string | null
  ranking: Array<{
    position: number
    branch: BackendRankingBranch
    total_cost: string
    distance_km: string
    saving: string
    score: string
    missing_products_count: number
  }>
  incomplete_branches: Array<{
    branch: BackendRankingBranch
    missing_products: Array<{ id: string; normalized_name: string }>
  }>
}

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: unknown; error?: { message?: string } }
      | null
    const detailMessage = typeof body?.detail === 'string' ? body.detail : null
    throw new Error(
      body?.error?.message ??
        detailMessage ??
        `No se pudo completar la solicitud (${response.status}).`,
    )
  }
  return response.json() as Promise<T>
}

const queryString = (values: Record<string, string | undefined>) => {
  const query = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => value && query.set(key, value))
  const serialized = query.toString()
  return serialized ? `?${serialized}` : ''
}

const toPagination = <T>(payload: BackendPaginated<T>): Paginated<T> => ({
  items: payload.items,
  pagination: {
    page: payload.pagination?.page ?? 1,
    page_size: payload.pagination?.page_size ?? payload.items.length,
    total: payload.pagination?.total ?? payload.pagination?.count ?? payload.count ?? payload.items.length,
  },
})

const mapProduct = (product: BackendProduct): Product => ({
  id: product.id,
  nombre: product.normalized_name,
  marca: product.brand_name ?? product.brand_id,
  categoria: product.category_name ?? product.category_id,
  unidad_medida: product.unit_measure,
  contenido_neto: product.net_content,
  codigo_interno: product.internal_code,
})

const mapCategory = (category: BackendCategory): Category => ({
  id: category.id,
  nombre: category.name,
})

const mapCity = (city: BackendCity): City => ({
  id: city.id,
  nombre: city.name,
  provincia: city.province_name ?? city.province_id,
  latitud: city.latitude === null ? null : Number(city.latitude),
  longitud: city.longitude === null ? null : Number(city.longitude),
})

const mapSupermarket = (supermarket: BackendSupermarket): Supermarket => ({
  id: supermarket.id,
  nombre: supermarket.name,
})

const mapBranch = (
  branch: BackendBranch,
  supermarkets: Supermarket[] = [],
  cities: City[] = [],
): Branch => {
  const supermarket = supermarkets.find((item) => item.id === branch.supermarket_id)
  const city = cities.find((item) => item.id === branch.city_id)
  return {
    id: branch.id,
    nombre: branch.name,
    direccion: branch.address,
    supermercado: branch.supermarket_name ?? supermarket?.nombre ?? branch.supermarket_id,
    ciudad: branch.city_name ?? city?.nombre ?? branch.city_id,
    latitud: Number(branch.latitude),
    longitud: Number(branch.longitude),
  }
}

const mapRankingBranch = (branch: BackendRankingBranch, cities: City[] = []): Branch => {
  const city = cities.find((item) => item.id === branch.city_id)
  return {
    id: branch.id,
    nombre: branch.name,
    direccion: branch.address,
    supermercado: branch.supermarket_name,
    ciudad: city?.nombre ?? branch.city_id,
    latitud: Number(branch.latitude),
    longitud: Number(branch.longitude),
  }
}

const fetchCatalogProducts = async (query = '') => {
  const payload = await request<BackendPaginated<BackendProduct>>(
    `/api/v1/catalog/products${queryString({ q: query })}`,
  )
  return toPagination({ ...payload, items: payload.items.map(mapProduct) })
}

const fetchCategories = async () => {
  const payload = await request<{ items: BackendCategory[] }>('/api/v1/catalog/categories')
  return { items: payload.items.map(mapCategory) }
}

const fetchCities = async () => {
  const payload = await request<{ items: BackendCity[] }>('/api/v1/locations/cities')
  return { items: payload.items.map(mapCity) }
}

const fetchSupermarkets = async () => {
  const payload = await request<{ items: BackendSupermarket[] }>('/api/v1/supermarkets')
  return { items: payload.items.map(mapSupermarket) }
}

const fetchBranches = async (cityId?: string, supermarketId?: string) => {
  const [branchPayload, cityPayload, supermarketPayload] = await Promise.all([
    request<BackendPaginated<BackendBranch>>(
      `/api/v1/branches${queryString({ city_id: cityId, supermarket_id: supermarketId })}`,
    ),
    fetchCities(),
    fetchSupermarkets(),
  ])
  return toPagination({
    ...branchPayload,
    items: branchPayload.items.map((branch) =>
      mapBranch(branch, supermarketPayload.items, cityPayload.items),
    ),
  })
}

const fetchCurrentPrices = async (filters: PriceFilters = {}) => {
  const [pricePayload, branchPayload, productPayload] = await Promise.all([
    request<BackendPaginated<BackendPrice>>(
      `/api/v1/prices/current${queryString({
        product_id: filters.productId,
        city_id: filters.cityId,
        branch_id: filters.branchId,
        supermarket_id: filters.supermarketId,
      })}`,
    ),
    fetchBranches(filters.cityId, filters.supermarketId),
    fetchCatalogProducts(),
  ])
  const branchesById = new Map(branchPayload.items.map((branch) => [branch.id, branch]))
  const product = productPayload.items.find((item) => item.id === filters.productId)
  return toPagination({
    ...pricePayload,
    items: pricePayload.items.map((price): CurrentPrice => {
      const branch = branchesById.get(price.branch_id)
      return {
        id: price.id,
        producto: price.product_name ?? product?.nombre ?? price.product_source_id,
        producto_fuente: price.product_source_name ?? price.product_source_id,
        sucursal: price.branch_name ?? branch?.nombre ?? price.branch_id,
        direccion: price.branch_address ?? branch?.direccion ?? '',
        supermercado: price.supermarket_name ?? branch?.supermercado ?? '',
        ciudad: price.city_name ?? branch?.ciudad ?? '',
        precio: price.amount,
        moneda: price.currency,
        fecha_relevamiento: price.observed_at,
        disponible: price.available,
        promocion: price.promotion,
      }
    }),
  })
}

const fetchRanking = async (rankingRequest: RankingRequest): Promise<RankingResponse> => {
  const [payload, cityPayload] = await Promise.all([
    request<BackendRankingResponse>('/api/v1/decisions/ranking', {
      method: 'POST',
      body: JSON.stringify(rankingRequest),
    }),
    fetchCities(),
  ])
  const city = cityPayload.items.find((item) => item.id === rankingRequest.city_id)
  return {
    origen: {
      id: rankingRequest.city_id,
      nombre: city?.nombre ?? rankingRequest.city_id,
    },
    pesos: {
      precio: payload.weights.price,
      distancia: payload.weights.distance,
      ahorro: payload.weights.saving,
    },
    fecha_relevamiento: payload.observed_at,
    ranking: payload.ranking.map((item) => ({
      posicion: item.position,
      sucursal: mapRankingBranch(item.branch, cityPayload.items),
      total: item.total_cost,
      distancia_km: item.distance_km,
      ahorro: item.saving,
      puntaje: item.score,
    })),
    incomplete: payload.incomplete_branches.map((item) => ({
      sucursal: mapRankingBranch(item.branch, cityPayload.items),
      productos_faltantes: item.missing_products.map((product) => ({
        id: product.id,
        nombre: product.normalized_name,
      })),
    })),
  }
}

const liveApi: DataClient = {
  health: () => request('/health'),
  products: fetchCatalogProducts,
  categories: fetchCategories,
  cities: fetchCities,
  supermarkets: fetchSupermarkets,
  branches: fetchBranches,
  currentPrices: fetchCurrentPrices,
  ranking: fetchRanking,
}

export const api = isMockMode ? mockApi : liveApi
export const apiMode = isMockMode ? 'mock' : 'live'
