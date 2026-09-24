import { ref } from 'vue'
import type { DataClient, SubstitutionSelection, SuggestionsRequest, SuggestionsResponse } from '@/types'

// Deliberately memory-only: replacements never enter the persisted comparison store.
export const useSubstitutions = (client: Pick<DataClient, 'substitutions'>) => {
  const selections = ref<SubstitutionSelection[]>([])
  const suggestions = ref<Record<string, SuggestionsResponse>>({})
  const errors = ref<Record<string, string>>({})
  const pending = ref<Record<string, boolean>>({})
  let generation = 0
  const requests = new Map<string, number>()

  const invalidate = (clearSelections = false) => {
    generation++
    suggestions.value = {}
    errors.value = {}
    pending.value = {}
    if (clearSelections) selections.value = []
  }
  const search = async (request: SuggestionsRequest) => {
    const branch = request.branch_id
    const version = generation
    const sequence = (requests.get(branch) ?? 0) + 1
    requests.set(branch, sequence)
    const current = () => version === generation && sequence === requests.get(branch)
    pending.value[branch] = true
    delete errors.value[branch]
    try {
      const response = await client.substitutions(request)
      if (current()) suggestions.value[branch] = response
    } catch (error) {
      if (current()) errors.value[branch] = error instanceof Error ? error.message : 'No se pudieron buscar alternativas.'
    } finally {
      if (current()) pending.value[branch] = false
    }
  }
  const select = (branch: string, original: string, replacement: string | null) => {
    selections.value = selections.value.filter((s) => s.branch_id !== branch || s.original_product_id !== original)
    if (replacement) selections.value.push({ branch_id: branch, original_product_id: original, replacement_product_id: replacement })
  }
  const restore = (branch: string) => {
    selections.value = selections.value.filter((s) => s.branch_id !== branch)
  }
  return { selections, suggestions, errors, pending, invalidate, search, select, restore }
}
