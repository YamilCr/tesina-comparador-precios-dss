<script setup lang="ts">
import { computed, ref } from 'vue'
import { Check, ChevronDown, LoaderCircle, RotateCcw, Search } from 'lucide-vue-next'
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
}>()
const emit = defineEmits<{
  search: [branchId: string]
  select: [branchId: string, originalId: string, replacementId: string | null]
  restore: [branchId: string]
  apply: []
}>()
const showAll = ref(false)
const ordered = computed(() => props.branches.filter((b) => !b.accepted_substitutions).sort((a, b) =>
  a.productos_faltantes.length - b.productos_faltantes.length || Number(a.distance_km ?? 0) - Number(b.distance_km ?? 0)))
const visible = computed(() => [...(showAll.value ? ordered.value : ordered.value.slice(0, 3)), ...props.branches.filter((b) => b.accepted_substitutions)])
const selected = (branch: string, original: string) => props.selections.find((s) => s.branch_id === branch && s.original_product_id === original)?.replacement_product_id
const reason = (value: string) => value === 'stale' ? 'Precio vencido' : value === 'suspect' ? 'Precio anómalo' : 'Sin precio apto'
</script>

<template>
  <section v-if="branches.length" class="mt-8 border-t border-amber-200 pt-6" aria-label="Alternativas por sucursal">
    <h3 class="text-lg font-semibold">{{ ordered.length ? 'Sucursales sin cobertura completa' : 'Revisar sustituciones' }}</h3>
    <p v-if="ordered.length" class="mt-1 text-sm text-slate-600">Las canastas incompletas quedan fuera del ranking hasta contar con precios aptos para todos sus productos.</p>
    <p class="mt-1 text-sm text-slate-600">Disponibilidad publicada o inferida; stock físico no confirmado.</p>
    <article v-for="branch in visible" :key="branch.sucursal.id" class="mt-4 rounded-lg border border-amber-200 bg-white p-4 sm:p-5">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0 break-words">
          <h4 class="font-semibold">{{ branch.sucursal.supermercado }} · {{ branch.sucursal.nombre }}</h4>
          <p class="mt-1 text-sm text-slate-600">Última cobertura evaluada: {{ branch.covered_products_count ?? 0 }}/{{ branch.total_products_count ?? branch.productos_faltantes.length }} · {{ formatNumber(branch.distance_km ?? '0') }} km</p>
          <p class="mt-1 text-sm font-medium text-amber-900">{{ branch.accepted_substitutions ? 'Con sustituciones' : `${branch.productos_faltantes.length} ${branch.productos_faltantes.length === 1 ? 'producto faltante' : 'productos faltantes'}` }}</p>
        </div>
        <button type="button" class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-slate-300 px-3 text-sm font-semibold disabled:opacity-50" :disabled="busy || pending[branch.sucursal.id]" @click="emit('search', branch.sucursal.id)">
          <LoaderCircle v-if="pending[branch.sucursal.id]" class="size-4 animate-spin" /><Search v-else class="size-4" />Buscar alternativas
        </button>
      </div>
      <ul v-if="!branch.accepted_substitutions" class="mt-3 space-y-1 text-sm text-amber-900"><li v-for="item in branch.productos_faltantes" :key="item.id">{{ item.nombre }} · {{ reason(item.motivo) }}</li></ul>
      <p v-if="pending[branch.sucursal.id]" role="status" class="mt-3 text-sm">Buscando alternativas compatibles...</p>
      <p v-if="errors[branch.sucursal.id]" role="alert" class="mt-3 text-sm text-rose-700">{{ errors[branch.sucursal.id] }}</p>
      <template v-if="suggestions[branch.sucursal.id]">
        <p v-if="!suggestions[branch.sucursal.id].items.length" class="mt-4 text-sm">Ya hay precios aptos para los productos originales. Recalculá para actualizar la cobertura.</p>
        <fieldset v-for="group in suggestions[branch.sucursal.id].items" :key="group.original.id" class="mt-5 min-w-0 border-t border-slate-200 pt-3">
          <legend class="max-w-full break-words pr-2 text-sm font-semibold">{{ group.original.normalized_name }} · {{ group.quantity }} {{ Number(group.quantity) === 1 ? 'unidad' : 'unidades' }}</legend>
          <p v-if="!group.candidates.length" class="py-3 text-sm text-slate-600" role="status">{{ substitutionEmptyMessage(group.diagnostics) }}</p>
          <label v-for="candidate in group.candidates" :key="candidate.product.id" class="flex cursor-pointer items-start gap-3 border-b border-slate-100 py-4">
            <input type="radio" :name="`sub-${branch.sucursal.id}-${group.original.id}`" :aria-label="`Elegir ${candidate.product.normalized_name}`" :checked="selected(branch.sucursal.id, group.original.id) === candidate.product.id" :disabled="busy" class="mt-4 size-4 shrink-0" @change="emit('select', branch.sucursal.id, group.original.id, candidate.product.id)" />
            <ProductImage :src="candidate.product.image_url" :name="candidate.product.normalized_name" />
            <span class="min-w-0 flex-1 break-words text-sm">
              <strong class="block">{{ candidate.product.normalized_name }}</strong>
              <span class="mt-1 block text-slate-600">{{ candidate.product.brand_name ?? 'Sin marca informada' }} · {{ candidate.product.base_quantity ?? candidate.product.net_content }} {{ candidate.product.base_unit ?? candidate.product.unit_measure }}<template v-if="(candidate.product.pack_size ?? 1) > 1"> · Pack × {{ candidate.product.pack_size }}</template></span>
              <span class="mt-1 block">{{ candidate.quantity }} × {{ formatCurrency(candidate.unit_price) }} · Subtotal <strong>{{ formatCurrency(candidate.subtotal) }}</strong></span>
              <span class="mt-1 block text-xs text-slate-500">{{ formatDate(candidate.observed_at) }} · {{ candidate.inferred_from_chain ? 'Referencia de otra sucursal de la cadena' : 'Precio publicado para esta sucursal' }}</span>
              <span class="mt-1 block text-xs text-slate-500">{{ candidate.compatibility_reason }}</span>
            </span>
          </label>
          <button v-if="selected(branch.sucursal.id, group.original.id)" type="button" class="mt-2 inline-flex min-h-10 items-center gap-2 text-sm text-rose-700" :disabled="busy" @click="emit('select', branch.sucursal.id, group.original.id, null)"><RotateCcw class="size-4" />Quitar sustituto</button>
        </fieldset>
      </template>
      <button v-if="selections.some((s) => s.branch_id === branch.sucursal.id)" type="button" class="mt-4 inline-flex min-h-10 items-center gap-2 text-sm text-slate-600" :disabled="busy" @click="emit('restore', branch.sucursal.id)"><RotateCcw class="size-4" />Restaurar lista original en esta sucursal</button>
    </article>
    <div class="mt-4 flex flex-wrap justify-between gap-3">
      <button v-if="ordered.length > 3" type="button" class="inline-flex min-h-11 items-center gap-2 text-sm font-semibold" @click="showAll = !showAll"><ChevronDown class="size-4" />{{ showAll ? 'Ver solo las primeras tres' : `Ver todas (${ordered.length})` }}</button>
      <button type="button" class="inline-flex min-h-11 items-center gap-2 rounded-lg bg-emerald-700 px-4 text-sm font-semibold text-white disabled:opacity-50" :disabled="busy" @click="emit('apply')"><LoaderCircle v-if="busy" class="size-4 animate-spin" /><Check v-else class="size-4" />Aplicar cambios y recalcular</button>
    </div>
  </section>
</template>
