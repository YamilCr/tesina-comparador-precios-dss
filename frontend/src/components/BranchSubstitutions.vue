<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Check, ChevronDown, Clock3, LoaderCircle, RotateCcw, Search } from 'lucide-vue-next'
import ProductImage from '@/components/ProductImage.vue'
import { formatCurrency, formatDate, formatNumber } from '@/lib/format'
import { substitutionEmptyMessage } from '@/lib/substitutionMessages'
import type { IncompleteBranch, SubstitutionSelection, SuggestionsResponse } from '@/types'

const props = defineProps<{
  branches: IncompleteBranch[]
  selections: SubstitutionSelection[]
  suggestions: Record<string, SuggestionsResponse>
  errors: Record<string, string>
  pending: Record<string, boolean>
  busy: boolean
  dirty: boolean
}>()
const emit = defineEmits<{
  search: [branchId: string]
  select: [branchId: string, originalId: string, replacementId: string | null]
  restore: [branchId: string]
  apply: []
}>()
const showAll = ref(false)
const requestedBranch = ref<string | null>(null)
const searchAlternatives = (branchId: string) => {
  requestedBranch.value = branchId
  emit('search', branchId)
}
watch(() => props.pending[requestedBranch.value ?? ''], async (pending, previous) => {
  if (pending || !previous || !requestedBranch.value) return
  await nextTick()
  const target = document.getElementById(`alternatives-${requestedBranch.value}`)
  target?.focus({ preventScroll: true })
  target?.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
})
const selectedCount = (branchId: string) => props.selections.filter((item) => item.branch_id === branchId).length
const ordered = computed(() => props.branches.filter((b) => !b.accepted_substitutions).sort((a, b) =>
  a.productos_faltantes.length - b.productos_faltantes.length || Number(a.distance_km ?? 0) - Number(b.distance_km ?? 0)))
const visible = computed(() => [...(showAll.value ? ordered.value : ordered.value.slice(0, 3)), ...props.branches.filter((b) => b.accepted_substitutions)])
const selected = (branch: string, original: string) => props.selections.find((s) => s.branch_id === branch && s.original_product_id === original)?.replacement_product_id
const reason = (value: string) => value === 'stale' ? 'Precio vencido' : value === 'suspect' ? 'Precio anómalo' : 'Sin precio apto'
const unpricedLabel = (status: string) => status === 'suspect' ? 'Precio pendiente de verificación' : 'Precio no actualizado'
</script>

<template>
  <section v-if="branches.length" class="mt-8 border-t border-amber-200 pt-6" aria-label="Alternativas por supermercado">
    <h3 class="text-xl font-semibold">Completá tu canasta con productos similares</h3>
    <p class="mt-2 text-sm text-slate-600">Si un supermercado no tiene precio para algún producto, podés elegir un reemplazo solo para esa compra. Tu lista original se conserva.</p>
    <ol class="my-5 grid gap-3 text-sm sm:grid-cols-3" aria-label="Cómo elegir alternativas">
      <li class="rounded-xl bg-sky-50 p-3"><strong class="block text-sky-900">1. Buscá opciones</strong><span>Elegí el supermercado que querés completar.</span></li>
      <li class="rounded-xl bg-sky-50 p-3"><strong class="block text-sky-900">2. Elegí un reemplazo</strong><span>Compará presentación y precio. Podés cambiar tu elección.</span></li>
      <li class="rounded-xl bg-sky-50 p-3"><strong class="block text-sky-900">3. Confirmá y compará</strong><span>Actualizá los resultados con los productos elegidos.</span></li>
    </ol>
    <p class="mt-1 text-sm text-slate-600">Disponibilidad publicada o inferida; stock físico no confirmado.</p>
    <article v-for="branch in visible" :key="branch.sucursal.id" class="mt-4 rounded-lg border border-amber-200 bg-white p-4 sm:p-5">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0 break-words">
          <h4 class="font-semibold">{{ branch.sucursal.supermercado }}</h4>
          <p class="mt-1 text-sm text-slate-600">Sucursal más cercana: {{ branch.sucursal.nombre }} · {{ formatNumber(branch.distance_km ?? '0') }} km</p>
          <p class="mt-1 text-sm text-slate-600">Última cobertura evaluada: {{ branch.covered_products_count ?? 0 }}/{{ branch.total_products_count ?? branch.productos_faltantes.length }}</p>
          <p class="mt-1 text-sm font-medium text-amber-900">{{ branch.accepted_substitutions ? 'Con sustituciones' : `${branch.productos_faltantes.length} ${branch.productos_faltantes.length === 1 ? 'producto faltante' : 'productos faltantes'}` }}</p>
        </div>
        <button type="button" class="inline-flex min-h-11 items-center gap-2 rounded-xl bg-sky-700 px-4 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50" :aria-label="`Buscar opciones en ${branch.sucursal.supermercado}`" :disabled="busy || pending[branch.sucursal.id]" @click="searchAlternatives(branch.sucursal.id)">
          <LoaderCircle v-if="pending[branch.sucursal.id]" class="size-4 animate-spin" /><Search v-else class="size-4" />{{ pending[branch.sucursal.id] ? 'Buscando opciones…' : suggestions[branch.sucursal.id] ? 'Volver a buscar' : 'Ver productos similares' }}
        </button>
      </div>
      <ul v-if="!branch.accepted_substitutions" class="mt-3 space-y-1 text-sm text-amber-900"><li v-for="item in branch.productos_faltantes" :key="item.id">{{ item.nombre }} · {{ reason(item.motivo) }}</li></ul>
      <p v-if="branch.substitutions?.some((item) => !('unit_price' in item))" class="mt-2 text-sm font-medium text-amber-800">Sustituto elegido sin precio utilizable: esta canasta aún no permite calcular el ahorro.</p>
      <p v-if="pending[branch.sucursal.id]" role="status" class="mt-3 text-sm">Buscando alternativas compatibles...</p>
      <div :id="`alternatives-${branch.sucursal.id}`" tabindex="-1" class="scroll-mt-6 rounded-xl" :aria-label="`Opciones para ${branch.sucursal.supermercado}`">
      <p v-if="errors[branch.sucursal.id]" role="alert" class="mt-3 text-sm text-rose-700">{{ errors[branch.sucursal.id] }} Podés volver a intentar con el botón de búsqueda.</p>
      <template v-if="suggestions[branch.sucursal.id]">
        <p v-if="!suggestions[branch.sucursal.id].items.length" class="mt-4 text-sm">Ya hay precios aptos para los productos originales. Recalculá para actualizar la cobertura.</p>
        <fieldset v-for="group in suggestions[branch.sucursal.id].items" :key="group.original.id" class="mt-5 min-w-0 border-t border-slate-200 pt-3">
          <legend class="max-w-full break-words pr-2 text-sm font-semibold">{{ group.original.normalized_name }} · {{ group.quantity }} {{ Number(group.quantity) === 1 ? 'unidad' : 'unidades' }}</legend>
          <p class="mb-3 text-sm text-slate-600">Elegí qué producto llevarías en su lugar. Revisá el tamaño: se mantiene la cantidad de envases de tu lista.</p>
          <p v-if="!group.candidates.length" class="py-3 text-sm text-slate-600" role="status">{{ substitutionEmptyMessage(group.diagnostics) }}</p>
          <label v-for="candidate in group.candidates" :key="candidate.product.id" class="my-2 flex cursor-pointer items-start gap-3 rounded-xl border-2 p-3 transition focus-within:ring-2 focus-within:ring-sky-500" :class="selected(branch.sucursal.id, group.original.id) === candidate.product.id ? 'border-emerald-600 bg-emerald-50' : 'border-slate-100 hover:border-sky-300'">
            <input type="radio" :name="`sub-${branch.sucursal.id}-${group.original.id}`" :aria-label="`Elegir ${candidate.product.normalized_name}`" :checked="selected(branch.sucursal.id, group.original.id) === candidate.product.id" :disabled="busy" class="mt-4 size-4 shrink-0" @change="emit('select', branch.sucursal.id, group.original.id, candidate.product.id)" />
            <ProductImage :src="candidate.product.image_url" :name="candidate.product.normalized_name" />
            <span class="min-w-0 flex-1 break-words text-sm">
              <strong class="block">{{ candidate.product.normalized_name }}</strong>
              <span v-if="selected(branch.sucursal.id, group.original.id) === candidate.product.id" class="mt-1 inline-flex items-center gap-1 font-semibold text-emerald-800"><Check class="size-4" />Elegido</span>
              <span class="mt-1 block text-slate-600">{{ candidate.product.brand_name ?? 'Sin marca informada' }} · {{ candidate.product.base_quantity ?? candidate.product.net_content }} {{ candidate.product.base_unit ?? candidate.product.unit_measure }}<template v-if="(candidate.product.pack_size ?? 1) > 1"> · Pack × {{ candidate.product.pack_size }}</template></span>
              <span class="mt-1 block">{{ candidate.quantity }} × {{ formatCurrency(candidate.unit_price) }} · Subtotal <strong>{{ formatCurrency(candidate.subtotal) }}</strong></span>
              <span v-if="candidate.price_status === 'stale'" class="mt-1 block font-semibold text-amber-800">Precio no actualizado · cálculo estimado</span>
              <span class="mt-1 block text-xs text-slate-500">{{ formatDate(candidate.observed_at) }} · {{ candidate.inferred_from_chain ? 'Referencia de otra sucursal de la cadena' : 'Precio publicado para esta sucursal' }}</span>
              <span class="mt-1 block text-xs text-slate-500">{{ candidate.compatibility_reason }}</span>
            </span>
          </label>
          <details v-if="group.unpriced_candidates?.length" class="mt-3 rounded-xl border border-amber-200 bg-amber-50/50 p-3">
            <summary class="cursor-pointer py-2 text-sm font-semibold text-amber-900">Otras opciones sin precio utilizable ({{ group.unpriced_candidates.length }})</summary>
            <p class="mt-2 text-sm text-amber-900">Estas opciones no permiten calcular el total ni el ahorro de esta canasta.</p>
          <label v-for="candidate in group.unpriced_candidates ?? []" :key="candidate.product.id" class="my-2 flex cursor-pointer items-start gap-3 rounded-xl border-2 p-3 focus-within:ring-2 focus-within:ring-sky-500" :class="selected(branch.sucursal.id, group.original.id) === candidate.product.id ? 'border-amber-600 bg-amber-100' : 'border-transparent bg-white'">
            <input type="radio" :name="`sub-${branch.sucursal.id}-${group.original.id}`" :aria-label="`Elegir ${candidate.product.normalized_name} sin precio vigente`" :checked="selected(branch.sucursal.id, group.original.id) === candidate.product.id" :disabled="busy" class="mt-4 size-4 shrink-0" @change="emit('select', branch.sucursal.id, group.original.id, candidate.product.id)" />
            <ProductImage :src="candidate.product.image_url" :name="candidate.product.normalized_name" />
            <div class="min-w-0 flex-1 break-words text-sm">
              <strong class="block">{{ candidate.product.normalized_name }}</strong>
              <span v-if="selected(branch.sucursal.id, group.original.id) === candidate.product.id" class="mt-1 block font-semibold text-amber-900">Elegido · sin total calculable</span>
              <span class="mt-1 block text-slate-600">{{ candidate.product.brand_name ?? 'Sin marca informada' }} · {{ candidate.product.base_quantity ?? candidate.product.net_content }} {{ candidate.product.base_unit ?? candidate.product.unit_measure }}<template v-if="(candidate.product.pack_size ?? 1) > 1"> · Pack × {{ candidate.product.pack_size }}</template></span>
              <span class="mt-2 inline-flex items-center gap-1 font-medium text-amber-800"><Clock3 class="size-4" />{{ unpricedLabel(candidate.price_status) }}</span>
              <span class="mt-1 block text-xs text-slate-600">Podés elegirlo, pero no se calculará el ahorro de este supermercado hasta contar con un precio utilizable.</span>
              <span class="mt-1 block text-xs text-slate-500">{{ candidate.compatibility_reason }}</span>
            </div>
          </label>
          </details>
          <button v-if="selected(branch.sucursal.id, group.original.id)" type="button" class="mt-2 inline-flex min-h-10 items-center gap-2 text-sm text-rose-700" :disabled="busy" @click="emit('select', branch.sucursal.id, group.original.id, null)"><RotateCcw class="size-4" />Quitar sustituto</button>
        </fieldset>
      </template>
      </div>
      <p v-if="selectedCount(branch.sucursal.id)" class="mt-4 text-sm font-semibold text-emerald-800" role="status">{{ selectedCount(branch.sucursal.id) }} reemplazo(s) elegido(s) en este supermercado.</p>
      <button v-if="selections.some((s) => s.branch_id === branch.sucursal.id)" type="button" class="mt-4 inline-flex min-h-10 items-center gap-2 text-sm text-slate-600" :disabled="busy" @click="emit('restore', branch.sucursal.id)"><RotateCcw class="size-4" />Restaurar lista original en este supermercado</button>
    </article>
    <div class="sticky bottom-3 z-10 mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-lg">
      <p class="text-sm text-slate-700" role="status">{{ dirty ? 'Tenés cambios sin confirmar.' : 'Elegí tus reemplazos y después actualizá la comparación.' }}<span v-if="selections.length" class="block font-semibold">{{ selections.length }} reemplazo(s) elegido(s) en total</span></p>
      <button v-if="ordered.length > 3" type="button" class="inline-flex min-h-11 items-center gap-2 text-sm font-semibold" @click="showAll = !showAll"><ChevronDown class="size-4" />{{ showAll ? 'Ver solo las primeras tres' : `Ver todas (${ordered.length})` }}</button>
      <button type="button" class="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50" :disabled="busy" @click="emit('apply')"><LoaderCircle v-if="busy" class="size-4 animate-spin" /><Check v-else class="size-4" />{{ busy ? 'Actualizando comparación…' : dirty ? 'Confirmar cambios y comparar' : 'Actualizar comparación' }}</button>
    </div>
  </section>
</template>
