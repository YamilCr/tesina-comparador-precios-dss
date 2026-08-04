import { describe, expect, it } from 'vitest'

import { mockApi, mockSeed } from './mock-data'

describe('mock ranking', () => {
  it('returns every mock branch for a complete basket', async () => {
    const result = await mockApi.ranking({
      city_id: mockSeed.cities[0].id,
      items: mockSeed.products.map((product) => ({ product_id: product.id, quantity: '1' })),
      weights: { price: 0.6, distance: 0.3, saving: 0.1 },
    })

    expect(result.ranking).toHaveLength(4)
    expect(result.ranking[0].sucursal.supermercado).toBe('Chango Más')
  })
})
