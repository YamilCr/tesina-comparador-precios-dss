import { describe, expect, it } from 'vitest'

import { formatCurrency } from './format'

describe('formatCurrency', () => {
  it('formats ARS values for Argentina', () => {
    expect(formatCurrency('10250')).toContain('10.250')
  })
})
