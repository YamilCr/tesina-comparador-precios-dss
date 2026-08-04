import type {
  Branch,
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
} from '@/types'

const observedAt = '2026-06-01T10:00:00+00:00'

const ids = {
  comodoro: '00000000-0000-4000-8000-000000000001',
  rada: '00000000-0000-4000-8000-000000000002',
  laCentro: '10000000-0000-4000-8000-000000000001',
  carrefour: '10000000-0000-4000-8000-000000000002',
  changomas: '10000000-0000-4000-8000-000000000003',
  laRada: '10000000-0000-4000-8000-000000000004',
}

export const mockProducts: Product[] = [
  { id: '20000000-0000-4000-8000-000000000001', nombre: 'Coca Cola 2.25 L', marca: 'Coca Cola', categoria: 'Bebidas', unidad_medida: 'L', contenido_neto: '2.25', codigo_interno: 'BEB-COCA-225' },
  { id: '20000000-0000-4000-8000-000000000002', nombre: 'Leche Entera 1 L', marca: 'La Serenísima', categoria: 'Lácteos', unidad_medida: 'L', contenido_neto: '1', codigo_interno: 'LAC-LECHE-001' },
  { id: '20000000-0000-4000-8000-000000000003', nombre: 'Arroz Largo Fino 1 Kg', marca: 'Marolio', categoria: 'Almacén', unidad_medida: 'KG', contenido_neto: '1', codigo_interno: 'ALM-ARROZ-001' },
  { id: '20000000-0000-4000-8000-000000000004', nombre: 'Lavandina 1 L', marca: 'Ayudín', categoria: 'Limpieza', unidad_medida: 'L', contenido_neto: '1', codigo_interno: 'LIM-LAV-001' },
  { id: '20000000-0000-4000-8000-000000000005', nombre: 'Papel Higiénico 4 Rollos', marca: 'Elite', categoria: 'Higiene personal', unidad_medida: 'PACK', contenido_neto: '4', codigo_interno: 'HIG-PAPEL-004' },
]

const categories: Category[] = ['Almacén', 'Bebidas', 'Higiene personal', 'Lácteos', 'Limpieza'].map((nombre, index) => ({
  id: `30000000-0000-4000-8000-00000000000${index + 1}`,
  nombre,
}))

const cities: City[] = [
  { id: ids.comodoro, nombre: 'Comodoro Rivadavia', provincia: 'Chubut', latitud: -45.8641, longitud: -67.4966 },
  { id: ids.rada, nombre: 'Rada Tilly', provincia: 'Chubut', latitud: -45.9269, longitud: -67.5542 },
]

const supermarkets: Supermarket[] = [
  { id: '40000000-0000-4000-8000-000000000001', nombre: 'La Anónima' },
  { id: '40000000-0000-4000-8000-000000000002', nombre: 'Carrefour' },
  { id: '40000000-0000-4000-8000-000000000003', nombre: 'Chango Más' },
  { id: '40000000-0000-4000-8000-000000000004', nombre: 'Jumbo' },
]

const branches: Branch[] = [
  { id: ids.laCentro, nombre: 'Centro', direccion: 'San Martín 500', supermercado: 'La Anónima', ciudad: 'Comodoro Rivadavia', latitud: -45.8645, longitud: -67.482 },
  { id: ids.carrefour, nombre: 'Comodoro', direccion: 'Av. Hipólito Yrigoyen 2600', supermercado: 'Carrefour', ciudad: 'Comodoro Rivadavia', latitud: -45.875, longitud: -67.51 },
  { id: ids.changomas, nombre: 'Comodoro', direccion: 'Av. Polonia 1200', supermercado: 'Chango Más', ciudad: 'Comodoro Rivadavia', latitud: -45.846, longitud: -67.5 },
  { id: ids.laRada, nombre: 'Rada Tilly', direccion: 'Av. Moyano 900', supermercado: 'La Anónima', ciudad: 'Rada Tilly', latitud: -45.925, longitud: -67.555 },
]

const prices: Record<string, number[]> = {
  [ids.laCentro]: [2600, 1450, 1800, 1200, 3200],
  [ids.carrefour]: [2550, 1500, 1750, 1150, 3150],
  [ids.changomas]: [2500, 1420, 1700, 1100, 3300],
  [ids.laRada]: [2700, 1480, 1850, 1250, 3400],
}

const distances: Record<string, Record<string, number>> = {
  [ids.comodoro]: { [ids.laCentro]: 1.1, [ids.carrefour]: 1.6, [ids.changomas]: 2, [ids.laRada]: 8.3 },
  [ids.rada]: { [ids.laCentro]: 8.2, [ids.carrefour]: 7.2, [ids.changomas]: 8.6, [ids.laRada]: 0.5 },
}

const paginate = <T>(items: T[]): Paginated<T> => ({
  items,
  pagination: { page: 1, page_size: 20, total: items.length },
})

const currentPriceRows = (): CurrentPrice[] =>
  branches.flatMap((branch) =>
    mockProducts.map((product, index) => ({
      id: `${branch.id}-${index}`,
      producto: product.nombre,
      producto_fuente: product.nombre,
      sucursal: branch.nombre,
      direccion: branch.direccion,
      supermercado: branch.supermercado,
      ciudad: branch.ciudad ?? '',
      precio: prices[branch.id][index].toFixed(2),
      moneda: 'ARS',
      fecha_relevamiento: observedAt,
      disponible: true,
      promocion: false,
    })),
  )

const normalizeCost = (value: number, values: number[]) => {
  const minimum = Math.min(...values)
  const maximum = Math.max(...values)
  return minimum === maximum ? 1 : (maximum - value) / (maximum - minimum)
}

const normalizeBenefit = (value: number, values: number[]) => {
  const minimum = Math.min(...values)
  const maximum = Math.max(...values)
  return minimum === maximum ? 1 : (value - minimum) / (maximum - minimum)
}

export const mockApi: DataClient = {
  async health() {
    return { status: 'ok', service: 'dss-precios-mock' }
  },
  async products(query = '') {
    const search = query.trim().toLocaleLowerCase('es')
    return paginate(mockProducts.filter((product) => product.nombre.toLocaleLowerCase('es').includes(search)))
  },
  async categories() {
    return { items: categories }
  },
  async cities() {
    return { items: cities }
  },
  async supermarkets() {
    return { items: supermarkets }
  },
  async branches(cityId, supermarketId) {
    const cityName = cities.find((city) => city.id === cityId)?.nombre
    const supermarketName = supermarkets.find((supermarket) => supermarket.id === supermarketId)?.nombre
    return paginate(branches.filter((branch) => (!cityName || branch.ciudad === cityName) && (!supermarketName || branch.supermercado === supermarketName)))
  },
  async currentPrices(filters: PriceFilters = {}) {
    const productName = mockProducts.find((product) => product.id === filters.productId)?.nombre
    const cityName = cities.find((city) => city.id === filters.cityId)?.nombre
    const branchName = branches.find((branch) => branch.id === filters.branchId)?.nombre
    const supermarketName = supermarkets.find((supermarket) => supermarket.id === filters.supermarketId)?.nombre
    return paginate(
      currentPriceRows().filter((price) =>
        (!productName || price.producto === productName) &&
        (!cityName || price.ciudad === cityName) &&
        (!branchName || price.sucursal === branchName) &&
        (!supermarketName || price.supermercado === supermarketName),
      ),
    )
  },
  async ranking(request: RankingRequest): Promise<RankingResponse> {
    const city = cities.find((candidate) => candidate.id === request.city_id) ?? cities[0]
    const selected = request.items.map((item) => ({
      product: mockProducts.find((product) => product.id === item.product_id),
      quantity: Number(item.quantity),
    }))
    const complete = branches.map((branch) => {
      const total = selected.reduce((sum, item) => {
        const index = mockProducts.findIndex((product) => product.id === item.product?.id)
        return sum + prices[branch.id][index] * item.quantity
      }, 0)
      return { branch, total, distance: distances[city.id][branch.id] }
    })
    const maxTotal = Math.max(...complete.map((candidate) => candidate.total))
    const totals = complete.map((candidate) => candidate.total)
    const distanceValues = complete.map((candidate) => candidate.distance)
    const savings = complete.map((candidate) => maxTotal - candidate.total)
    const ranking = complete
      .map((candidate, index) => {
        const saving = maxTotal - candidate.total
        const score =
          request.weights.price * normalizeCost(candidate.total, totals) +
          request.weights.distance * normalizeCost(candidate.distance, distanceValues) +
          request.weights.saving * normalizeBenefit(saving, savings)
        return { candidate, saving, score }
      })
      .sort((left, right) => right.score - left.score)
      .map(({ candidate, saving, score }, index) => ({
        posicion: index + 1,
        sucursal: candidate.branch,
        total: candidate.total.toFixed(2),
        distancia_km: candidate.distance.toFixed(2),
        ahorro: saving.toFixed(2),
        puntaje: score.toFixed(4),
      }))
    return {
      origen: { id: city.id, nombre: city.nombre },
      pesos: { precio: String(request.weights.price), distancia: String(request.weights.distance), ahorro: String(request.weights.saving) },
      fecha_relevamiento: observedAt,
      ranking,
      incomplete: [],
    }
  },
}

export const mockSeed = { products: mockProducts, cities, branches, supermarkets }
