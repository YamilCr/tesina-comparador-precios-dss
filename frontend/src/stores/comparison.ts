import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'

import type { BasketItem, Product } from '@/types'

interface PersistedComparison {
  cityId: string
  items: Array<{ product: Product; quantity: number }>
  priceWeight: number
  distanceWeight: number
}

const storageKey = 'dss-precios-comparison'

const loadPersistedState = (): PersistedComparison | null => {
  try {
    const raw = localStorage.getItem(storageKey)
    return raw ? (JSON.parse(raw) as PersistedComparison) : null
  } catch {
    return null
  }
}

export const useComparisonStore = defineStore('comparison', () => {
  const persisted = loadPersistedState()
  const cityId = ref(persisted?.cityId ?? '')
  const items = ref<BasketItem[]>(persisted?.items ?? [])
  const priceWeight = ref(persisted?.priceWeight ?? 60)
  const distanceWeight = ref(persisted?.distanceWeight ?? 30)
  const savingWeight = computed(() => Math.max(0, 100 - priceWeight.value - distanceWeight.value))
  const hasValidWeights = computed(() => priceWeight.value + distanceWeight.value <= 100)
  const totalProducts = computed(() => items.value.length)

  const persist = () => {
    localStorage.setItem(
      storageKey,
      JSON.stringify({
        cityId: cityId.value,
        items: items.value,
        priceWeight: priceWeight.value,
        distanceWeight: distanceWeight.value,
      }),
    )
  }

  watch([cityId, items, priceWeight, distanceWeight], persist, { deep: true })

  const addProduct = (product: Product) => {
    const existing = items.value.find((item) => item.product.id === product.id)
    if (existing) {
      existing.quantity += 1
      return
    }
    items.value.push({ product, quantity: 1 })
  }

  const updateQuantity = (productId: string, quantity: number) => {
    const item = items.value.find((candidate) => candidate.product.id === productId)
    if (!item) return
    item.quantity = Math.max(0.1, Number.isFinite(quantity) ? quantity : 1)
  }

  const removeProduct = (productId: string) => {
    items.value = items.value.filter((item) => item.product.id !== productId)
  }

  const reset = () => {
    items.value = []
    priceWeight.value = 60
    distanceWeight.value = 30
  }

  return {
    cityId,
    items,
    priceWeight,
    distanceWeight,
    savingWeight,
    hasValidWeights,
    totalProducts,
    addProduct,
    updateQuantity,
    removeProduct,
    reset,
  }
})
