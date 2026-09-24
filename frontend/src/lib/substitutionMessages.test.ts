import { describe, expect, it } from 'vitest'
import { substitutionEmptyMessage } from './substitutionMessages'
import type { SubstitutionDiagnostics } from '@/types'

const diagnostics: SubstitutionDiagnostics = {
  code: 'no_suitable_prices', compatible_products: 2, stale_products: 1,
  suspect_products: 0, max_price_age_days: 14,
}

describe('live substitution explanations', () => {
  it('distinguishes compatible products with unusable prices from incompatible products', () => {
    const message = substitutionEmptyMessage(diagnostics)
    expect(message).toContain('Hay 2 productos compatibles')
    expect(message).toContain('1 con precios de más de 14 días')
    expect(message).toContain('1 sin precio disponible')
    expect(substitutionEmptyMessage({ ...diagnostics, code: 'no_compatible_products' })).toContain('Ningún producto cargado')
  })
  it('explains missing attributes and chain data without inventing stock', () => {
    expect(substitutionEmptyMessage({ ...diagnostics, code: 'insufficient_attributes' })).toContain('verificar su presentación')
    expect(substitutionEmptyMessage({ ...diagnostics, code: 'no_chain_products' })).toContain('publicaciones activas')
    expect(substitutionEmptyMessage()).toBe('No hay alternativas compatibles con precio apto.')
  })
})
