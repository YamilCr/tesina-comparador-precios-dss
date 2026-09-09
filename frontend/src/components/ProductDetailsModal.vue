<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { LoaderCircle, ShoppingBasket, X } from 'lucide-vue-next'
import ProductImage from '@/components/ProductImage.vue'
import { api } from '@/services/api'
import { formatCurrency, formatDate } from '@/lib/format'
import { useComparisonStore } from '@/stores/comparison'
import type { CurrentPrice, Product } from '@/types'

const props = defineProps<{ product: Product; cityId?: string }>()
const emit = defineEmits<{ close: [] }>()
const store = useComparisonStore()
const dialog = ref<HTMLDialogElement | null>(null)
const quantity = ref<number | string>(1)
const prices = ref<CurrentPrice[]>([])
const loading = ref(false)
const error = ref('')
const validQuantity = computed(() => Number.isFinite(Number(quantity.value)) && Number(quantity.value) >= 0.1)
let requestId = 0
let previousOverflow = ''
let opener: HTMLElement | null = null

watch(() => [props.product.id, props.cityId], async () => {
  const current = ++requestId
  prices.value = []
  error.value = ''
  loading.value = true
  try {
    const response = await api.currentPrices({ productId: props.product.id, cityId: props.cityId || undefined })
    if (current === requestId) prices.value = response.items
  } catch {
    if (current === requestId) error.value = 'No se pudieron consultar los precios. Podés volver a abrir el producto para reintentar.'
  } finally {
    if (current === requestId) loading.value = false
  }
}, { immediate: true })

const addToBasket = () => {
  if (!validQuantity.value) return
  const previous = store.items.find(item => item.product.id === props.product.id)?.quantity ?? 0
  store.addProduct(props.product)
  store.updateQuantity(props.product.id, previous + Number(quantity.value))
  dialog.value?.close()
}

onMounted(() => {
  opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  dialog.value?.showModal()
})
onBeforeUnmount(() => {
  ++requestId
  dialog.value?.close()
  document.body.style.overflow = previousOverflow
  opener?.focus()
})
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" aria-labelledby="product-details-title"
      class="m-auto max-h-[94dvh] w-[calc(100%-1rem)] max-w-3xl overflow-y-auto rounded-lg bg-white p-0 text-slate-900 shadow-xl backdrop:bg-black/50"
      @close="emit('close')" @click="event => { if (event.target === dialog) dialog?.close() }">
      <div class="p-5 sm:p-6">
        <header class="mb-5 flex items-start justify-between gap-4">
          <h2 id="product-details-title" class="min-w-0 break-words text-xl font-semibold">{{ product.nombre }}</h2>
          <button type="button" autofocus aria-label="Cerrar detalles" title="Cerrar detalles" class="grid size-9 shrink-0 place-items-center rounded-lg hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-600" @click="dialog?.close()"><X class="size-5" /></button>
        </header>
        <div class="grid gap-6 sm:grid-cols-2">
          <ProductImage :src="product.image_url" :name="product.nombre" large />
          <div class="min-w-0">
            <dl class="grid grid-cols-2 gap-x-4 gap-y-3 break-words text-sm">
              <dt class="text-slate-500">Marca</dt><dd>{{ product.marca || 'Sin informar' }}</dd>
              <dt class="text-slate-500">Categoría</dt><dd>{{ product.categoria || 'Sin informar' }}</dd>
              <dt class="text-slate-500">Presentación</dt><dd>{{ [product.contenido_neto, product.unidad_medida].filter(Boolean).join(' ') || 'Sin informar' }}</dd>
              <template v-if="product.codigo_interno"><dt class="text-slate-500">Código</dt><dd>{{ product.codigo_interno }}</dd></template>
            </dl>
            <form class="mt-6 flex flex-wrap items-end gap-3" @submit.prevent="addToBasket">
              <label class="text-sm font-medium">Cantidad<input v-model="quantity" required type="number" min="0.1" step="0.1" class="mt-2 block w-24 rounded-lg border border-slate-300 px-3 py-2" /></label>
              <button type="submit" :disabled="!validQuantity" class="flex min-h-10 items-center justify-center gap-2 rounded-lg bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50"><ShoppingBasket class="size-4 shrink-0" />Agregar a la canasta</button>
            </form>
          </div>
        </div>
        <section class="mt-6 border-t border-slate-200 pt-5" aria-labelledby="product-prices-title">
          <h3 id="product-prices-title" class="font-semibold">Precios por supermercado</h3>
          <p class="mt-1 text-xs text-slate-500">{{ cityId ? 'En la ciudad seleccionada' : 'Todas las ciudades' }} · Relevados en las sucursales indicadas</p>
          <p v-if="loading" role="status" class="mt-4 flex items-center gap-2 text-sm text-slate-500"><LoaderCircle class="size-4 animate-spin" />Consultando precios...</p>
          <p v-else-if="error" role="alert" class="mt-4 text-sm text-red-700">{{ error }}</p>
          <p v-else-if="!prices.length" class="mt-4 text-sm text-slate-500">No hay precios disponibles para este producto{{ cityId ? ' en esta ciudad' : '' }}.</p>
          <ul v-else class="mt-3 divide-y divide-slate-100">
            <li v-for="price in prices" :key="price.id" class="flex flex-wrap items-start justify-between gap-3 py-3 text-sm">
              <div class="min-w-0 flex-1 break-words"><p class="font-medium">{{ price.supermercado }}</p><p class="text-slate-600">{{ price.sucursal }} · {{ price.ciudad }}</p><p class="text-xs text-slate-500">{{ price.direccion }}</p><p class="mt-1 text-xs text-slate-500">Actualizado: {{ formatDate(price.fecha_relevamiento) }}</p></div>
              <div class="text-right"><p class="font-semibold">{{ formatCurrency(price.precio) }}</p><p v-if="!price.disponible" class="text-xs text-amber-700">No disponible</p><p v-if="price.promocion" class="text-xs text-emerald-700">Promoción</p><p v-if="price.calidad !== 'fresh'" class="text-xs text-amber-700">{{ price.calidad === 'stale' ? 'Precio vencido' : 'Precio a verificar' }}</p></div>
            </li>
          </ul>
        </section>
      </div>
    </dialog>
  </Teleport>
</template>
