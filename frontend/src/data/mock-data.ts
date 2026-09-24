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
  SubstitutionCandidate,
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

const substitutionProduct: Product = { ...mockProducts[1], id: '20000000-0000-4000-8000-000000000006', nombre: 'Leche Entera SanCor 1 L', marca: 'SanCor', codigo_interno: 'LAC-SANCOR-001' }
const catalog = [...mockProducts, substitutionProduct]

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
  { id: ids.laCentro, nombre: 'Sucursal 024 Alem', direccion: 'Leandro Alem 962', supermercado: 'La Anónima', ciudad: 'Comodoro Rivadavia', latitud: -45.860429, longitud: -67.498914, coordenadas_verificadas: true, fuente_coordenadas: 'La Anónima y OpenStreetMap' },
  { id: ids.carrefour, nombre: 'Comodoro Centro', direccion: 'Pellegrini 851', supermercado: 'Carrefour', ciudad: 'Comodoro Rivadavia', latitud: -45.861941, longitud: -67.480174, coordenadas_verificadas: true, fuente_coordenadas: 'Carrefour y OpenStreetMap' },
  { id: ids.changomas, nombre: 'Comodoro', direccion: 'Enrique Girolamo 3100', supermercado: 'Chango Más', ciudad: 'Comodoro Rivadavia', latitud: -45.883411, longitud: -67.524666, coordenadas_verificadas: true, fuente_coordenadas: 'Más Online y verificación cartográfica' },
  { id: ids.laRada, nombre: 'Rada Tilly', direccion: 'Francisco Luque 1200', supermercado: 'La Anónima', ciudad: 'Rada Tilly', latitud: -45.929773, longitud: -67.572098, coordenadas_verificadas: true, fuente_coordenadas: 'La Anónima y OpenStreetMap' },
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

// Controlled demo: this extra product is absent in La Anonima, without changing the original seed.
const productPrice = (branchId: string, productId: string): number | undefined => {
  if (productId === substitutionProduct.id) return [ids.laCentro, ids.laRada].includes(branchId) ? undefined : 1550
  return prices[branchId]?.[mockProducts.findIndex((p) => p.id === productId)]
}
const mockCompatible = (original: string, replacement: string) => original !== replacement &&
  [mockProducts[1].id, substitutionProduct.id].includes(original) && [mockProducts[1].id, substitutionProduct.id].includes(replacement)
const suggestionProduct = (p: Product): SubstitutionCandidate['product'] => ({
  id: p.id, normalized_name: p.nombre, brand_name: p.marca, image_url: p.image_url,
  net_content: p.contenido_neto, unit_measure: p.unidad_medida,
})
const mockCandidate = (branchId: string, original: string, replacement: Product, quantity: string): SubstitutionCandidate => ({
  original_product_id: original, original_name: catalog.find((p) => p.id === original)?.nombre,
  product: suggestionProduct(replacement), quantity, unit_price: String(productPrice(branchId, replacement.id)),
  subtotal: String(productPrice(branchId, replacement.id)! * Number(quantity)), currency: 'ARS',
  observed_at: observedAt, price_branch_id: branchId, inferred_from_chain: false,
  compatibility_reason: 'Mismo tipo, variantes y presentación; otra marca.',
})

const paginate = <T>(items: T[]): Paginated<T> => ({
  items,
  pagination: { page: 1, page_size: 20, total: items.length },
})

const currentPriceRows = (): CurrentPrice[] =>
  branches.flatMap((branch) =>
    catalog.filter((product) => productPrice(branch.id, product.id) !== undefined).map((product, index) => ({
      id: `${branch.id}-${index}`,
      productId: product.id,
      producto: product.nombre,
      producto_fuente: product.nombre,
      sucursal: branch.nombre,
      direccion: branch.direccion,
      supermercado: branch.supermercado,
      ciudad: branch.ciudad ?? '',
      precio: productPrice(branch.id, product.id)!.toFixed(2),
      moneda: 'ARS',
      fecha_relevamiento: observedAt,
      disponible: true,
      promocion: false,
      calidad: 'fresh' as const,
      motivo_calidad: null,
      antiguedad_dias: 0,
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
    return paginate(catalog.filter((product) => product.nombre.toLocaleLowerCase('es').includes(search)))
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
    const productName = catalog.find((product) => product.id === filters.productId)?.nombre
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
  async scrapingSources() {
    return { items: [] }
  },
  async refreshPrices() {
    return { results: [] }
  },
  async substitutions(request) {
    if (!branches.some((b) => b.id === request.branch_id)) throw new Error('Sucursal no habilitada.')
    return {
      branch_id: request.branch_id, evaluated_at: observedAt,
      items: request.items.filter((line) => productPrice(request.branch_id, line.product_id) === undefined).map((line) => {
        const original = catalog.find((p) => p.id === line.product_id)
        if (!original) throw new Error('Producto inexistente.')
        return { original: suggestionProduct(original), quantity: line.quantity, reason: 'missing' as const,
          candidates: catalog.filter((p) => mockCompatible(original.id, p.id) && productPrice(request.branch_id, p.id) !== undefined)
            .map((p) => mockCandidate(request.branch_id, original.id, p, line.quantity))
            .sort((a, b) => Number(a.subtotal) - Number(b.subtotal) || a.product.normalized_name.localeCompare(b.product.normalized_name)).slice(0, 3),
        }
      }),
    }
  },
  async ranking(request: RankingRequest): Promise<RankingResponse> {
    const city = cities.find((candidate) => candidate.id === request.city_id) ?? cities[0]
    const selected = request.items.map((item) => ({
      product: catalog.find((product) => product.id === item.product_id),
      quantity: Number(item.quantity),
    }))
    const requestedBranchIds = request.branch_ids ? new Set(request.branch_ids) : null
    const substitutions = request.substitutions ?? []
    const seen = new Set<string>()
    for (const s of substitutions) {
      const key = `${s.branch_id}:${s.original_product_id}`
      if (seen.has(key) || !branches.some((b) => b.id === s.branch_id) ||
        (requestedBranchIds && !requestedBranchIds.has(s.branch_id)) ||
        !request.items.some((i) => i.product_id === s.original_product_id) ||
        !mockCompatible(s.original_product_id, s.replacement_product_id) ||
        productPrice(s.branch_id, s.replacement_product_id) === undefined) throw new Error('Reemplazo inválido para esta línea y sucursal.')
      seen.add(key)
    }
    const effective = (branch: string, product: string) => substitutions.find((s) => s.branch_id === branch && s.original_product_id === product)?.replacement_product_id ?? product
    const evaluated = branches.filter((branch) => !requestedBranchIds || requestedBranchIds.has(branch.id)).map((branch) => {
      const missing = selected.filter((item) => productPrice(branch.id, effective(branch.id, item.product!.id)) === undefined)
      const total = selected.reduce((sum, item) => {
        return sum + (productPrice(branch.id, effective(branch.id, item.product!.id)) ?? 0) * item.quantity
      }, 0)
      const details = substitutions.filter((s) => s.branch_id === branch.id).map((s) => mockCandidate(branch.id, s.original_product_id,
        catalog.find((p) => p.id === s.replacement_product_id)!, request.items.find((i) => i.product_id === s.original_product_id)!.quantity))
      return { branch, total, distance: distances[city.id][branch.id], missing, details }
    })
    const complete = evaluated.filter((c) => !c.missing.length)
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
        basket_type: candidate.details.length ? 'substituted' as const : 'original' as const,
        substitutions: candidate.details,
        posicion: index + 1,
        sucursal: candidate.branch,
        total: candidate.total.toFixed(2),
        distancia_km: candidate.distance.toFixed(2),
        ahorro: saving.toFixed(2),
        puntaje: score.toFixed(4),
      }))
    return {
      origen: {
        id: request.origin_latitude === undefined ? city.id : null,
        nombre: request.origin_latitude === undefined ? city.nombre : 'Tu ubicación',
        latitud: request.origin_latitude ?? city.latitud ?? 0,
        longitud: request.origin_longitude ?? city.longitud ?? 0,
        fuente: request.origin_latitude === undefined ? 'city' : 'user',
      },
      pesos: { precio: String(request.weights.price), distancia: String(request.weights.distance), ahorro: String(request.weights.saving) },
      fecha_relevamiento: observedAt,
      ranking,
      incomplete: evaluated.filter((c) => c.missing.length)
        .sort((a, b) => a.missing.length - b.missing.length || a.distance - b.distance)
        .map((c) => ({ sucursal: c.branch, distance_km: String(c.distance),
          covered_products_count: selected.length - c.missing.length, total_products_count: selected.length,
          substitutions: c.details,
          productos_faltantes: c.missing.map((i) => ({ id: i.product!.id, nombre: i.product!.nombre, motivo: 'missing' as const })),
        })),
      calidad: {
        fecha_evaluacion: observedAt,
        antiguedad_maxima_dias: 14,
        precios_aptos: selected.length * branches.length,
        precios_vencidos: 0,
        precios_sospechosos: 0,
      },
    }
  },
}

export const mockSeed = { products: mockProducts, cities, branches, supermarkets, substitutionProduct }
