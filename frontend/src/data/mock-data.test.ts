import { describe, expect, it } from 'vitest'

import { mockApi, mockSeed } from './mock-data'

describe('mock ranking', () => {
  it('suggests explicitly and completes only the selected chain', async () => {
    const request = {
      city_id: mockSeed.cities[0].id,
      items: [{ product_id: mockSeed.substitutionProduct.id, quantity: '2' }],
      weights: { price: 0.6, distance: 0.3, saving: 0.1 },
    }
    const original = await mockApi.ranking(request)
    expect(original.incomplete).toHaveLength(1)
    const branch = original.incomplete[0].sucursal.id
    const suggestions = await mockApi.substitutions({ branch_id: branch, items: request.items })
    expect(suggestions.items[0].candidates).toHaveLength(1)
    const changed = await mockApi.ranking({ ...request, substitutions: [{ branch_id: branch,
      original_product_id: request.items[0].product_id, replacement_product_id: suggestions.items[0].candidates[0].product.id }] })
    expect(changed.incomplete).toHaveLength(0)
    expect(changed.ranking.find((b) => b.sucursal.id === branch)?.basket_type).toBe('substituted')
    expect(request.items[0].product_id).toBe(mockSeed.substitutionProduct.id)
    expect((await mockApi.ranking(request)).incomplete).toHaveLength(1)
  })

  it('rejects incompatible and duplicate selections', async () => {
    const selection = { branch_id: mockSeed.branches[0].id, original_product_id: mockSeed.substitutionProduct.id,
      replacement_product_id: mockSeed.products[0].id }
    const request = { city_id: mockSeed.cities[0].id, items: [{ product_id: selection.original_product_id, quantity: '1' }],
      weights: { price: 0.6, distance: 0.3, saving: 0.1 }, substitutions: [selection] }
    await expect(mockApi.ranking(request)).rejects.toThrow('Reemplazo inválido')
    selection.replacement_product_id = mockSeed.products[1].id
    request.substitutions.push(selection)
    await expect(mockApi.ranking(request)).rejects.toThrow('Reemplazo inválido')
  })
  it('keeps a selected product without price out of the savings ranking', async () => {
    const branch = mockSeed.branches[0].id
    const original = mockSeed.products[1].id
    const result = await mockApi.ranking({
      city_id: mockSeed.cities[0].id,
      items: [{ product_id: original, quantity: '1' }],
      weights: { price: 0.6, distance: 0.3, saving: 0.1 },
      substitutions: [{ branch_id: branch, original_product_id: original,
        replacement_product_id: mockSeed.substitutionProduct.id }],
    })
    expect(result.ranking.some((item) => item.sucursal.id === branch)).toBe(false)
    expect(result.incomplete[0].substitutions?.[0].price_status).toBe('missing')
  })
  it('returns each chain once and uses the closest branch', async () => {
    const result = await mockApi.ranking({
      city_id: mockSeed.cities[0].id,
      items: mockSeed.products.map((product) => ({ product_id: product.id, quantity: '1' })),
      weights: { price: 0.6, distance: 0.3, saving: 0.1 },
    })

    expect(result.ranking).toHaveLength(3)
    expect(result.ranking.find((item) => item.sucursal.supermercado === 'La Anónima')?.sucursal.id).toBe(mockSeed.branches[0].id)
    expect(result.ranking[0].sucursal.supermercado).toBe('Chango Más')
  })

  it('keeps a chain substitution when another branch becomes nearest', async () => {
    const request = { city_id: mockSeed.cities[1].id,
      origin_latitude: mockSeed.branches[3].latitud, origin_longitude: mockSeed.branches[3].longitud,
      items: [{ product_id: mockSeed.substitutionProduct.id, quantity: '1' }],
      weights: { price: 0.6, distance: 0.3, saving: 0.1 },
      substitutions: [{ branch_id: mockSeed.branches[0].id,
        original_product_id: mockSeed.substitutionProduct.id, replacement_product_id: mockSeed.products[1].id }] }
    const result = await mockApi.ranking(request)
    const la = result.ranking.find((item) => item.sucursal.supermercado === 'La Anónima')
    expect(la?.sucursal.id).toBe(mockSeed.branches[3].id)
    expect(la?.basket_type).toBe('substituted')
  })
})
