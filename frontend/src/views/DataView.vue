<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  Activity,
  ArrowLeft,
  Boxes,
  Database,
  LoaderCircle,
  MapPinned,
  PackageSearch,
  RefreshCw,
  Search,
  Store,
  Tag,
} from 'lucide-vue-next'

import DashboardHeader from '@/components/DashboardHeader.vue'
import { formatCurrency, formatDate } from '@/lib/format'
import { api, apiMode } from '@/services/api'
import type { Branch, City, CurrentPrice, Product, Supermarket } from '@/types'

type Tab = 'catalog' | 'branches' | 'prices'

const activeTab = ref<Tab>('catalog')
const products = ref<Product[]>([])
const cities = ref<City[]>([])
const supermarkets = ref<Supermarket[]>([])
const branches = ref<Branch[]>([])
const prices = ref<CurrentPrice[]>([])
const status = ref<'loading' | 'online' | 'error'>('loading')
const error = ref('')
const search = ref('')
const cityFilter = ref('')
const supermarketFilter = ref('')

const visibleProducts = computed(() => {
  const term = search.value.trim().toLocaleLowerCase('es')
  return products.value.filter((product) => !term || [product.nombre, product.marca, product.categoria].filter(Boolean).join(' ').toLocaleLowerCase('es').includes(term))
})

const visiblePrices = computed(() => {
  const term = search.value.trim().toLocaleLowerCase('es')
  return prices.value.filter((price) => !term || `${price.producto} ${price.supermercado} ${price.sucursal}`.toLocaleLowerCase('es').includes(term))
})

const loadData = async () => {
  status.value = 'loading'
  error.value = ''
  try {
    const [health, productResponse, cityResponse, supermarketResponse, branchResponse, priceResponse] = await Promise.all([
      api.health(),
      api.products(),
      api.cities(),
      api.supermarkets(),
      api.branches(cityFilter.value || undefined, supermarketFilter.value || undefined),
      api.currentPrices({ cityId: cityFilter.value || undefined, supermarketId: supermarketFilter.value || undefined }),
    ])
    products.value = productResponse.items
    cities.value = cityResponse.items
    supermarkets.value = supermarketResponse.items
    branches.value = branchResponse.items
    prices.value = priceResponse.items
    status.value = health.status === 'ok' ? 'online' : 'error'
  } catch (reason) {
    status.value = 'error'
    error.value = reason instanceof Error ? reason.message : 'No se pudieron consultar los datos.'
  }
}

watch([cityFilter, supermarketFilter], loadData)
onMounted(loadData)
</script>

<template>
  <main class="page-shell">
    <DashboardHeader />
    <div class="mx-auto max-w-7xl px-4 pb-16 pt-6 sm:px-6 lg:px-8">
      <RouterLink to="/" class="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 transition hover:text-slate-950"><ArrowLeft class="size-4" /> Volver al inicio</RouterLink>
      <div class="mt-5 flex flex-col justify-between gap-5 lg:flex-row lg:items-end"><div><span class="section-kicker"><Database class="size-3.5" /> Explorador de datos</span><h1 class="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">Datos de prueba disponibles.</h1><p class="mt-3 max-w-2xl leading-7 text-slate-500">Consultá el catálogo, las sucursales y los precios sin modificar el conjunto de datos.</p></div><div class="flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm" :class="status === 'online' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : status === 'error' ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-sky-200 bg-sky-50 text-sky-800'"><Activity class="size-4" :class="status === 'loading' ? 'animate-pulse' : ''" /><span><strong>{{ status === 'online' ? 'Conectado' : status === 'error' ? 'Sin conexión' : 'Consultando' }}</strong> · {{ apiMode === 'mock' ? 'datos de prueba' : 'backend local' }}</span></div></div>

      <div class="mt-8 rounded-3xl border border-white/70 bg-white/65 p-4 shadow-glass backdrop-blur-xl sm:p-6"><div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"><div class="flex flex-wrap gap-2" role="tablist" aria-label="Conjuntos de datos"><button v-for="tab in [{ id: 'catalog', label: 'Catálogo', icon: PackageSearch }, { id: 'branches', label: 'Sucursales', icon: Store }, { id: 'prices', label: 'Precios', icon: Tag }]" :key="tab.id" type="button" role="tab" :aria-selected="activeTab === tab.id" class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition" :class="activeTab === tab.id ? 'bg-slate-950 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" @click="activeTab = tab.id as Tab"><component :is="tab.icon" class="size-4" />{{ tab.label }}</button></div><button type="button" class="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50" :disabled="status === 'loading'" @click="loadData"><RefreshCw class="size-4" :class="status === 'loading' ? 'animate-spin' : ''" />Actualizar</button></div>

        <div class="mt-5 grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_12rem_12rem]"><label class="relative"><span class="sr-only">Buscar en los datos</span><Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><input v-model="search" type="search" placeholder="Buscar en la vista actual" class="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm outline-none transition focus:border-sky-400" /></label><select v-model="cityFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700"><option value="">Todas las ciudades</option><option v-for="city in cities" :key="city.id" :value="city.id">{{ city.nombre }}</option></select><select v-model="supermarketFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700"><option value="">Todos los supermercados</option><option v-for="supermarket in supermarkets" :key="supermarket.id" :value="supermarket.id">{{ supermarket.nombre }}</option></select></div>
      </div>

      <p v-if="error" class="mt-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">{{ error }}</p>
      <div v-else-if="status === 'loading'" class="mt-5 grid place-items-center rounded-3xl border border-white bg-white/70 py-24 text-slate-500"><LoaderCircle class="size-6 animate-spin" /><p class="mt-3 text-sm">Consultando la fuente de datos…</p></div>

      <section v-else class="mt-5 overflow-hidden rounded-3xl border border-slate-100 bg-white shadow-sm">
        <div class="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h2 class="font-semibold">{{ activeTab === 'catalog' ? 'Productos normalizados' : activeTab === 'branches' ? 'Sucursales activas' : 'Precios vigentes' }}</h2><p class="mt-1 text-sm text-slate-500">{{ activeTab === 'catalog' ? `${visibleProducts.length} registros en el catálogo` : activeTab === 'branches' ? `${branches.length} sucursales según los filtros` : `${visiblePrices.length} precios vigentes` }}</p></div><Boxes class="size-5 text-sky-700" /></div>

        <div v-if="activeTab === 'catalog'" class="overflow-x-auto"><table class="min-w-full text-left text-sm"><thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th class="px-5 py-3 font-semibold">Producto</th><th class="px-5 py-3 font-semibold">Marca</th><th class="px-5 py-3 font-semibold">Categoría</th><th class="px-5 py-3 font-semibold">Presentación</th><th class="px-5 py-3 font-semibold">Código</th></tr></thead><tbody class="divide-y divide-slate-100"><tr v-for="product in visibleProducts" :key="product.id" class="hover:bg-slate-50/70"><td class="px-5 py-4 font-medium text-slate-800">{{ product.nombre }}</td><td class="px-5 py-4 text-slate-600">{{ product.marca ?? '—' }}</td><td class="px-5 py-4 text-slate-600">{{ product.categoria ?? '—' }}</td><td class="px-5 py-4 text-slate-600">{{ product.contenido_neto }} {{ product.unidad_medida }}</td><td class="px-5 py-4 font-mono text-xs text-slate-500">{{ product.codigo_interno }}</td></tr><tr v-if="!visibleProducts.length"><td colspan="5" class="px-5 py-12 text-center text-slate-500">No hay productos para mostrar.</td></tr></tbody></table></div>

        <div v-else-if="activeTab === 'branches'" class="overflow-x-auto"><table class="min-w-full text-left text-sm"><thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th class="px-5 py-3 font-semibold">Supermercado</th><th class="px-5 py-3 font-semibold">Sucursal</th><th class="px-5 py-3 font-semibold">Ciudad</th><th class="px-5 py-3 font-semibold">Dirección</th><th class="px-5 py-3 font-semibold">Coordenadas</th></tr></thead><tbody class="divide-y divide-slate-100"><tr v-for="branch in branches" :key="branch.id" class="hover:bg-slate-50/70"><td class="px-5 py-4 font-medium text-slate-800">{{ branch.supermercado }}</td><td class="px-5 py-4 text-slate-600">{{ branch.nombre }}</td><td class="px-5 py-4 text-slate-600">{{ branch.ciudad }}</td><td class="px-5 py-4 text-slate-600">{{ branch.direccion }}</td><td class="px-5 py-4 font-mono text-xs text-slate-500">{{ branch.latitud }}, {{ branch.longitud }}</td></tr><tr v-if="!branches.length"><td colspan="5" class="px-5 py-12 text-center text-slate-500">No hay sucursales con estos filtros.</td></tr></tbody></table></div>

        <div v-else class="overflow-x-auto"><table class="min-w-full text-left text-sm"><thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th class="px-5 py-3 font-semibold">Producto</th><th class="px-5 py-3 font-semibold">Supermercado</th><th class="px-5 py-3 font-semibold">Sucursal</th><th class="px-5 py-3 font-semibold">Precio</th><th class="px-5 py-3 font-semibold">Relevamiento</th><th class="px-5 py-3 font-semibold">Estado</th></tr></thead><tbody class="divide-y divide-slate-100"><tr v-for="price in visiblePrices" :key="price.id" class="hover:bg-slate-50/70"><td class="px-5 py-4"><p class="font-medium text-slate-800">{{ price.producto }}</p><p class="mt-1 text-xs text-slate-500">{{ price.producto_fuente }}</p></td><td class="px-5 py-4 text-slate-600">{{ price.supermercado }}</td><td class="px-5 py-4 text-slate-600"><p>{{ price.sucursal }}</p><p class="mt-1 text-xs text-slate-400">{{ price.ciudad }}</p></td><td class="px-5 py-4 font-semibold text-slate-800">{{ formatCurrency(price.precio) }}</td><td class="px-5 py-4 text-slate-600">{{ formatDate(price.fecha_relevamiento) }}</td><td class="px-5 py-4"><span class="rounded-full px-2.5 py-1 text-xs font-semibold" :class="price.disponible ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'">{{ price.disponible ? 'Disponible' : 'No disponible' }}</span></td></tr><tr v-if="!visiblePrices.length"><td colspan="6" class="px-5 py-12 text-center text-slate-500">No hay precios con estos filtros.</td></tr></tbody></table></div>
      </section>
    </div>
  </main>
</template>
