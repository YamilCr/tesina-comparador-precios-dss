<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  BarChart3,
  Check,
  ChevronDown,
  LoaderCircle,
  LocateFixed,
  MapPin,
  Minus,
  PackagePlus,
  RefreshCw,
  RotateCcw,
  Search,
  ShoppingBasket,
  SlidersHorizontal,
  Trash2,
  Trophy,
} from 'lucide-vue-next'

import DashboardHeader from '@/components/DashboardHeader.vue'
import RankingMap from '@/components/RankingMap.vue'
import { formatCurrency, formatDate, formatNumber } from '@/lib/format'
import { api } from '@/services/api'
import { useComparisonStore } from '@/stores/comparison'
import type {
  City,
  CurrentPrice,
  LiveRefreshResponse,
  Product,
  RankingResponse,
  ScrapingSource,
} from '@/types'

const store = useComparisonStore()
const cities = ref<City[]>([])
const products = ref<Product[]>([])
const productQuery = ref('')
const ranking = ref<RankingResponse | null>(null)
const sources = ref<ScrapingSource[]>([])
const selectedSourceIds = ref<string[]>([])
const currentPrices = ref<CurrentPrice[]>([])
const refreshResult = ref<LiveRefreshResponse | null>(null)
const loading = ref(true)
const calculating = ref(false)
const refreshing = ref(false)
const loadingPrices = ref(false)
const error = ref('')
const liveError = ref('')
const locating = ref(false)
const locationError = ref('')
const userLocation = ref<{ latitude: number; longitude: number; accuracy: number } | null>(null)

const filteredProducts = computed(() => {
  const term = productQuery.value.trim().toLocaleLowerCase('es')
  if (!term) return products.value
  return products.value.filter((product) => product.nombre.toLocaleLowerCase('es').includes(term))
})

const selectedCity = computed(() => cities.value.find((city) => city.id === store.cityId))
const isInBasket = (productId: string) => store.items.some((item) => item.product.id === productId)
const activeSources = computed(() => sources.value.filter((source) => source.active && source.branchId))
const originDescription = computed(() => {
  if (userLocation.value) return `Ubicación actual · precisión aproximada ${Math.round(userLocation.value.accuracy)} m`
  return `Centro de ${selectedCity.value?.nombre ?? 'la ciudad seleccionada'}`
})
const refreshTotals = computed(() => {
  const results = refreshResult.value?.results ?? []
  return {
    loaded: results.reduce((total, result) => total + result.loaded, 0),
    failed: results.filter((result) => result.errorMessage || result.status !== 'succeeded').length,
  }
})

const missingReasonLabel = (reason: 'missing' | 'stale' | 'suspect') => {
  if (reason === 'stale') return 'precio vencido'
  if (reason === 'suspect') return 'precio anómalo'
  return 'sin precio'
}

const ensureWeightLimit = (changed: 'price' | 'distance') => {
  if (store.priceWeight + store.distanceWeight <= 100) return
  if (changed === 'price') store.distanceWeight = Math.max(0, 100 - store.priceWeight)
  else store.priceWeight = Math.max(0, 100 - store.distanceWeight)
}

const addProduct = (product: Product) => {
  store.addProduct(product)
  ranking.value = null
}

const useCurrentLocation = () => {
  locationError.value = ''
  if (!navigator.geolocation) {
    locationError.value = 'Este navegador no permite obtener tu ubicación.'
    return
  }

  locating.value = true
  navigator.geolocation.getCurrentPosition(
    (position) => {
      userLocation.value = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      }
      ranking.value = null
      locating.value = false
    },
    (reason) => {
      locationError.value =
        reason.code === reason.PERMISSION_DENIED
          ? 'No se concedió permiso de ubicación. Podés seguir usando el centro de la ciudad.'
          : 'No pudimos determinar tu ubicación. Podés seguir usando el centro de la ciudad.'
      locating.value = false
    },
    { enableHighAccuracy: true, timeout: 10_000, maximumAge: 300_000 },
  )
}

const useCityCenter = () => {
  userLocation.value = null
  locationError.value = ''
  ranking.value = null
}

const loadBasketPrices = async () => {
  if (!store.cityId || !store.items.length) {
    currentPrices.value = []
    return
  }
  loadingPrices.value = true
  try {
    const responses = await Promise.all(
      store.items.map((item) =>
        api.currentPrices({ productId: item.product.id, cityId: store.cityId }),
      ),
    )
    currentPrices.value = Array.from(
      new Map(responses.flatMap((response) => response.items).map((price) => [price.id, price])).values(),
    )
  } catch (reason) {
    liveError.value = reason instanceof Error ? reason.message : 'No se pudieron consultar los precios.'
  } finally {
    loadingPrices.value = false
  }
}

const runLiveRefresh = async () => {
  const query = productQuery.value.trim()
  if (!query || !selectedCity.value || !selectedSourceIds.value.length) return
  refreshing.value = true
  liveError.value = ''
  refreshResult.value = null
  try {
    refreshResult.value = await api.refreshPrices({
      source_ids: selectedSourceIds.value,
      queries: [query],
      city: selectedCity.value.nombre,
      limit: 5,
      max_concurrency: Math.min(2, selectedSourceIds.value.length),
      timeout_seconds: 60,
    })
    products.value = (await api.products(query)).items
    await loadBasketPrices()
  } catch (reason) {
    liveError.value = reason instanceof Error ? reason.message : 'No se pudo actualizar la búsqueda.'
  } finally {
    refreshing.value = false
  }
}

const runRanking = async () => {
  if (!store.cityId || !store.items.length || !store.hasValidWeights) return
  calculating.value = true
  error.value = ''
  try {
    const branchResponse = await api.branches(store.cityId)
    const verifiedBranches = branchResponse.items.filter((branch) => branch.coordenadas_verificadas)
    if (!verifiedBranches.length) {
      throw new Error('No hay sucursales con coordenadas verificadas para esta ciudad.')
    }
    ranking.value = await api.ranking({
      city_id: store.cityId,
      branch_ids: verifiedBranches.map((branch) => branch.id),
      ...(userLocation.value
        ? {
            origin_latitude: userLocation.value.latitude,
            origin_longitude: userLocation.value.longitude,
          }
        : {}),
      items: store.items.map((item) => ({ product_id: item.product.id, quantity: String(item.quantity) })),
      weights: {
        price: store.priceWeight / 100,
        distance: store.distanceWeight / 100,
        saving: store.savingWeight / 100,
      },
    })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'No se pudo calcular el ranking.'
  } finally {
    calculating.value = false
  }
}

const initialize = async () => {
  loading.value = true
  error.value = ''
  try {
    const [cityResponse, productResponse, sourceResponse] = await Promise.all([
      api.cities(),
      api.products(),
      api.scrapingSources(),
    ])
    cities.value = cityResponse.items
    products.value = productResponse.items
    sources.value = sourceResponse.items
    selectedSourceIds.value = sourceResponse.items
      .filter((source) => source.active && source.branchId)
      .map((source) => source.id)
    if (!store.cityId && cities.value[0]) store.cityId = cities.value[0].id
    await loadBasketPrices()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'No se pudieron cargar los datos iniciales.'
  } finally {
    loading.value = false
  }
}

watch([() => store.cityId, () => store.items], () => { ranking.value = null }, { deep: true })
watch([() => store.cityId, () => store.items], loadBasketPrices, { deep: true })
onMounted(initialize)
</script>

<template>
  <main class="page-shell">
    <DashboardHeader />
    <div class="mx-auto max-w-7xl px-4 pb-16 pt-6 sm:px-6 lg:px-8">
      <RouterLink to="/" class="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 transition hover:text-slate-950"><ArrowLeft class="size-4" /> Volver al inicio</RouterLink>
      <div class="mt-5 flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><span class="section-kicker"><BarChart3 class="size-3.5" /> Comparador DSS</span><h1 class="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">Encontrá la alternativa más conveniente para tu canasta.</h1><p class="mt-3 max-w-2xl leading-7 text-slate-500">Sumá productos, elegí una ciudad y ajustá qué criterio importa más para tu compra.</p></div><div class="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800"><span class="font-bold">{{ store.totalProducts }}</span> productos en la canasta</div></div>

      <div v-if="error && !loading" class="mt-8 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">{{ error }}</div>
      <div v-else-if="loading" class="mt-8 grid place-items-center rounded-3xl border border-white bg-white/70 py-24 text-slate-500"><LoaderCircle class="size-6 animate-spin" aria-hidden="true" /><p class="mt-3 text-sm">Preparando los datos de comparación…</p></div>

      <template v-else>
        <div class="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <section class="space-y-6">
            <article class="glass-card rounded-3xl p-5 sm:p-6">
              <div class="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
                <div>
                  <label for="city" class="text-sm font-semibold text-slate-800">Zona de comparación</label>
                  <p class="mt-1 text-sm text-slate-500">{{ originDescription }}</p>
                </div>
                <div class="flex flex-col gap-3 sm:flex-row">
                  <div class="relative min-w-64">
                    <MapPin class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-sky-700" />
                    <select id="city" v-model="store.cityId" class="w-full appearance-none rounded-xl border border-slate-200 bg-white px-9 py-3 text-sm font-semibold text-slate-800 shadow-sm">
                      <option v-for="city in cities" :key="city.id" :value="city.id">{{ city.nombre }}, {{ city.provincia }}</option>
                    </select>
                    <ChevronDown class="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
                  </div>
                  <button v-if="!userLocation" type="button" class="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 text-sm font-bold text-sky-900 transition hover:bg-sky-100 disabled:opacity-50" :disabled="locating" @click="useCurrentLocation">
                    <LoaderCircle v-if="locating" class="size-4 animate-spin" />
                    <LocateFixed v-else class="size-4" />
                    {{ locating ? 'Ubicando…' : 'Usar mi ubicación' }}
                  </button>
                  <button v-else type="button" class="grid size-11 shrink-0 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50" title="Volver al centro de la ciudad" aria-label="Volver al centro de la ciudad" @click="useCityCenter">
                    <RotateCcw class="size-4" />
                  </button>
                </div>
              </div>
              <p v-if="locationError" class="mt-3 text-sm text-amber-800" role="alert">{{ locationError }}</p>
            </article>

            <article class="glass-card rounded-3xl p-5 sm:p-6"><div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><h2 class="text-lg font-semibold">Productos de la canasta</h2><p class="mt-1 text-sm text-slate-500">Buscá en el catálogo o actualizá precios desde las fuentes.</p></div><label class="relative block sm:w-72"><span class="sr-only">Buscar producto</span><Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><input v-model="productQuery" type="search" placeholder="Buscar producto" class="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-sky-400" /></label></div>
              <div class="mt-4 flex flex-col gap-3 border-y border-slate-100 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div class="flex flex-wrap gap-x-4 gap-y-2"><label v-for="source in activeSources" :key="source.id" class="inline-flex items-center gap-2 text-xs font-medium text-slate-600"><input v-model="selectedSourceIds" type="checkbox" :value="source.id" class="size-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500" />{{ source.scraperKey === 'la_anonima' ? 'La Anónima' : source.scraperKey === 'coope' ? 'La Coope' : source.scraperKey.charAt(0).toUpperCase() + source.scraperKey.slice(1) }}</label></div>
                <button type="button" class="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 rounded-xl bg-sky-100 px-4 text-sm font-bold text-sky-900 transition hover:bg-sky-200 disabled:cursor-not-allowed disabled:opacity-45" :disabled="!productQuery.trim() || !selectedSourceIds.length || refreshing" @click="runLiveRefresh"><LoaderCircle v-if="refreshing" class="size-4 animate-spin" /><RefreshCw v-else class="size-4" />{{ refreshing ? 'Actualizando…' : 'Actualizar precios' }}</button>
              </div>
              <div v-if="liveError" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">{{ liveError }}</div>
              <div v-if="refreshResult" class="mt-4 rounded-xl border px-4 py-3 text-sm" :class="refreshTotals.failed ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-emerald-200 bg-emerald-50 text-emerald-900'">
                <div class="flex flex-wrap items-center justify-between gap-2"><strong>{{ refreshTotals.loaded }} precios cargados</strong><span>{{ refreshResult.results.length - refreshTotals.failed }}/{{ refreshResult.results.length }} fuentes completadas</span></div>
                <ul class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs"><li v-for="result in refreshResult.results" :key="result.sourceId">{{ result.sourceName }}: {{ result.errorMessage ? 'error' : `${result.loaded} cargados · ${result.durationMs} ms` }}</li></ul>
              </div>
              <div class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2"><article v-for="product in filteredProducts" :key="product.id" class="flex items-start justify-between gap-4 rounded-2xl border border-slate-100 bg-white p-4"><div><p class="font-semibold text-slate-800">{{ product.nombre }}</p><p class="mt-1 text-xs text-slate-500">{{ product.marca ?? 'Sin marca' }} · {{ product.categoria ?? 'Sin categoría' }}</p></div><button type="button" class="grid size-9 shrink-0 place-items-center rounded-xl transition" :class="isInBasket(product.id) ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-900 text-white hover:bg-slate-700'" :aria-label="`Agregar ${product.nombre}`" @click="addProduct(product)"><Check v-if="isInBasket(product.id)" class="size-4" /><PackagePlus v-else class="size-4" /></button></article></div>
              <p v-if="!filteredProducts.length" class="mt-5 text-sm text-slate-500">No encontramos productos para esa búsqueda.</p>
            </article>

            <article v-if="store.items.length" class="glass-card overflow-hidden rounded-3xl"><div class="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6"><div><h2 class="text-lg font-semibold">Precios vigentes</h2><p class="mt-1 text-sm text-slate-500">{{ currentPrices.length }} precios para la canasta en {{ selectedCity?.nombre }}</p></div><LoaderCircle v-if="loadingPrices" class="size-5 animate-spin text-sky-700" /><RefreshCw v-else class="size-5 text-sky-700" /></div>
              <div v-if="currentPrices.length" class="overflow-x-auto"><table class="min-w-full text-left text-sm"><thead class="bg-slate-50 text-xs uppercase text-slate-500"><tr><th class="px-5 py-3 font-semibold sm:px-6">Producto</th><th class="px-5 py-3 font-semibold">Supermercado</th><th class="px-5 py-3 font-semibold">Sucursal</th><th class="px-5 py-3 font-semibold">Vigencia</th><th class="px-5 py-3 text-right font-semibold sm:px-6">Precio</th></tr></thead><tbody class="divide-y divide-slate-100"><tr v-for="price in currentPrices" :key="price.id"><td class="px-5 py-3 font-medium text-slate-800 sm:px-6">{{ price.producto }}</td><td class="px-5 py-3 text-slate-600">{{ price.supermercado }}</td><td class="px-5 py-3 text-slate-600">{{ price.sucursal }}</td><td class="px-5 py-3"><span class="inline-flex rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">{{ price.antiguedad_dias === 0 ? 'Hoy' : `Hace ${price.antiguedad_dias} d` }}</span></td><td class="px-5 py-3 text-right font-bold text-slate-900 sm:px-6">{{ formatCurrency(price.precio) }}</td></tr></tbody></table></div>
              <p v-else-if="!loadingPrices" class="px-5 py-8 text-center text-sm text-slate-500">No hay precios vigentes para los productos seleccionados.</p>
            </article>

            <article class="glass-card rounded-3xl p-5 sm:p-6"><div class="flex items-center justify-between gap-4"><div><h2 class="text-lg font-semibold">Criterios de decisión</h2><p class="mt-1 text-sm text-slate-500">El peso del ahorro se completa automáticamente hasta llegar al 100%.</p></div><SlidersHorizontal class="size-5 text-sky-700" /></div>
              <div class="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3"><label class="block"><span class="flex justify-between text-sm font-medium"><span>Precio</span><span class="text-sky-700">{{ store.priceWeight }}%</span></span><input v-model.number="store.priceWeight" class="range-input mt-3 w-full" type="range" min="0" max="100" step="5" @change="ensureWeightLimit('price')" /></label><label class="block"><span class="flex justify-between text-sm font-medium"><span>Distancia</span><span class="text-sky-700">{{ store.distanceWeight }}%</span></span><input v-model.number="store.distanceWeight" class="range-input mt-3 w-full" type="range" min="0" max="100" step="5" @change="ensureWeightLimit('distance')" /></label><div class="rounded-2xl bg-emerald-50 p-4"><p class="text-sm font-medium text-emerald-800">Ahorro</p><p class="mt-2 text-2xl font-semibold tracking-tight text-emerald-700">{{ store.savingWeight }}%</p><p class="mt-1 text-xs text-emerald-700/80">Peso restante</p></div></div>
            </article>
          </section>

          <aside class="h-fit rounded-3xl bg-slate-950 p-5 text-white shadow-float sm:p-6 lg:sticky lg:top-5"><div class="flex items-center justify-between"><h2 class="font-semibold">Tu canasta</h2><button v-if="store.items.length" type="button" class="text-xs font-semibold text-slate-300 hover:text-white" @click="store.reset">Restablecer</button></div><p class="mt-1 text-sm text-slate-400">{{ selectedCity?.nombre ?? 'Elegí una ciudad' }}</p>
            <div v-if="store.items.length" class="mt-6 divide-y divide-white/10"><div v-for="item in store.items" :key="item.product.id" class="py-4 first:pt-0"><div class="flex items-start justify-between gap-3"><div><p class="text-sm font-medium text-white">{{ item.product.nombre }}</p><p class="mt-1 text-xs text-slate-400">{{ item.product.marca }}</p></div><button type="button" class="text-slate-400 transition hover:text-rose-300" :aria-label="`Quitar ${item.product.nombre}`" @click="store.removeProduct(item.product.id)"><Trash2 class="size-4" /></button></div><div class="mt-3 flex items-center justify-between"><label class="sr-only" :for="`quantity-${item.product.id}`">Cantidad de {{ item.product.nombre }}</label><input :id="`quantity-${item.product.id}`" :value="item.quantity" min="0.1" step="0.1" type="number" class="w-20 rounded-lg border border-white/15 bg-white/10 px-2 py-1.5 text-sm text-white" @input="store.updateQuantity(item.product.id, Number(($event.target as HTMLInputElement).value))" /><span class="text-xs text-slate-400">unidades</span></div></div></div>
            <div v-else class="mt-7 rounded-2xl border border-dashed border-white/20 p-5 text-center"><ShoppingBasket class="mx-auto size-5 text-sky-300" /><p class="mt-3 text-sm text-slate-300">Tu canasta está vacía.</p><p class="mt-1 text-xs leading-5 text-slate-500">Agregá productos desde el catálogo para calcular una recomendación.</p></div>
            <button type="button" class="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-sky-300 px-4 py-3 font-bold text-slate-950 transition hover:bg-sky-200 disabled:cursor-not-allowed disabled:opacity-45" :disabled="!store.items.length || !store.cityId || calculating || !store.hasValidWeights" @click="runRanking"><LoaderCircle v-if="calculating" class="size-4 animate-spin" /><Trophy v-else class="size-4" />{{ calculating ? 'Calculando…' : 'Calcular ranking' }}</button>
          </aside>
        </div>

        <section class="mt-8" aria-live="polite"><div class="flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><span class="section-kicker"><Trophy class="size-3.5" /> Resultado</span><h2 class="mt-3 text-2xl font-semibold tracking-tight">{{ ranking ? 'Ranking de alternativas' : 'Esperando una canasta' }}</h2><p class="mt-2 text-sm text-slate-500">{{ ranking ? `Calculado desde ${ranking.origen.nombre} · Relevamiento ${formatDate(ranking.fecha_relevamiento)}` : 'Cuando estés listo, calculá el ranking para ver la comparación.' }}</p></div><span v-if="ranking" class="text-sm font-medium text-slate-500">{{ ranking.ranking.length }} alternativas completas</span></div>
          <div v-if="ranking" class="mt-4 flex flex-wrap gap-2 text-xs font-semibold"><span class="rounded-full bg-emerald-50 px-3 py-1.5 text-emerald-700">{{ ranking.calidad.precios_aptos }} precios aptos</span><span v-if="ranking.calidad.precios_vencidos" class="rounded-full bg-amber-50 px-3 py-1.5 text-amber-800">{{ ranking.calidad.precios_vencidos }} vencidos</span><span v-if="ranking.calidad.precios_sospechosos" class="rounded-full bg-rose-50 px-3 py-1.5 text-rose-700">{{ ranking.calidad.precios_sospechosos }} anómalos</span></div>
          <div v-if="ranking" class="mt-6">
            <RankingMap :origin="ranking.origen" :ranking="ranking.ranking" :incomplete="ranking.incomplete" />
            <div class="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs font-medium text-slate-600">
              <span class="inline-flex items-center gap-2"><i class="size-2.5 rounded-full bg-sky-400 ring-2 ring-slate-900" />Origen</span>
              <span class="inline-flex items-center gap-2"><i class="size-2.5 rounded-full bg-emerald-400 ring-2 ring-emerald-700" />Recomendada</span>
              <span class="inline-flex items-center gap-2"><i class="size-2.5 rounded-full bg-sky-400 ring-2 ring-sky-700" />Alternativa</span>
              <span class="inline-flex items-center gap-2"><i class="size-2.5 rounded-full bg-amber-400 ring-2 ring-amber-700" />Canasta incompleta</span>
              <span class="inline-flex items-center gap-1.5 text-emerald-700"><BadgeCheck class="size-3.5" />Coordenadas verificadas</span>
            </div>
          </div>
          <div v-if="ranking" class="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2"><article v-for="result in ranking.ranking" :key="result.sucursal.id" class="rounded-3xl border p-5 shadow-sm" :class="result.posicion === 1 ? 'border-emerald-200 bg-emerald-50/60' : 'border-slate-100 bg-white'"><div class="flex items-start justify-between gap-4"><div class="flex gap-3"><span class="grid size-9 shrink-0 place-items-center rounded-xl font-bold" :class="result.posicion === 1 ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600'">{{ result.posicion }}</span><div><p class="font-semibold">{{ result.sucursal.supermercado }}</p><p class="mt-1 text-sm text-slate-500">{{ result.sucursal.nombre }} · {{ result.sucursal.ciudad }}</p></div></div><span v-if="result.posicion === 1" class="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-1 text-xs font-bold text-emerald-700"><BadgeCheck class="size-3" /> Recomendada</span></div><div class="mt-5 grid grid-cols-3 gap-2 text-center"><div class="rounded-xl bg-white/75 p-3"><p class="text-xs text-slate-400">Total</p><p class="mt-1 text-sm font-bold">{{ formatCurrency(result.total) }}</p></div><div class="rounded-xl bg-white/75 p-3"><p class="text-xs text-slate-400">Distancia</p><p class="mt-1 text-sm font-bold">{{ formatNumber(result.distancia_km) }} km</p></div><div class="rounded-xl bg-white/75 p-3"><p class="text-xs text-slate-400">Ahorro</p><p class="mt-1 text-sm font-bold text-emerald-700">{{ formatCurrency(result.ahorro) }}</p></div></div><div class="mt-4"><div class="flex justify-between text-xs font-medium text-slate-500"><span>Puntaje DSS</span><span>{{ Math.round(Number(result.puntaje) * 100) }}%</span></div><div class="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div class="h-full rounded-full bg-sky-500 transition-all" :style="{ width: `${Math.max(Number(result.puntaje) * 100, 4)}%` }" /></div></div></article></div>
          <div v-else class="mt-6 rounded-3xl border border-dashed border-slate-200 bg-white/50 p-10 text-center"><Trophy class="mx-auto size-6 text-sky-700" /><p class="mt-3 font-semibold text-slate-700">Todavía no hay resultados.</p><p class="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">Agregá al menos un producto y usá el botón “Calcular ranking”.</p></div>
          <div v-if="ranking?.incomplete.length" class="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-5"><p class="font-semibold text-amber-950">Sucursales sin cobertura completa</p><p class="mt-1 text-sm text-amber-800">No se incluyen en el ranking porque la canasta no tiene precios aptos para todos sus productos.</p><ul class="mt-3 space-y-2 text-sm text-amber-900"><li v-for="branch in ranking.incomplete" :key="branch.sucursal.id"><strong>{{ branch.sucursal.supermercado }} {{ branch.sucursal.nombre }}:</strong> {{ branch.productos_faltantes.map((item) => `${item.nombre} (${missingReasonLabel(item.motivo)})`).join(', ') }}</li></ul></div>
        </section>
      </template>
    </div>
  </main>
</template>
